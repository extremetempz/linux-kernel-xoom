"""Opt-in KitKat shutdown handoff; existing diagnostic images keep log-only powerctl."""

def init_actions():
    lines = ['# Explicit normal shutdown/reboot only; diagnostic profiles remain log-only.']
    for request, mode in (('shutdown', 'shutdown'), ('shutdown,', 'shutdown'),
                          ('shutdown,userrequested', 'shutdown'),
                          ('reboot', 'reboot'), ('reboot,', 'reboot')):
        lines += ['on property:sys.powerctl=' + request,
                  '    write /dev/kmsg XOOM_SHUTDOWN_REQUEST_' + mode,
                  '    write /cache/xoom-shutdown-step before_late_start',
                  '    class_stop late_start',
                  '    write /cache/xoom-shutdown-step after_late_start',
                  '    write /cache/xoom-shutdown-step before_main',
                  '    class_stop main',
                  '    write /cache/xoom-shutdown-step after_main',
                  '    write /cache/xoom-shutdown-step before_core',
                  '    class_stop core',
                  '    write /cache/xoom-shutdown-step after_core',
                  '    write /cache/xoom-shutdown-step before_script',
                  '    start xoom' + mode, '']
    for mode in ('shutdown', 'reboot'):
        lines += ['service xoom' + mode + ' /bin/xoom-clean-shutdown ' + mode,
                  '    class xoom_power', '    user root', '    group root',
                  '    disabled', '    oneshot', '',
                  'on property:sys.xoom.shutdown_ready=' + mode,
                  '    write /dev/kmsg XOOM_SHUTDOWN_NATIVE_' + mode,
                  '    powerctl ' + mode, '']
    return '\n'.join(lines).encode()
