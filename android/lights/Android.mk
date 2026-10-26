LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)
LOCAL_MODULE := lights.stingray
LOCAL_MODULE_RELATIVE_PATH := hw
LOCAL_MODULE_TAGS := optional
LOCAL_SRC_FILES := lights.c
LOCAL_CFLAGS := -Wall -Wextra -Werror -std=gnu11
LOCAL_SHARED_LIBRARIES :=
LOCAL_LDLIBS :=
include $(BUILD_SHARED_LIBRARY)
