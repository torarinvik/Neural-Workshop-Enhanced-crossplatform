/* Decoding the nw-core display list.
 *
 * The C twin of shells/web/display-list.js and test/display_decode.py. All three
 * decode the same 40-byte fixed command record, and keeping them
 * line-comparable is how they stay in agreement.
 *
 *   [magic u32][version u32][count u32][pool_len u32][commands...][pool bytes]
 *
 * A command is 40 bytes: kind at +0, color at +4, six f32 at +8..+32, then two
 * u32 (ref, len) at +32 and +36. For TEXT and MARKER, `ref` is a byte offset
 * into the pool and the low 24 bits of `len` are the string length; TEXT packs
 * its anchor into the high 8 bits.
 */
#ifndef NW_DISPLAY_LIST_H
#define NW_DISPLAY_LIST_H

#include <stdint.h>
#include <string.h>

#define NW_DL_MAGIC    1313426254u
#define NW_DL_VERSION  1u
#define NW_DL_CMD_SIZE 40u

#define NW_REFERENCE_WIDTH  912.0f
#define NW_REFERENCE_HEIGHT 684.0f

enum nw_kind {
    NW_RECT = 1, NW_BORDERED_RECT = 2, NW_BOX = 3, NW_CIRCLE = 4, NW_ARC = 5,
    NW_LINE = 6, NW_TRIANGLE = 7, NW_POLYGON = 8, NW_POLY_POINT = 9,
    NW_SPRITE = 10, NW_TEXT = 11, NW_VERDICT = 12, NW_SOUND = 13, NW_MARKER = 14,
    NW_SPRITE_FIT = 15, NW_MULTILINE = 16, NW_STAR = 17
};

/* An f32 that rides in a u32 slot -- a rectangle's rotation. The bytes are the
 * number; this is a reinterpret, not a conversion. */
static inline float nw_bits_to_f32(uint32_t bits) {
    float out;
    memcpy(&out, &bits, 4);
    return out;
}

typedef struct {
    uint8_t  kind;
    uint32_t color;
    float    a, b, c, d, e, f;
    uint32_t ref, len;
} nw_cmd;

typedef struct {
    const nw_cmd *commands;      /* borrowed: points into the caller's buffer */
    uint32_t      count;
    const uint8_t *pool;
    uint32_t      pool_len;
} nw_frame;

/* Implemented in Elisa; scratch and frame remain borrowed caller-owned storage. */
int nw_decode(const uint8_t *bytes, size_t length, nw_cmd *scratch,
              size_t scratch_count, nw_frame *out);

/* Text/marker payload. Returns the length and points `text` at pool bytes --
 * NOT NUL-terminated, so callers copy before handing it to a C string API. */
uint32_t nw_text_of(const nw_frame *frame, const nw_cmd *cmd, const uint8_t **text);

#define NW_ANCHOR_OF(cmd) (((cmd)->len >> 24) & 0xffu)

#endif
