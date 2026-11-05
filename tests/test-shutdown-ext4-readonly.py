#!/usr/bin/env python3
"""Compile the donor's real clean-RO transition against a faulted journal model."""
from pathlib import Path
import subprocess,tempfile,re
R=Path(__file__).resolve().parents[1]
s=(R/'sources/kernel-donor/fs/ext4/super.c').read_text()
def function(name):
 match=re.search(r'(?m)^static (?:void|int) '+re.escape(name)+r'\([^;{]*\)\s*\{',s)
 assert match,name
 start=match.start();begin=match.end()-1;end=begin+1;depth=1
 while depth:
  depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]+'\n'
body=function('ext4_mark_recovery_complete')
remount=function('ext4_remount')
assert 'ext4_mark_recovery_complete' in remount and 'jbd2_journal_destroy' not in remount
c=r'''
#include <assert.h>
#define MS_RDONLY 1
#define NULL ((void*)0)
#define BUG_ON(x) assert(!(x))
typedef int journal_t;
struct info {journal_t *s_journal;};
struct super_block {int s_flags,journal,needs;struct info info;};
struct ext4_super_block {int unused;};
#define EXT4_SB(sb) (&(sb)->info)
static int locked,unlocked,flush_error,committed;
static int ext4_has_feature_journal(struct super_block *s){return s->journal;}
static int ext4_has_feature_journal_needs_recovery(struct super_block *s){return s->needs;}
static void ext4_clear_feature_journal_needs_recovery(struct super_block *s){s->needs=0;}
static void jbd2_journal_lock_updates(journal_t *j){assert(j);locked++;}
static void jbd2_journal_unlock_updates(journal_t *j){assert(j);unlocked++;}
static int jbd2_journal_flush(journal_t *j){assert(j);return flush_error;}
static void ext4_commit_super(struct super_block *s,int sync){assert(s&&sync);committed++;}
'''+body+r'''
int main(void){
 journal_t j=0;struct ext4_super_block es={0};
 struct super_block sb={MS_RDONLY,1,1,{&j}};
 ext4_mark_recovery_complete(&sb,&es);assert(!sb.needs&&committed==1&&locked==1&&unlocked==1);
 sb.needs=1;flush_error=-5;ext4_mark_recovery_complete(&sb,&es);
 assert(sb.needs&&committed==1&&locked==2&&unlocked==2); /* userspace must reject still-dirty state */
 flush_error=0;sb.s_flags=0;ext4_mark_recovery_complete(&sb,&es);
 assert(sb.needs&&committed==1&&locked==3&&unlocked==3);
 sb.journal=0;sb.info.s_journal=NULL;ext4_mark_recovery_complete(&sb,&es);
 assert(locked==3&&unlocked==3);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'test';p.with_suffix('.c').write_text(c)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=undefined',str(p.with_suffix('.c')),'-o',str(p)],check=True)
 subprocess.run([str(p)],check=True)
print('PASS actual ext4 clean-RO transition: flush/clear/commit ordering and dirty-state retention on journal failure')
