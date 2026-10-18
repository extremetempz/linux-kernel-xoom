#!/usr/bin/env python3
"""Read-only audit of the preserved working and failed diagnostic boot images."""
from pathlib import Path
import argparse, gzip, hashlib, json, struct, zlib
p=argparse.ArgumentParser();p.add_argument('--working',type=Path,default=Path('artifacts/hardware-private/backup-boot.img'));p.add_argument('--candidate',type=Path,default=Path('artifacts/diagnostic/wingray-diagnostic.img'));args=p.parse_args()
def sha(data):return hashlib.sha256(data).hexdigest()
def kernel_payload(z):
    for off in range(len(z)-3):
        if z[off:off+3]!=b'\x1f\x8b\x08':continue
        try:
            decoder=zlib.decompressobj(31);raw=decoder.decompress(z[off:]);raw+=decoder.flush()
            if decoder.eof and len(raw)>100000:return off,raw
        except zlib.error:pass
    raise ValueError('No complete gzip kernel found')
def audit(path):
    data=path.read_bytes();assert data[:8]==b'ANDROID!'
    k,ka,r,ra,s,sa,tags,page,dt_size,unused=struct.unpack_from('<10I',data,8)
    assert page>=608 and page&(page-1)==0 and s==0 and dt_size==0
    align=lambda n:(n+page-1)//page*page
    roff=page+align(k)
    kernel=data[page:page+k];ramdisk=data[roff:roff+r]
    assert len(kernel)==k and len(ramdisk)==r
    assert struct.unpack_from('<I',kernel,36)[0]==0x016f2818
    zs,ze=struct.unpack_from('<II',kernel,40);zend=ze-zs
    assert 48<zend<=k
    off,raw=kernel_payload(kernel[:zend])
    h=hashlib.sha1()
    for component in (kernel,ramdisk,b''):h.update(component);h.update(struct.pack('<I',len(component)))
    d={'file':path.name,'sha256':sha(data),'page_size':page,'kernel_size':k,'kernel_load':hex(ka),'ramdisk_size':r,'ramdisk_load':hex(ra),'tags_address':hex(tags),'second_load':hex(sa),'zimage_start_word':hex(zs),'zimage_end_word':hex(ze),'zimage_size':zend,'gzip_offset':off,'decompressed_image_size':len(raw),'decompressed_range_at_0x8000':[hex(0x8000),hex(0x8000+len(raw))],'kernel_component_sha256':sha(kernel),'v0_sha1_id_matches':data[576:596]==h.digest(),'header_cmdline':data[64:576].split(b'\0')[0].decode(errors='replace')}
    assert ka+k<=ra, 'compressed kernel overlaps ramdisk'
    assert not (0x8000<=tags<0x8000+len(raw)), 'tags overlap decompression output'
    assert 0x8000+len(raw)<ka and 0x8000+len(raw)<ra
    if k>zend:
        dtb=kernel[zend:];magic,total=struct.unpack_from('>II',dtb)
        assert magic==0xd00dfeed and total==len(dtb) and (ka+zend)%8==0
        d['appended_dtb']={'size':total,'address_before_fixup':hex(ka+zend),'sha256':sha(dtb)}
    d['ramdisk_gzip_valid']=len(gzip.decompress(ramdisk))>0
    marker=raw.find(b'IKCFG_ST')
    if marker>=0:
        decoder=zlib.decompressobj(31)
        config=decoder.decompress(raw[marker+8:])+decoder.flush()
        assert decoder.eof
        lines=config.decode().splitlines()
        d['embedded_config_sha256']=sha(config)
        d['embedded_boot_config']=[line for line in lines if line.startswith((
            'CONFIG_CMDLINE=', 'CONFIG_AUTO_ZRELADDR=', 'CONFIG_DEBUG_LL=',
            'CONFIG_DEBUG_UNCOMPRESS=', 'CONFIG_ARM_APPENDED_DTB=',
            'CONFIG_ARM_ATAG_DTB_COMPAT=', 'CONFIG_PAGE_OFFSET=',
            'CONFIG_SMP=', 'CONFIG_ARM_VIRT_EXT=', 'CONFIG_CPU_V7='))]

    # Confirm the existing Wingray fixed-destination ARM instructions, rather
    # than inferring their presence from CONFIG_AUTO_ZRELADDR=y.
    d['early_r4_pc_relative_literals']=[]
    for i in range(48,min(zend,256),4):
        instruction=struct.unpack_from('<I',kernel,i)[0]
        if instruction & 0xfffff000 == 0xe59f4000:
            address=i+8+(instruction&0xfff)
            if address+4<=zend:
                d['early_r4_pc_relative_literals'].append({'instruction_offset':hex(i),'literal_offset':hex(address),'value':hex(struct.unpack_from('<I',kernel,address)[0])})
    d['fixed_destination_0x8000_instruction_offsets']=[hex(i) for i in range(0,min(zend,1024),4) if kernel[i:i+8]==struct.pack('<II',0xe3a04000,0xe2844902)]
    return d
print(json.dumps({'working':audit(args.working),'diagnostic':audit(args.candidate),'limits':['Header addresses are declarations, not a capture of entry registers or actual bootloader placement.','No live ATAG list or CPU/MMU/cache state was captured.','Old v0 SHA1 ID mismatch alone does not establish a boot defect.']},indent=2))
