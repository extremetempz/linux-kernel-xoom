LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)
LOCAL_MODULE := xoom-egl-probe
LOCAL_MODULE_TAGS := optional
LOCAL_SRC_FILES := egl-probe.c
LOCAL_SHARED_LIBRARIES := libEGL libGLESv2
LOCAL_CFLAGS := -std=gnu99 -Wall -Wextra -Werror
include $(BUILD_EXECUTABLE)
