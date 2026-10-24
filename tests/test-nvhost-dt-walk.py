#!/usr/bin/env python3
"""Run actual recursive nvhost DT population with reference-counted fake nodes."""
from pathlib import Path
import subprocess,tempfile
source=(Path(__file__).resolve().parents[1]/'sources/kernel-donor/drivers/of/platform.c').read_text()
a=source.index('static int of_nvhost_bus_create(');e=source.index('{',a)+1;depth=1
while depth:depth+=(source[e]=='{')-(source[e]=='}');e+=1
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define pr_debug(...) ((void)0)
struct device_node{const char*name,*full_name;int refs,enabled,error;struct device_node*child,*next;};
struct of_dev_auxdata{const char*name;void*platform_data;};
static int creates;
static int of_device_is_available(struct device_node*n){return n->enabled;}
static const struct of_dev_auxdata*of_dev_lookup(const struct of_dev_auxdata*l,struct device_node*n){(void)l;(void)n;return NULL;}
static int of_nvhost_device_create(struct device_node*n,const char*b,void*p){(void)b;(void)p;creates++;return n->error;}
static void of_node_put(struct device_node*n){assert(n->refs>1);n->refs--;}
static struct device_node*next_child(struct device_node*p,struct device_node*prev){struct device_node*n=prev?prev->next:p->child;if(prev)of_node_put(prev);if(n)n->refs++;return n;}
#define for_each_child_of_node(p,c) for(c=next_child(p,NULL);c;c=next_child(p,c))
'''
main=r'''
int main(void){
 struct device_node disabled={"off","/off",1,0,0,NULL,NULL};
 struct device_node active={"on","/on",1,1,0,NULL,NULL};
 struct device_node root={"host","/host",1,1,0,&disabled,NULL};disabled.next=&active;
 assert(!of_nvhost_bus_create(&root,NULL));assert(creates==2&&root.refs==1&&disabled.refs==1&&active.refs==1);
 active.error=-EIO;creates=0;assert(of_nvhost_bus_create(&root,NULL)==-EIO);assert(creates==2&&disabled.refs==1&&active.refs==1);
 root.enabled=0;creates=0;assert(of_nvhost_bus_create(&root,NULL)==-ENODEV);assert(!creates&&root.refs==1);
 puts("PASS actual nvhost DT walk: disabled child skip, success/error propagation and balanced iterator references (UBSan)");}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'test.c';p.write_text(prefix+source[a:e]+main)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',t+'/test'],check=True);subprocess.run([t+'/test'],check=True)
