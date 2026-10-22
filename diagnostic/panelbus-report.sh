#!/bin/busybox sh
# Fixed readiness readback. No i2cset, force flag, bus scan or configuration.
/bin/busybox printf 'XOOM_PANELBUS_BEGIN\n'
release=$(/bin/busybox uname -r)
if [ "$release" != '4.4.147-wingray-panelbus' ]; then
 /bin/busybox printf 'XOOM_PANELBUS_STATUS denied_release\nXOOM_PANELBUS_END\n'
 exit 0
fi
if ! /bin/busybox tr '\000' '\n' < /sys/firmware/devicetree/base/compatible | /bin/busybox grep -qx 'motorola,wingray'; then
 /bin/busybox printf 'XOOM_PANELBUS_STATUS denied_board\nXOOM_PANELBUS_END\n'
 exit 0
fi
node=$(/bin/busybox readlink -f /sys/class/i2c-adapter/i2c-0/of_node)
case "$node" in
 */i2c@7000c000) ;;
 *) /bin/busybox printf 'XOOM_PANELBUS_STATUS denied_adapter\nXOOM_PANELBUS_END\n'; exit 0;;
esac
if [ ! -c /dev/i2c-0 ]; then
 /bin/busybox printf 'XOOM_PANELBUS_STATUS missing_device\nXOOM_PANELBUS_END\n'
 exit 0
fi
# Read byte-data only at the known backlight address. Selecting a register
# sends its address byte; no register value or EEPROM-program command is sent.
# Stop at the first failure. Never force access to an owned I2C address.
status=read_complete
for reg in 0x00 0x01 0x03 0x04 0xa0 0xa1 0xa2 0xa3 0xa4 0xa5 0xa6 0xa7; do
 value=$(/bin/busybox i2cget -y 0 0x2c "$reg" b 2>/run/panelbus-read-error.txt)
 result=$?
 if [ "$result" -ne 0 ]; then
  /bin/busybox printf 'XOOM_PANELBUS_READ_ERROR %s %s\n' "$reg" "$result"
  status=read_failed
  break
 fi
 /bin/busybox printf 'XOOM_LP8550_REG %s %s\n' "$reg" "$value"
done
/bin/busybox printf 'XOOM_PANELBUS_STATUS %s\n' "$status"
/bin/busybox printf 'XOOM_PANEL_REGULATORS_BEGIN\n'
for rail in /sys/class/regulator/regulator.*; do
 [ -r "$rail/name" ] || continue
 name=$(/bin/busybox cat "$rail/name")
 [ "$name" = 'wingray-panel' ] || continue
 /bin/busybox printf 'XOOM_PANEL_RAIL %s\n' "$name"
 for attr in state microvolts num_users; do
  [ -r "$rail/$attr" ] || continue
  /bin/busybox printf '%s=' "$attr"
  /bin/busybox cat "$rail/$attr"
 done
done
/bin/busybox printf 'XOOM_PANEL_REGULATORS_END\nXOOM_CLOCKS_BEGIN\n'
[ ! -r /sys/kernel/debug/clk/clk_summary ] || /bin/busybox cat /sys/kernel/debug/clk/clk_summary
/bin/busybox printf 'XOOM_CLOCKS_END\nXOOM_PANELBUS_END\n'
