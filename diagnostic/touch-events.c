/* SPDX-License-Identifier: GPL-2.0
 * Bounded Wingray evdev observation. Independent O_RDONLY/nonblocking fd;
 * never grabs/injects events, changes input state, or opens raw hardware.
 */
#include <linux/input.h>
#include <linux/poll.h>

#ifdef __arm__
_Static_assert(sizeof(long) == 4, "ARM EABI scalar width");
_Static_assert(sizeof(struct input_event) == 16, "Linux 4.4 ARM evdev wire size");
_Static_assert(sizeof(struct input_absinfo) == 24, "Linux 4.4 absinfo wire size");
_Static_assert(sizeof(struct pollfd) == 8, "Linux ARM poll wire size");
#endif

#define MAX_SLOTS 32
#define MAX_EVENTS 8192U
#define MAX_RECORDS 64U
#ifndef EXPECTED_RELEASE
#define EXPECTED_RELEASE "4.4.147-wingray-android44-touch"
#endif
#define EXPECTED_NAME "Atmel maXTouch Touchscreen"

static long call6(long n, long a, long b, long c, long d, long e, long f)
{
    register long r0 __asm__("r0") = a;
    register long r1 __asm__("r1") = b;
    register long r2 __asm__("r2") = c;
    register long r3 __asm__("r3") = d;
    register long r4 __asm__("r4") = e;
    register long r5 __asm__("r5") = f;
    register long r7 __asm__("r7") = n;
    __asm__ volatile("svc 0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3),
                     "r"(r4), "r"(r5), "r"(r7) : "memory", "cc");
    return r0;
}
static unsigned length(const char *s)
{
    unsigned n = 0;
    while (s[n]) ++n;
    return n;
}
static int equal(const char *a, const char *b)
{
    unsigned i = 0;
    while (a[i] && a[i] == b[i]) ++i;
    return a[i] == b[i];
}
static void text(const char *s)
{
    unsigned n = length(s);
    while (n) {
        long wrote = call6(4, 1, (long)s, n, 0, 0, 0);
        if (wrote == -4) continue;
        if (wrote <= 0 || (unsigned long)wrote > n) return;
        s += wrote;
        n -= (unsigned)wrote;
    }
}
static void number(long v)
{
    char buffer[12];
    unsigned magnitude, p = sizeof(buffer)-1;
    buffer[p] = 0;
    magnitude = v < 0 ? 0U-(unsigned)v : (unsigned)v;
    do {
        buffer[--p] = (char)('0' + magnitude % 10U);
        magnitude /= 10U;
    } while (magnitude);
    if (v < 0) buffer[--p] = '-';
    text(buffer+p);
}
static void field(const char *name, long value)
{
    text(name); number(value); text("\n");
}
static void clear(void *pointer, unsigned bytes)
{
    unsigned char *p = pointer;
    while (bytes--) *p++ = 0;
}
static int has_bit(const unsigned long *bits, unsigned bit)
{
    unsigned width = sizeof(unsigned long)*8;
    return !!(bits[bit / width] & (1UL << (bit % width)));
}
static char uts[6][65], compatible[256];
static int scope_ok(void)
{
    long fd, n;
    unsigned offset = 0;
    if (call6(122, (long)uts, 0, 0, 0, 0, 0) < 0 ||
        !equal(uts[2], EXPECTED_RELEASE)) {
        text("XOOM_TOUCH_DENIED_RELEASE\n");
        return 0;
    }
    fd = call6(5, (long)"/sys/firmware/devicetree/base/compatible",
               0x80000, 0, 0, 0, 0); /* O_RDONLY|O_CLOEXEC */
    if (fd < 0) {
        text("XOOM_TOUCH_DENIED_BOARD\n");
        return 0;
    }
    n = call6(3, fd, (long)compatible, sizeof(compatible), 0, 0, 0);
    call6(6, fd, 0, 0, 0, 0, 0);
    if (n > 0 && (unsigned long)n < sizeof(compatible) && !compatible[n-1]) {
        while (offset < (unsigned)n) {
            if (equal(compatible+offset, "motorola,wingray")) return 1;
            offset += length(compatible+offset)+1;
        }
    }
    text("XOOM_TOUCH_DENIED_BOARD\n");
    return 0;
}
struct slot_state {
    int tracking, x, y;
    unsigned changed, known_x, known_y;
};
struct sample_state {
    struct slot_state slots[MAX_SLOTS];
    struct input_absinfo slot_range, x_range, y_range, id_range;
    int slot;
    unsigned events, frames, presses, releases, positions;
    unsigned invalid, records, suppressed, btn_press, btn_release, lost;
    unsigned id_replacements;
};
static struct sample_state state;
static void init_state(struct sample_state *s)
{
    unsigned i;
    clear(s, sizeof(*s));
    for (i = 0; i < MAX_SLOTS; ++i) s->slots[i].tracking = -1;
}
static int in_range(int value, const struct input_absinfo *range)
{
    return value >= range->minimum && value <= range->maximum;
}
static void record_slot(struct sample_state *s, unsigned index)
{
    struct slot_state *slot = &s->slots[index];
    if (s->records >= MAX_RECORDS) { ++s->suppressed; return; }
    ++s->records;
    text("XOOM_TOUCH_CONTACT slot="); number(index);
    text(" id="); number(slot->tracking);
    text(" x="); if (slot->known_x) number(slot->x); else text("unknown");
    text(" y="); if (slot->known_y) number(slot->y); else text("unknown");
    text("\n");
}
/* Returns false if evdev reports a lost stream. No inferred events are added. */
static int consume(struct sample_state *s, const struct input_event *event)
{
    struct slot_state *slot;
    unsigned i;
    ++s->events;
    if (event->type == EV_SYN) {
        if (event->code == SYN_DROPPED) { ++s->lost; return 0; }
        if (event->code != SYN_REPORT) return 1;
        ++s->frames;
        for (i = 0; i <= (unsigned)s->slot_range.maximum; ++i) {
            if (s->slots[i].changed) record_slot(s, i);
            s->slots[i].changed = 0;
        }
        return 1;
    }
    if (event->type == EV_KEY && event->code == BTN_TOUCH) {
        if (event->value == 1) ++s->btn_press;
        else if (event->value == 0) ++s->btn_release;
        else if (event->value != 2) ++s->invalid;
        return 1;
    }
    if (event->type != EV_ABS) return 1;
    if (event->code == ABS_MT_SLOT) {
        if (!in_range(event->value, &s->slot_range)) {
            ++s->invalid; s->slot = -1;
        } else s->slot = event->value;
        return 1;
    }
    if (s->slot < 0) { ++s->invalid; return 1; }
    slot = &s->slots[s->slot];
    if (event->code == ABS_MT_TRACKING_ID) {
        if (event->value == -1) {
            if (slot->tracking >= 0) ++s->releases;
            slot->tracking = -1;
            slot->changed = 1;
        } else if (in_range(event->value, &s->id_range)) {
            if (slot->tracking < 0) ++s->presses;
            else if (slot->tracking != event->value) {
                ++s->id_replacements; ++s->presses;
            }
            slot->tracking = event->value;
            slot->known_x = slot->known_y = 0;
            slot->changed = 1;
        } else ++s->invalid;
    } else if (event->code == ABS_MT_POSITION_X) {
        if (in_range(event->value, &s->x_range)) {
            slot->x = event->value; slot->known_x = 1;
            slot->changed = 1; ++s->positions;
        } else ++s->invalid;
    } else if (event->code == ABS_MT_POSITION_Y) {
        if (in_range(event->value, &s->y_range)) {
            slot->y = event->value; slot->known_y = 1;
            slot->changed = 1; ++s->positions;
        } else ++s->invalid;
    }
    return 1;
}
static int capabilities(long fd, struct sample_state *s)
{
    unsigned long events[(EV_MAX+sizeof(long)*8)/(sizeof(long)*8)];
    unsigned long abs[(ABS_MAX+sizeof(long)*8)/(sizeof(long)*8)];
    unsigned long keys[(KEY_MAX+sizeof(long)*8)/(sizeof(long)*8)];
    char name[64];
    long n;
    clear(name, sizeof(name));
    n = call6(54, fd, EVIOCGNAME(sizeof(name)), (long)name, 0, 0, 0);
    if (n <= 0 || n > (long)sizeof(name) || name[sizeof(name)-1] ||
        !equal(name, EXPECTED_NAME)) return 0;
    clear(events, sizeof(events)); clear(abs, sizeof(abs)); clear(keys, sizeof(keys));
    if (call6(54, fd, EVIOCGBIT(0, sizeof(events)), (long)events, 0, 0, 0) < 0 ||
        !has_bit(events, EV_ABS) || !has_bit(events, EV_KEY) ||
        call6(54, fd, EVIOCGBIT(EV_ABS, sizeof(abs)), (long)abs, 0, 0, 0) < 0 ||
        call6(54, fd, EVIOCGBIT(EV_KEY, sizeof(keys)), (long)keys, 0, 0, 0) < 0 ||
        !has_bit(keys, BTN_TOUCH) || !has_bit(abs, ABS_MT_SLOT) ||
        !has_bit(abs, ABS_MT_TRACKING_ID) ||
        !has_bit(abs, ABS_MT_POSITION_X) || !has_bit(abs, ABS_MT_POSITION_Y)) return 0;
    if (call6(54, fd, EVIOCGABS(ABS_MT_SLOT), (long)&s->slot_range, 0, 0, 0) < 0 ||
        call6(54, fd, EVIOCGABS(ABS_MT_TRACKING_ID), (long)&s->id_range, 0, 0, 0) < 0 ||
        call6(54, fd, EVIOCGABS(ABS_MT_POSITION_X), (long)&s->x_range, 0, 0, 0) < 0 ||
        call6(54, fd, EVIOCGABS(ABS_MT_POSITION_Y), (long)&s->y_range, 0, 0, 0) < 0)
        return 0;
    if (s->slot_range.minimum != 0 || s->slot_range.maximum < 0 ||
        s->slot_range.maximum >= MAX_SLOTS ||
        !in_range(s->slot_range.value, &s->slot_range) ||
        s->id_range.minimum != 0 || s->id_range.maximum < 0 ||
        s->id_range.maximum > 65535 ||
        s->x_range.minimum < 0 || s->x_range.maximum <= s->x_range.minimum ||
        s->x_range.maximum > 65535 || s->y_range.minimum < 0 ||
        s->y_range.maximum <= s->y_range.minimum || s->y_range.maximum > 65535)
        return 0;
    s->slot = s->slot_range.value;
    return 1;
}
static long choose_device(struct sample_state *s)
{
    unsigned i;
    char path[] = "/dev/input/event00";
    for (i = 0; i < 16; ++i) {
        long fd;
        unsigned end = sizeof(path)-3;
        if (i >= 10) { path[end++] = '1'; path[end++] = (char)('0'+i-10); }
        else path[end++] = (char)('0'+i);
        path[end] = 0;
        fd = call6(5, (long)path, 0xa0800, 0, 0, 0, 0);
        /* O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC; never use write flags. */
        if (fd < 0) continue;
        if (capabilities(fd, s)) {
            text("XOOM_TOUCH_DEVICE "); text(path); text("\n");
            return fd;
        }
        call6(6, fd, 0, 0, 0, 0, 0);
    }
    return -1;
}
struct arm_time { long seconds, nanoseconds; };
static int get_time(struct arm_time *t)
{
    return call6(263, 1, (long)t, 0, 0, 0, 0) >= 0 &&
           t->seconds >= 0 && t->nanoseconds >= 0 && t->nanoseconds < 1000000000L;
}
static int before(const struct arm_time *a, const struct arm_time *b)
{
    return a->seconds < b->seconds ||
           (a->seconds == b->seconds && a->nanoseconds < b->nanoseconds);
}
static int sample(void)
{
    struct arm_time started, now, previous;
    struct pollfd wait;
    struct input_event buffer[32];
    long fd, count, remaining_ms;
    unsigned i;
    const char *status = "deadline_complete";
    int result = 0;
    text("XOOM_TOUCH_EVENTS_BEGIN\n");
    if (!scope_ok()) { text("XOOM_TOUCH_EVENTS_END\n"); return 1; }
    init_state(&state);
    fd = choose_device(&state);
    if (fd < 0) {
        text("XOOM_TOUCH_NO_MATCHING_DEVICE\nXOOM_TOUCH_EVENTS_END\n");
        return 2;
    }
    text("XOOM_TOUCH_NAME " EXPECTED_NAME "\n");
    field("XOOM_TOUCH_SLOT_MAX ", state.slot_range.maximum);
    field("XOOM_TOUCH_X_MIN ", state.x_range.minimum);
    field("XOOM_TOUCH_X_MAX ", state.x_range.maximum);
    field("XOOM_TOUCH_Y_MIN ", state.y_range.minimum);
    field("XOOM_TOUCH_Y_MAX ", state.y_range.maximum);
    if (!get_time(&started)) { status = "clock_failed"; result = 3; goto done; }
    previous = started;
    wait.fd = (int)fd; wait.events = POLLIN; wait.revents = 0;
    for (;;) {
        if (!get_time(&now) || before(&now, &previous)) {
            status = "clock_failed"; result = 3; break;
        }
        previous = now;
        /* Exact five-second monotonic deadline, checked before each batch. */
        if (now.seconds-started.seconds > 5 ||
            (now.seconds-started.seconds == 5 && now.nanoseconds >= started.nanoseconds))
            break;
        wait.revents = 0;
        remaining_ms = (5-(now.seconds-started.seconds))*1000 -
                       (now.nanoseconds-started.nanoseconds)/1000000;
        if (remaining_ms <= 0) break;
        count = call6(168, (long)&wait, 1, remaining_ms < 50 ? remaining_ms : 50,
                      0, 0, 0);
        if (count == -4) continue;
        if (count < 0 || (wait.revents & (POLLERR|POLLHUP|POLLNVAL))) {
            status = "poll_failed"; result = 3; break;
        }
        if (!count || !(wait.revents & POLLIN)) continue;
        if (!get_time(&now) || before(&now, &previous)) {
            status = "clock_failed"; result = 3; break;
        }
        previous = now;
        if (now.seconds-started.seconds > 5 ||
            (now.seconds-started.seconds == 5 && now.nanoseconds >= started.nanoseconds))
            break;
        count = call6(3, fd, (long)buffer, sizeof(buffer), 0, 0, 0);
        if (count == -11 || count == -4) continue;
        if (count <= 0 || (unsigned long)count > sizeof(buffer) ||
            count % sizeof(struct input_event)) {
            status = "read_failed"; result = 3; break;
        }
        for (i = 0; i < (unsigned long)count/sizeof(struct input_event); ++i) {
            if (!consume(&state, &buffer[i])) {
                status = "syn_dropped_incomplete"; result = 3; goto done;
            }
            if (state.events >= MAX_EVENTS) {
                status = "event_limit_incomplete"; result = 3; goto done;
            }
        }
    }
done:
    call6(6, fd, 0, 0, 0, 0, 0);
    field("XOOM_TOUCH_EVENTS ", state.events);
    field("XOOM_TOUCH_FRAMES ", state.frames);
    field("XOOM_TOUCH_PRESSES_OBSERVED ", state.presses);
    field("XOOM_TOUCH_RELEASES_OBSERVED ", state.releases);
    field("XOOM_TOUCH_ID_REPLACEMENTS ", state.id_replacements);
    field("XOOM_TOUCH_POSITION_EVENTS ", state.positions);
    field("XOOM_TOUCH_BTN_PRESS ", state.btn_press);
    field("XOOM_TOUCH_BTN_RELEASE ", state.btn_release);
    field("XOOM_TOUCH_INVALID_EVENTS ", state.invalid);
    field("XOOM_TOUCH_RECORDS_SUPPRESSED ", state.suppressed);
    text("XOOM_TOUCH_SAMPLE_STATUS "); text(status); text("\n");
    text("XOOM_TOUCH_EVENTS_END\n");
    return result;
}
void _start(void) __attribute__((noreturn));
void _start(void)
{
    int status = sample();
    call6(1, status, 0, 0, 0, 0, 0);
    for (;;) { }
}
