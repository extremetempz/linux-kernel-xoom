#!/usr/bin/env python3
"""Compile actual Wingray CPCAP transport/setup functions with an SPI spy."""
from pathlib import Path
import subprocess,tempfile,sys
source=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'sources/kernel-donor'
s=(source/'drivers/mfd/motorola-cpcap.c').read_text()
def function(name):
 start=s.index('static ',s.index(name)-30)
 brace=s.index('{',start);i=brace+1;depth=1
 while depth:
  if s[i]=='{':depth+=1
  elif s[i]=='}':depth-=1
  i+=1
 return s[start:i]+'\n'
code='''#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
#define CPCAP_REG_ST_TEST2 0x7d08
#define SPI_MODE_0 0
#define SPI_CS_HIGH 4
struct spi_device {unsigned int mode,bits_per_word;};
struct spi_transfer {const void *tx_buf;void *rx_buf;unsigned int len,bits_per_word;};
struct spi_message {struct spi_transfer *transfer;};
static int wingray=1, spi_error=0, calls=0, setup_error=0;
static u32 last_tx, reply;
static bool of_machine_is_compatible(const char *s){return wingray&&!strcmp(s,"motorola,wingray");}
static void spi_message_init(struct spi_message *m){m->transfer=0;}
static void spi_message_add_tail(struct spi_transfer *t,struct spi_message *m){assert(!m->transfer);m->transfer=t;}
static int spi_sync(struct spi_device *spi,struct spi_message *m){
 (void)spi;calls++;assert(m->transfer&&m->transfer->len==4&&m->transfer->bits_per_word==32);
 assert(m->transfer->tx_buf&&m->transfer->rx_buf);
 last_tx=*(const u32 *)m->transfer->tx_buf;*(u32 *)m->transfer->rx_buf=reply;return spi_error;
}
static int spi_setup(struct spi_device *spi){(void)spi;return setup_error;}
'''
code+=function('cpcap_wingray_identity_valid')+function('cpcap_wingray_transfer')+function('cpcap_setup_transport')
code+='''int main(void){struct spi_device spi={0};unsigned int out=0xdead;
assert(!cpcap_setup_transport(&spi));assert(spi.bits_per_word==32&&spi.mode==(SPI_MODE_0|SPI_CS_HIGH));
wingray=0;assert(!cpcap_setup_transport(&spi));assert(spi.bits_per_word==16&&spi.mode==(SPI_MODE_0|SPI_CS_HIGH));
setup_error=-5;assert(cpcap_setup_transport(&spi)==-5);
reply=0xabcd1234;assert(!cpcap_wingray_transfer(&spi,0x24,0,false,&out));
assert(last_tx==0x00240000&&out==0x1234); /* INTS2 = legacy address 9 << 2 */
assert(!cpcap_wingray_transfer(&spi,0x48,0,false,&out));assert(last_tx==0x00480000);
assert(!cpcap_wingray_transfer(&spi,0x14,0xff7f,true,0));assert(last_tx==0x8014ff7f);
int before=calls;assert(cpcap_wingray_transfer(&spi,1,0,false,&out)==-EINVAL);
assert(cpcap_wingray_transfer(&spi,0x8000,0,false,&out)==-EINVAL);
assert(cpcap_wingray_transfer(&spi,0x24,0x10000,true,0)==-EINVAL);assert(calls==before);
spi_error=-5;out=0xdead;assert(cpcap_wingray_transfer(&spi,0x24,0,false,&out)==-5);assert(out==0xdead);
assert(!cpcap_wingray_identity_valid(0));assert(!cpcap_wingray_identity_valid(0xffff));assert(cpcap_wingray_identity_valid(0x1234));
return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['cc','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual CPCAP functions: native32 full duplex, Motorola CS polarity, register vectors, errors, identity guard')
