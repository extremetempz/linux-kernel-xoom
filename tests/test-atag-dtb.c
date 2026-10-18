/* Execute the donor's real ATAG converter and libfdt against the built DTB.
 * Synthetic public boot data: this does not capture the live bootloader r2.
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libfdt.h>
#include <asm/setup.h>
int atags_to_fdt(void *, void *, int);
int main(int argc, char **argv)
{
    unsigned char fdt[65536] __attribute__((aligned(8)));
    unsigned char tags[2048] __attribute__((aligned(8))) = {0};
    const char *cmd = "mem=1024M@0M gpt gpt_sector=0x03b9dfff rdinit=/init";
    struct tag *t = (void *)tags;
    FILE *in; int n,len,chosen,memory; const fdt32_t *v;
    assert(argc==2); in=fopen(argv[1],"rb"); assert(in);
    n=fread(fdt,1,sizeof(fdt),in); fclose(in);assert(n>0 && n<32768);
    assert(fdt_check_header(fdt)==0);
    t->hdr.tag=ATAG_CORE;t->hdr.size=2;t=tag_next(t);
    t->hdr.tag=ATAG_MEM;t->hdr.size=tag_size(tag_mem32);
    t->u.mem.start=0;t->u.mem.size=0x40000000;t=tag_next(t);
    t->hdr.tag=ATAG_INITRD2;t->hdr.size=tag_size(tag_initrd);
    t->u.initrd.start=0x11000000;t->u.initrd.size=0x100000;t=tag_next(t);
    t->hdr.tag=ATAG_CMDLINE;t->hdr.size=(sizeof(struct tag_header)+strlen(cmd)+1+3)/4;
    memcpy(tags + ((unsigned char *)t-tags) + sizeof(struct tag_header),cmd,strlen(cmd)+1);t=tag_next(t);
    t->hdr.tag=ATAG_NONE;t->hdr.size=0;
    assert(atags_to_fdt(tags,fdt,32768)==0);
    memory=fdt_path_offset(fdt,"/memory");assert(memory>=0);
    v=fdt_getprop(fdt,memory,"reg",&len);assert(v && len==8);
    assert(fdt32_to_cpu(v[0])==0 && fdt32_to_cpu(v[1])==0x40000000);
    chosen=fdt_path_offset(fdt,"/chosen");assert(chosen>=0);
    assert(!strcmp(fdt_getprop(fdt,chosen,"bootargs",NULL),cmd));
    v=fdt_getprop(fdt,chosen,"linux,initrd-start",&len);assert(v&&len==4&&fdt32_to_cpu(*v)==0x11000000);
    v=fdt_getprop(fdt,chosen,"linux,initrd-end",&len);assert(v&&len==4&&fdt32_to_cpu(*v)==0x11100000);
    puts("Actual donor ATAG converter passed synthetic Wingray memory/cmdline/initrd transfer.");
    return 0;
}
