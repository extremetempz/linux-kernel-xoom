#!/usr/bin/env python3
"""Exercise the actual probe with host Mesa software and fault wrappers.

NVIDIA identity is supplied ONLY by this test executable's link wrappers.
No host result establishes Tegra acceleration or Android build compatibility.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WRAPPERS = r'''
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int surfaces, contexts, shaders, programs;
static int fault(const char *name) {
    const char *value = getenv("XOOM_HOST_TEST_FAULT");
    return value && !strcmp(value, name);
}
static void check_cleanup(void) __attribute__((destructor));
static void check_cleanup(void) {
    assert(!surfaces && !contexts && !shaders && !programs);
    puts("HOST_MESA_TEST_ONLY resource_cleanup=pass");
}
const GLubyte *__real_glGetString(GLenum);
const GLubyte *__wrap_glGetString(GLenum name) {
    if (fault("software")) return __real_glGetString(name);
    if (fault("null_identity")) return NULL;
    if (name == GL_VENDOR) return (const GLubyte *)"NVIDIA Corporation";
    if (name == GL_RENDERER) return (const GLubyte *)"NVIDIA Tegra 2";
    if (name == GL_VERSION) return (const GLubyte *)"OpenGL ES 2.0 HOST TEST ONLY";
    return __real_glGetString(name);
}
EGLBoolean __real_eglChooseConfig(EGLDisplay,const EGLint *,EGLConfig *,EGLint,EGLint *);
EGLBoolean __wrap_eglChooseConfig(EGLDisplay d,const EGLint *a,EGLConfig *c,EGLint n,EGLint *found) {
    if (fault("no_config")) { *found=0; return EGL_TRUE; }
    return __real_eglChooseConfig(d,a,c,n,found);
}
EGLSurface __real_eglCreatePbufferSurface(EGLDisplay,EGLConfig,const EGLint *);
EGLSurface __wrap_eglCreatePbufferSurface(EGLDisplay d,EGLConfig c,const EGLint *a) {
    EGLSurface s;
    if (fault("pbuffer")) return EGL_NO_SURFACE;
    s=__real_eglCreatePbufferSurface(d,c,a); if(s!=EGL_NO_SURFACE) surfaces++; return s;
}
EGLBoolean __real_eglDestroySurface(EGLDisplay,EGLSurface);
EGLBoolean __wrap_eglDestroySurface(EGLDisplay d,EGLSurface s) {
    EGLBoolean ok=__real_eglDestroySurface(d,s); assert(ok); surfaces--; return ok;
}
EGLContext __real_eglCreateContext(EGLDisplay,EGLConfig,EGLContext,const EGLint *);
EGLContext __wrap_eglCreateContext(EGLDisplay d,EGLConfig c,EGLContext share,const EGLint *a) {
    EGLContext ctx;
    if (fault("context")) return EGL_NO_CONTEXT;
    ctx=__real_eglCreateContext(d,c,share,a); if(ctx!=EGL_NO_CONTEXT) contexts++; return ctx;
}
EGLBoolean __real_eglDestroyContext(EGLDisplay,EGLContext);
EGLBoolean __wrap_eglDestroyContext(EGLDisplay d,EGLContext c) {
    EGLBoolean ok=__real_eglDestroyContext(d,c); assert(ok); contexts--; return ok;
}
EGLBoolean __real_eglMakeCurrent(EGLDisplay,EGLSurface,EGLSurface,EGLContext);
EGLBoolean __wrap_eglMakeCurrent(EGLDisplay d,EGLSurface s,EGLSurface r,EGLContext c) {
    if (fault("current") && c!=EGL_NO_CONTEXT) return EGL_FALSE;
    return __real_eglMakeCurrent(d,s,r,c);
}
GLuint __real_glCreateShader(GLenum);
GLuint __wrap_glCreateShader(GLenum t) {
    GLuint s=__real_glCreateShader(t); if(s) shaders++; return s;
}
void __real_glDeleteShader(GLuint);
void __wrap_glDeleteShader(GLuint s) { __real_glDeleteShader(s); shaders--; }
void __real_glGetShaderiv(GLuint,GLenum,GLint *);
void __wrap_glGetShaderiv(GLuint s,GLenum p,GLint *out) {
    GLint type;
    __real_glGetShaderiv(s,p,out);
    __real_glGetShaderiv(s,GL_SHADER_TYPE,&type);
    if (p==GL_COMPILE_STATUS &&
        ((fault("vertex_compile") && type==GL_VERTEX_SHADER) ||
         (fault("fragment_compile") && type==GL_FRAGMENT_SHADER))) *out=GL_FALSE;
}
GLuint __real_glCreateProgram(void);
GLuint __wrap_glCreateProgram(void) {
    GLuint p=__real_glCreateProgram(); if(p) programs++; return p;
}
void __real_glDeleteProgram(GLuint);
void __wrap_glDeleteProgram(GLuint p) { __real_glDeleteProgram(p); programs--; }
void __real_glGetProgramiv(GLuint,GLenum,GLint *);
void __wrap_glGetProgramiv(GLuint p,GLenum name,GLint *out) {
    __real_glGetProgramiv(p,name,out);
    if(fault("link") && name==GL_LINK_STATUS) *out=GL_FALSE;
}
void __real_glDrawArrays(GLenum,GLint,GLsizei);
void __wrap_glDrawArrays(GLenum mode,GLint first,GLsizei count) {
    if(!fault("no_draw")) __real_glDrawArrays(mode,first,count);
}
void __real_glReadPixels(GLint,GLint,GLsizei,GLsizei,GLenum,GLenum,void *);
void __wrap_glReadPixels(GLint x,GLint y,GLsizei w,GLsizei h,GLenum format,GLenum type,void *pixels) {
    static unsigned int frame;
    __real_glReadPixels(x,y,w,h,format,type,pixels);
    if(fault("bad_readback")) memset(pixels,0,w*h*4);
    if(fault("stale_second_frame") && frame++) {
        GLubyte *p=(GLubyte *)pixels+4*(8*16+8); p[0]=0; p[1]=255; p[2]=0; p[3]=255;
    }
}
'''

names = [
    'glGetString', 'eglChooseConfig', 'eglCreatePbufferSurface',
    'eglDestroySurface', 'eglCreateContext', 'eglDestroyContext',
    'eglMakeCurrent', 'glCreateShader', 'glDeleteShader', 'glGetShaderiv',
    'glCreateProgram', 'glDeleteProgram', 'glGetProgramiv',
    'glDrawArrays', 'glReadPixels',
]
cases = {
    'none': (0, None),
    'software': (2, 'identity'),
    'null_identity': (2, 'identity'),
    'no_config': (1, 'choose_config'),
    'pbuffer': (1, 'create_pbuffer'),
    'context': (1, 'create_context'),
    'current': (1, 'make_current'),
    'vertex_compile': (1, 'compile_shaders'),
    'fragment_compile': (1, 'compile_shaders'),
    'link': (1, 'link_program'),
    'no_draw': (1, 'draw_readback'),
    'bad_readback': (1, 'draw_readback'),
    'stale_second_frame': (1, 'draw_readback'),
}
with tempfile.TemporaryDirectory(prefix='xoom-egl-host-test-') as temp:
    temp = Path(temp)
    wrappers = temp / 'wrappers.c'
    wrappers.write_text(WRAPPERS)
    binary = temp / 'probe'
    subprocess.run([
        'cc', '-std=gnu99', '-Wall', '-Wextra', '-Werror',
        str(ROOT / 'diagnostic/egl-probe/egl-probe.c'), str(wrappers),
        *['-Wl,--wrap=' + name for name in names], '-lEGL', '-lGLESv2',
        '-o', str(binary),
    ], check=True)
    for fault, (expected, stage) in cases.items():
        env = dict(os.environ, EGL_PLATFORM='surfaceless',
                   LIBGL_ALWAYS_SOFTWARE='true', XOOM_HOST_TEST_FAULT=fault)
        result = subprocess.run([str(binary)], env=env, capture_output=True,
                                text=True, timeout=25)
        assert result.returncode == expected, (fault, result.stdout, result.stderr)
        assert 'resource_cleanup=pass' in result.stdout, (fault, result.stdout)
        if stage:
            assert 'stage=' + stage in result.stdout, (fault, result.stdout)
            assert 'XOOM_EGL_OFFSCREEN_READBACK_PASS' not in result.stdout
        else:
            assert 'frame=1 triangle_and_background_readback=pass' in result.stdout
            assert 'XOOM_EGL_OFFSCREEN_READBACK_PASS' in result.stdout
        print('PASS HOST MESA ONLY:', fault)
print('13 host client/failure cases passed. Tegra/Android execution not tested.')
