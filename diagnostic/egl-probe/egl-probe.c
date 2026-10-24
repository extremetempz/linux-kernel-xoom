/* SPDX-License-Identifier: GPL-2.0-only
 * Manual, offscreen smoke test of the existing EGL/GLES2 implementation.
 * Does not replace a driver, compositor, fence test or display test.
 * Not included in any boot image or automatic startup path.
 */
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#ifdef XOOM_EGL_KITKAT_ABI
#include "kitkat-c-api.h"
#else
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#endif

static GLuint shader(GLenum type, const char *source)
{
    GLuint object = glCreateShader(type);
    GLint ok = GL_FALSE;
    char log[512];
    GLsizei length = 0;

    if (!object)
        return 0;
    glShaderSource(object, 1, &source, NULL);
    glCompileShader(object);
    glGetShaderiv(object, GL_COMPILE_STATUS, &ok);
    if (ok)
        return object;
    glGetShaderInfoLog(object, sizeof(log), &length, log);
    if (length < 0)
        length = 0;
    if (length > (GLsizei)sizeof(log))
        length = sizeof(log);
    printf("shader_failed type=%u log=%.*s\n", type, (int)length, log);
    glDeleteShader(object);
    return 0;
}

static int pixel_equal(const GLubyte *pixel, const GLubyte *expected)
{
    unsigned int i;
    for (i = 0; i < 4; ++i) {
        int delta = (int)pixel[i] - expected[i];
        if (delta < -2 || delta > 2)
            return 0;
    }
    return 1;
}

int main(void)
{
    const EGLint config_attrs[] = {
        EGL_SURFACE_TYPE, EGL_PBUFFER_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8,
        EGL_ALPHA_SIZE, 8, EGL_NONE
    };
    const EGLint surface_attrs[] = {EGL_WIDTH, 16, EGL_HEIGHT, 16, EGL_NONE};
    const EGLint context_attrs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    const GLfloat vertices[] = {-1, -1, 1, -1, 0, 1};
    const GLubyte backgrounds[2][4] = {{255, 0, 0, 255}, {0, 0, 255, 255}};
    const GLubyte foregrounds[2][4] = {{0, 255, 0, 255}, {255, 255, 0, 255}};
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT;
    EGLConfig config;
    EGLint count = 0, major = 0, minor = 0;
    GLuint vs = 0, fs = 0, program = 0;
    GLint linked = GL_FALSE, color = -1;
    int initialized = 0, current = 0, result = 1;
    unsigned int frame;
    const char *stage = "get_display";
    const char *vendor, *renderer, *version;

    /* Bounds ordinary userspace stalls; cannot guarantee interrupting a
     * driver stuck in an uninterruptible kernel wait. */
    alarm(20);
#ifndef XOOM_EGL_KITKAT_ABI
    setvbuf(stdout, NULL, _IONBF, 0);
#endif
    display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (display == EGL_NO_DISPLAY)
        goto out;
    stage = "initialize";
    if (!eglInitialize(display, &major, &minor))
        goto out;
    initialized = 1;
    stage = "bind_es";
    if (!eglBindAPI(EGL_OPENGL_ES_API))
        goto out;
    stage = "choose_config";
    if (!eglChooseConfig(display, config_attrs, &config, 1, &count) || count != 1)
        goto out;
    stage = "create_pbuffer";
    surface = eglCreatePbufferSurface(display, config, surface_attrs);
    if (surface == EGL_NO_SURFACE)
        goto out;
    stage = "create_context";
    context = eglCreateContext(display, config, EGL_NO_CONTEXT, context_attrs);
    if (context == EGL_NO_CONTEXT)
        goto out;
    stage = "make_current";
    if (!eglMakeCurrent(display, surface, surface, context))
        goto out;
    current = 1;
    stage = "identity";
    vendor = (const char *)glGetString(GL_VENDOR);
    renderer = (const char *)glGetString(GL_RENDERER);
    version = (const char *)glGetString(GL_VERSION);
    printf("egl=%d.%d vendor=%.*s renderer=%.*s version=%.*s\n",
           major, minor, 160, vendor ? vendor : "(null)",
           160, renderer ? renderer : "(null)",
           160, version ? version : "(null)");
    /* Identity is necessary but insufficient evidence of acceleration.
     * Require correct rendering below too; never accept a software control. */
    if (!vendor || !renderer || !version ||
        !strstr(vendor, "NVIDIA") || !strstr(renderer, "Tegra") ||
        strncmp(version, "OpenGL ES 2.", 12)) {
        result = 2;
        goto out;
    }
    stage = "compile_shaders";
    vs = shader(GL_VERTEX_SHADER,
                "attribute vec2 position; void main() {"
                "gl_Position = vec4(position, 0.0, 1.0); }");
    if (!vs)
        goto out;
    fs = shader(GL_FRAGMENT_SHADER,
                "precision mediump float; uniform vec4 color;"
                "void main() { gl_FragColor = color; }");
    if (!fs)
        goto out;
    stage = "link_program";
    program = glCreateProgram();
    if (!program)
        goto out;
    glAttachShader(program, vs);
    glAttachShader(program, fs);
    glBindAttribLocation(program, 0, "position");
    glLinkProgram(program);
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked)
        goto out;
    color = glGetUniformLocation(program, "color");
    if (color < 0)
        goto out;
    stage = "draw_readback";
    glUseProgram(program);
    glViewport(0, 0, 16, 16);
    glDisable(GL_DITHER);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, vertices);
    glEnableVertexAttribArray(0);
    for (frame = 0; frame < 2; ++frame) {
        GLubyte pixels[16 * 16 * 4];
        glClearColor(backgrounds[frame][0] / 255.0f,
                     backgrounds[frame][1] / 255.0f,
                     backgrounds[frame][2] / 255.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        glUniform4f(color, foregrounds[frame][0] / 255.0f,
                    foregrounds[frame][1] / 255.0f,
                    foregrounds[frame][2] / 255.0f, 1.0f);
        glDrawArrays(GL_TRIANGLES, 0, 3);
        glFinish();
        memset(pixels, 0x5a, sizeof(pixels));
        glReadPixels(0, 0, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
        if (glGetError() != GL_NO_ERROR ||
            !pixel_equal(pixels + 4 * (8 * 16 + 8), foregrounds[frame]) ||
            !pixel_equal(pixels + 4 * (15 * 16), backgrounds[frame]) ||
            !pixel_equal(pixels + 4 * (15 * 16 + 15), backgrounds[frame]))
            goto out;
        printf("frame=%u triangle_and_background_readback=pass\n", frame);
    }
    result = 0;
out:
    if (result)
        printf("XOOM_EGL_PROBE_FAILED stage=%s result=%d egl_error=0x%x\n",
               stage, result, eglGetError());
    if (current) {
        if (program)
            glDeleteProgram(program);
        if (fs)
            glDeleteShader(fs);
        if (vs)
            glDeleteShader(vs);
        eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    }
    if (context != EGL_NO_CONTEXT)
        eglDestroyContext(display, context);
    if (surface != EGL_NO_SURFACE)
        eglDestroySurface(display, surface);
    if (initialized)
        eglTerminate(display);
    if (!result)
        puts("XOOM_EGL_OFFSCREEN_READBACK_PASS (not composition/fence validation)");
    alarm(0);
#ifdef XOOM_EGL_KITKAT_ABI
    fflush(NULL);
#endif
    return result;
}
