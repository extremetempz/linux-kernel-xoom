/*
 * ABI subset transcribed without changes to layout from Android 4.4.4_r2
 * hardware/libhardware include/hardware/{hardware,lights}.h.
 * Copyright (C) 2008 The Android Open Source Project
 * Licensed under the Apache License, Version 2.0.
 * http://www.apache.org/licenses/LICENSE-2.0
 * Provided AS IS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
 * Keep standalone ARM build independent of a host libc/sysroot.
 */
#ifndef XOOM_KITKAT_LIGHTS_ABI_H
#define XOOM_KITKAT_LIGHTS_ABI_H
struct hw_module_t;
struct hw_device_t;
struct hw_module_methods_t {
 int (*open)(const struct hw_module_t *, const char *, struct hw_device_t **);
};
struct hw_module_t {
 unsigned int tag;
 unsigned short module_api_version, hal_api_version;
 const char *id, *name, *author;
 struct hw_module_methods_t *methods;
 void *dso;
 unsigned int reserved[32-7];
};
struct hw_device_t {
 unsigned int tag, version;
 struct hw_module_t *module;
 unsigned int reserved[12];
 int (*close)(struct hw_device_t *);
};
struct light_state_t {
 unsigned int color;
 int flashMode, flashOnMS, flashOffMS, brightnessMode;
};
struct light_device_t {
 struct hw_device_t common;
 int (*set_light)(struct light_device_t *, const struct light_state_t *);
};
#define HARDWARE_MODULE_TAG 0x48574d54U
#define HARDWARE_DEVICE_TAG 0x48574454U
#ifdef __arm__
_Static_assert(sizeof(struct hw_module_t)==128,"KitKat ARM32 module ABI");
_Static_assert(sizeof(struct hw_device_t)==64,"KitKat ARM32 device ABI");
_Static_assert(sizeof(struct light_device_t)==68,"KitKat ARM32 lights ABI");
_Static_assert(sizeof(struct light_state_t)==20,"KitKat ARM32 state ABI");
#endif
#endif
