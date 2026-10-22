#!/usr/bin/env python3
"""Execute real evdev policy/parser behind a recorded host syscall boundary.
No host input device is opened. Host input_event widths differ from ARM; the
separate exported-UAPI ARM build checks the physical wire representation.
"""
from pathlib import Path
import re
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
source = (ROOT/'diagnostic/touch-events.c').read_text()
start = source.index('static long call6(')
opening = source.index('{', start)
position, depth = opening+1, 1
while depth:
    depth += (source[position]=='{')-(source[position]=='}')
    position += 1
source = source[:start]+source[start:opening].rstrip()+';'+source[position:]
source = re.sub(r'\b_start\b', 'probe_start', source)
fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
enum failure { NORMAL, BAD_RELEASE, BAD_BOARD, NO_DEVICE, BAD_NAME,
 NO_CAP, BAD_SLOT_MAX, BAD_SLOT_VALUE, BAD_X_RANGE, CLOCK_FAIL, CLOCK_BACKWARDS,
 POLL_FAIL, POLL_HANGUP, SHORT_READ, EOF_READ, LOST, FLOOD, SILENT };
static struct {
 enum failure failure;
 unsigned opens, ioctls, clocks, polls, reads, closes, event_opens, events_seen;
 int consumed;
 char output[32768];
 unsigned bytes;
} mock;
'''
mock = r'''
static void set_bit(unsigned long *bits, unsigned value) {
 bits[value/(8*sizeof(long))] |= 1UL << (value%(8*sizeof(long)));
}
static long call6(long n, long a, long b, long c, long d, long e, long f) {
 (void)d;(void)e;(void)f;
 switch(n) {
 case 122: strcpy(uts[2], mock.failure==BAD_RELEASE?"old-kernel":EXPECTED_RELEASE);return 0;
 case 5: {
  ++mock.opens;
  const char *path=(const char *)a;
  if(!strcmp(path,"/sys/firmware/devicetree/base/compatible")) {
   assert(b==0x80000 && c==0);return 3;
  }
  char expected[32];snprintf(expected,sizeof(expected),"/dev/input/event%u",mock.event_opens++);
  assert(!strcmp(path,expected));
  assert(b==0xa0800 && c==0); /* read-only, never grab or exclusive flags */
  if(mock.failure==NO_DEVICE)return -2;
  return 10;
 }
 case 6: assert(a==3 || a==10);++mock.closes;return 0;
 case 4:
  assert(a==1 && c>=0 && mock.bytes+(unsigned long)c<sizeof(mock.output));
  memcpy(mock.output+mock.bytes,(void *)b,(size_t)c);mock.bytes+=(unsigned)c;
  mock.output[mock.bytes]=0;return c;
 case 3:
  if(a==3) {
   const char *board=mock.failure==BAD_BOARD?"motorola,other":"motorola,wingray";
   size_t size=strlen(board)+1;memcpy((void *)b,board,size);return size;
  }
  assert(a==10 && c==sizeof(struct input_event)*32);
  ++mock.reads;
  if(mock.failure==SHORT_READ)return 1;
  if(mock.failure==EOF_READ)return 0;
  struct input_event *events=(struct input_event *)b;
  memset(events,0,(size_t)c);
  if(mock.failure==LOST) { events[0].type=EV_SYN;events[0].code=SYN_DROPPED;return sizeof(*events); }
  if(mock.failure==FLOOD) {
   for(unsigned i=0;i<32;i+=4) {
    events[i].type=EV_ABS;events[i].code=ABS_MT_TRACKING_ID;events[i].value=(int)++mock.events_seen;
    events[i+1].type=EV_ABS;events[i+1].code=ABS_MT_POSITION_X;events[i+1].value=65535;
    events[i+2].type=EV_ABS;events[i+2].code=ABS_MT_POSITION_Y;events[i+2].value=65535;
    events[i+3].type=EV_SYN;events[i+3].code=SYN_REPORT;
   }
   return c;
  }
  assert(!mock.consumed++);
  events[0].type=EV_ABS;events[0].code=ABS_MT_SLOT;events[0].value=1;
  events[1].type=EV_ABS;events[1].code=ABS_MT_TRACKING_ID;events[1].value=45;
  events[2].type=EV_ABS;events[2].code=ABS_MT_POSITION_X;events[2].value=123;
  events[3].type=EV_ABS;events[3].code=ABS_MT_POSITION_Y;events[3].value=456;
  events[4].type=EV_KEY;events[4].code=BTN_TOUCH;events[4].value=1;
  events[5].type=EV_SYN;events[5].code=SYN_REPORT;
  events[6].type=EV_ABS;events[6].code=ABS_MT_TRACKING_ID;events[6].value=-1;
  events[7].type=EV_KEY;events[7].code=BTN_TOUCH;events[7].value=0;
  events[8].type=EV_SYN;events[8].code=SYN_REPORT;
  return sizeof(*events)*9;
 case 54: {
  assert(a==10);++mock.ioctls;
  if(b==(long)EVIOCGNAME(64)) {
   const char *name=mock.failure==BAD_NAME?"Atmel maXTouch Touchpad":EXPECTED_NAME;
   strcpy((char *)c,name);return (long)strlen(name)+1;
  }
  unsigned long *bits=(unsigned long *)c;
  if(b==(long)EVIOCGBIT(0, sizeof(unsigned long)*((EV_MAX+sizeof(long)*8)/(sizeof(long)*8)))) {
   if(mock.failure==NO_CAP)return -25;
   set_bit(bits,EV_ABS);set_bit(bits,EV_KEY);return 1;
  }
  if(b==(long)EVIOCGBIT(EV_ABS,sizeof(unsigned long)*((ABS_MAX+sizeof(long)*8)/(sizeof(long)*8)))) {
   set_bit(bits,ABS_MT_SLOT);set_bit(bits,ABS_MT_TRACKING_ID);
   set_bit(bits,ABS_MT_POSITION_X);set_bit(bits,ABS_MT_POSITION_Y);return 1;
  }
  if(b==(long)EVIOCGBIT(EV_KEY,sizeof(unsigned long)*((KEY_MAX+sizeof(long)*8)/(sizeof(long)*8)))) {
   set_bit(bits,BTN_TOUCH);return 1;
  }
  struct input_absinfo *range=(struct input_absinfo *)c;
  assert(b==(long)EVIOCGABS(ABS_MT_SLOT) || b==(long)EVIOCGABS(ABS_MT_TRACKING_ID) ||
   b==(long)EVIOCGABS(ABS_MT_POSITION_X) || b==(long)EVIOCGABS(ABS_MT_POSITION_Y));
  memset(range,0,sizeof(*range));range->maximum=65535;
  if(b==(long)EVIOCGABS(ABS_MT_SLOT)) {
   range->maximum=mock.failure==BAD_SLOT_MAX?32:9;
   range->value=mock.failure==BAD_SLOT_VALUE?10:0;
  }
  if(b==(long)EVIOCGABS(ABS_MT_POSITION_X) && mock.failure==BAD_X_RANGE)range->minimum=-1;
  return 0;
 }
 case 263: {
  assert(a==1);++mock.clocks;
  if(mock.failure==CLOCK_FAIL)return -38;
  struct arm_time *time=(struct arm_time *)b;
  unsigned ticks=mock.failure==FLOOD?0:mock.clocks;
  time->seconds=100+ticks/20;time->nanoseconds=(ticks%20)*50000000U;
  if(mock.failure==CLOCK_BACKWARDS && mock.clocks>1)time->seconds=99;
  return 0;
 }
 case 168: {
  assert(b==1 && c>0 && c<=50);++mock.polls;
  struct pollfd *wait=(struct pollfd *)a;assert(wait->fd==10 && wait->events==POLLIN);
  if(mock.failure==POLL_FAIL)return -5;
  if(mock.failure==POLL_HANGUP) {wait->revents=POLLHUP;return 1;}
  if(mock.failure==SILENT || (mock.consumed && mock.failure!=FLOOD))return 0;
  wait->revents=POLLIN;return 1;
 }
 default: assert(!"unreviewed syscall attempted");return -38;
 }
}
static void run(enum failure failure,int expected) {
 memset(&mock,0,sizeof(mock));mock.failure=failure;
 assert(sample()==expected);
 assert(mock.bytes<8192);
 if(failure==BAD_RELEASE)assert(mock.opens==0);
 if(failure==BAD_BOARD)assert(mock.event_opens==0);
 if(failure==NO_DEVICE || failure==BAD_NAME || failure==NO_CAP || failure==BAD_SLOT_MAX || failure==BAD_SLOT_VALUE || failure==BAD_X_RANGE) {
  assert(mock.event_opens==16 && mock.polls==0);
 }
 if(failure==NORMAL) {
  assert(state.presses==1 && state.releases==1 && state.positions==2 && state.frames==2);
  assert(state.btn_press==1 && state.btn_release==1);
  assert(strstr(mock.output,"slot=1 id=45 x=123 y=456"));
  assert(strstr(mock.output,"deadline_complete"));
 }
 if(failure==SILENT) {
  assert(!state.events && !state.presses && !state.releases);
  assert(strstr(mock.output,"deadline_complete")); /* Not hardware touch proof. */
 }
 if(failure==FLOOD) {
  assert(state.events==8192 && state.records==64 && state.suppressed==1984);
  assert(state.presses==2048 && state.releases==0 && state.id_replacements==2047);
  assert(strstr(mock.output,"event_limit_incomplete"));
  printf("MAX_NATIVE_BYTES=%u\n",mock.bytes);
 }
 if(failure==LOST)assert(strstr(mock.output,"syn_dropped_incomplete"));
}
static void parsing_bounds(void) {
 struct {unsigned before;struct sample_state state;unsigned after;} guarded;
 guarded.before=0x12345678;guarded.after=0x87654321;
 init_state(&guarded.state);guarded.state.slot_range.maximum=31;
 guarded.state.id_range.maximum=65535;guarded.state.x_range.maximum=1280;guarded.state.y_range.maximum=800;
 struct input_event event={0};event.type=EV_ABS;event.code=ABS_MT_SLOT;
 int bad[]={-2147483647,-1,32,2147483647};
 for(unsigned i=0;i<4;++i) {
  event.value=bad[i];consume(&guarded.state,&event);
  event.code=ABS_MT_POSITION_X;event.value=22;consume(&guarded.state,&event);
  event.code=ABS_MT_SLOT;
 }
 event.value=31;consume(&guarded.state,&event);
 event.code=ABS_MT_TRACKING_ID;event.value=3;consume(&guarded.state,&event);
 event.code=ABS_MT_POSITION_X;event.value=1281;consume(&guarded.state,&event);
 event.code=ABS_MT_POSITION_Y;event.value=-1;consume(&guarded.state,&event);
 assert(guarded.state.invalid==10 && guarded.state.presses==1 && guarded.state.positions==0);
 assert(guarded.before==0x12345678 && guarded.after==0x87654321);
}
int main(void) {
 run(NORMAL,0);run(BAD_RELEASE,1);run(BAD_BOARD,1);
 for(enum failure f=NO_DEVICE;f<=BAD_X_RANGE;++f)run(f,2);
 for(enum failure f=CLOCK_FAIL;f<=FLOOD;++f)run(f,3);
 run(SILENT,0);parsing_bounds();
 puts("PASS real touch reader: scopes, fixed read-only paths/ioctls, 5s monotonic deadline, device/stream failures, tracking/coordinates/releases, lost-stream denial, flood/output/slot bounds.");
}
'''
with tempfile.TemporaryDirectory(prefix='xoom-touch-events-') as directory:
    p=Path(directory)
    (p/'test.c').write_text(fixture+source+mock)
    subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-O2','-fsanitize=undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    completed=subprocess.run([str(p/'test')],text=True,capture_output=True,check=True)
    print(completed.stdout,end='')
