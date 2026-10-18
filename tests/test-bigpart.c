/* Host regression tests for the actual kernel BigPart implementation. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

typedef uint64_t u64;
typedef uint32_t u32;
struct device_node { bool bigpart; };
struct device { struct device *parent; struct device_node *of_node; };
struct disk { struct device dev; };
struct bdev { struct disk *bd_disk; unsigned block_size; u64 sectors; };
struct parsed_partitions { struct bdev *bdev; int limit; };
typedef struct { u32 num_partition_entries; u64 last_usable_lba; } gpt_header;
typedef struct { u64 starting_lba, ending_lba; bool used; } gpt_entry;
static bool wingray = true;
#define le32_to_cpu(x) (x)
#define le64_to_cpu(x) (x)
#define disk_to_dev(d) (&(d)->dev)
#define pr_info(...) ((void)0)
static bool of_machine_is_compatible(const char *s)
{ return wingray && !strcmp(s, "motorola,wingray"); }
static bool of_property_read_bool(struct device_node *n, const char *s)
{ return n->bigpart && !strcmp(s, "motorola,xoom-bigpart"); }
static unsigned bdev_logical_block_size(struct bdev *b) { return b->block_size; }
static u64 last_lba(struct bdev *b) { return b->sectors - 1; }
static bool is_pte_valid(gpt_entry *p, u64 last)
{ return p->used && p->starting_lba <= last && p->ending_lba <= last; }

#include "xoom-bigpart-gpt.h"

int main(void)
{
	struct device_node node = { true };
	struct device controller = { NULL, &node };
	struct disk disk = { { &controller, NULL } };
	struct bdev bdev = { &disk, 512, 0x4000000 };
	struct parsed_partitions state = { &bdev, 32 };
	gpt_header gpt = { 4, 0x3ffffde };
	gpt_entry ptes[4] = {
		{ XOOM_SYSTEM_START, XOOM_CACHE_START - 1, true },
		{ XOOM_CACHE_START, XOOM_DATA_START - 1, true },
		{ XOOM_DATA_START, 0x3ffffde, true },
		{ 0x1000, 0x2000, true }
	};
	struct xoom_bigpart_extent p[3];
	int slots[3], i;

	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) == 1);
	assert(p[0].start == 0x1d000 && p[0].size == 0x200000);
	assert(p[1].start == 0x21d000 && p[1].size == 0x100000);
	assert(p[2].start == 0x31d000);
	assert(p[2].start + p[2].size - 1 == ptes[2].ending_lba);
	assert(slots[0] == 0 && slots[1] == 1 && slots[2] == 2);
	/* The function changes only its output, never GPT entries. */
	assert(ptes[0].ending_lba == XOOM_CACHE_START - 1);
	assert(xoom_bigpart_layout(p, gpt.last_usable_lba) < 0);

	wingray = false;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) == 0);
	wingray = true;
	node.bigpart = false;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) == 0);
	node.bigpart = true;
	bdev.block_size = 4096;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	bdev.block_size = 512;
	ptes[0].ending_lba++;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	ptes[0].ending_lba--;
	ptes[3].starting_lba = 0x200000;
	ptes[3].ending_lba = 0x210000;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	ptes[3].starting_lba = 0x1000;
	ptes[3].ending_lba = 0x2000;
	ptes[2].ending_lba = XOOM_DATA_START + XOOM_DATA_SHIFT - 1;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	ptes[2].ending_lba = gpt.last_usable_lba + 1;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	ptes[2].ending_lba = gpt.last_usable_lba;
	ptes[3] = ptes[0];
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	ptes[3].used = false;
	state.limit = 3;
	assert(xoom_bigpart_prepare(&state, &gpt, ptes, slots, p) < 0);
	state.limit = 32;
	for (i = 1; i <= 1000; i++) {
		u64 size = XOOM_DATA_SHIFT + (u64)i * 0x1000;
		struct xoom_bigpart_extent q[3] = {
			{ XOOM_SYSTEM_START, XOOM_SYSTEM_OLD },
			{ XOOM_CACHE_START, XOOM_CACHE_OLD },
			{ XOOM_DATA_START, size }
		};
		u64 end = q[2].start + size;
		assert(xoom_bigpart_layout(q, end - 1) == 0);
		assert(q[0].start + q[0].size == q[1].start);
		assert(q[1].start + q[1].size == q[2].start);
		assert(q[2].start + q[2].size == end);
	}
	puts("BigPart tests passed: board/controller gates, geometry, overlap, bounds, duplicate entries, idempotence and 1000 capacities");
	return 0;
}
