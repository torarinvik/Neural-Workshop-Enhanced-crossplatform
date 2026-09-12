/* Neural Workshop — native desktop shell (SDL3).
 *
 * The third renderer for the same display list: shells/web draws it on a 2D
 * canvas, shells/python draws it with pyglet, this draws it with SDL3. None of
 * them contain game logic — the Elisa core decides what a frame contains and
 * every shell only turns commands into pixels. A verdict is a COMMAND here too,
 * not a colour the shell picked.
 *
 * Build: scripts/build_sdl3.sh
 */
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "display_list.h"

/* The core's C ABI, the same surface the wasm build exports (src/wasm/
 * wasm_exports.elisa). Everything is scalar: aggregates do not cross it. */
extern int64_t nw_frame_alloc(int64_t size);
extern int64_t nw_frame_write(int64_t dest, int64_t capacity, int64_t trial,
                              int64_t nback, int64_t position, int64_t verdict);
extern int64_t nw_session_frame_write(int64_t dest, int64_t capacity, int64_t trial,
                                      int64_t nback, int64_t seed, int64_t mode,
                                      int64_t verdict);
extern int64_t nw_batch_write(int64_t dest, int64_t capacity, int64_t trial,
                              int64_t nback, int64_t seed, int64_t mode,
                              int64_t black, int64_t started, int64_t hide_text,
                              int64_t paused, int64_t grid_3d, int64_t expanded,
                              int64_t gridlines, int64_t old_style,
                              int64_t sharp_corners, int64_t session_number,
                              int64_t verdict, int64_t input_answer);

#define FRAME_CAPACITY 65536
#define MAX_COMMANDS   1024
#define DEBUG_GLYPH_PX 8.0f   /* SDL_RenderDebugText's fixed 8x8 cell */

/* Reference space (y UP, origin bottom-left) -> window pixels (y DOWN), letterboxed. */
typedef struct { float scale, offset_x, offset_y, height; } nw_view;

static nw_view view_for(int width, int height) {
    nw_view v;
    float sx = (float)width / NW_REFERENCE_WIDTH;
    float sy = (float)height / NW_REFERENCE_HEIGHT;
    v.scale = sx < sy ? sx : sy;
    v.offset_x = ((float)width - NW_REFERENCE_WIDTH * v.scale) * 0.5f;
    v.offset_y = ((float)height - NW_REFERENCE_HEIGHT * v.scale) * 0.5f;
    v.height = (float)height;
    return v;
}
static float vx(const nw_view *v, float x) { return v->offset_x + x * v->scale; }
static float vy(const nw_view *v, float y) { return v->height - v->offset_y - y * v->scale; }

static void set_color(SDL_Renderer *r, uint32_t rgba) {
    SDL_SetRenderDrawColor(r, (rgba >> 24) & 255, (rgba >> 16) & 255,
                           (rgba >> 8) & 255, rgba & 255);
}

/* A filled rect in reference space. y is the BOTTOM edge there and the TOP edge
 * here, which is the whole of the flip for an axis-aligned box. */
static SDL_FRect rect_of(const nw_view *v, float x, float y, float w, float h) {
    SDL_FRect out;
    out.x = vx(v, x);
    out.y = vy(v, y + h);
    out.w = w * v->scale;
    out.h = h * v->scale;
    return out;
}

static void fill_circle(SDL_Renderer *r, const nw_view *v, float cx, float cy,
                        float radius, uint32_t color) {
    enum { SEGMENTS = 48 };
    SDL_Vertex verts[SEGMENTS + 1];
    int indices[SEGMENTS * 3];
    SDL_FColor c = { ((color >> 24) & 255) / 255.0f, ((color >> 16) & 255) / 255.0f,
                     ((color >> 8) & 255) / 255.0f, (color & 255) / 255.0f };
    verts[0].position.x = vx(v, cx);
    verts[0].position.y = vy(v, cy);
    verts[0].color = c;
    verts[0].tex_coord.x = verts[0].tex_coord.y = 0.0f;
    for (int i = 0; i < SEGMENTS; i++) {
        float t = (float)i / SEGMENTS * 2.0f * SDL_PI_F;
        verts[i + 1].position.x = vx(v, cx + SDL_cosf(t) * radius);
        verts[i + 1].position.y = vy(v, cy + SDL_sinf(t) * radius);
        verts[i + 1].color = c;
        verts[i + 1].tex_coord.x = verts[i + 1].tex_coord.y = 0.0f;
        indices[i * 3 + 0] = 0;
        indices[i * 3 + 1] = i + 1;
        indices[i * 3 + 2] = (i + 1) % SEGMENTS + 1;
    }
    SDL_RenderGeometry(r, NULL, verts, SEGMENTS + 1, indices, SEGMENTS * 3);
}

static void fill_triangle(SDL_Renderer *r, const nw_view *v, float x1, float y1,
                          float x2, float y2, float x3, float y3, uint32_t color) {
    SDL_FColor c = { ((color >> 24) & 255) / 255.0f, ((color >> 16) & 255) / 255.0f,
                     ((color >> 8) & 255) / 255.0f, (color & 255) / 255.0f };
    SDL_Vertex verts[3];
    float xs[3] = { x1, x2, x3 }, ys[3] = { y1, y2, y3 };
    for (int i = 0; i < 3; i++) {
        verts[i].position.x = vx(v, xs[i]);
        verts[i].position.y = vy(v, ys[i]);
        verts[i].color = c;
        verts[i].tex_coord.x = verts[i].tex_coord.y = 0.0f;
    }
    SDL_RenderGeometry(r, NULL, verts, 3, NULL, 0);
}

/* An arc as a polyline; SDL3 has no arc primitive. Angles are DEGREES, CCW,
 * matching the canvas shell. */
static void stroke_arc(SDL_Renderer *r, const nw_view *v, float cx, float cy,
                       float radius, float start_deg, float sweep_deg) {
    enum { SEGMENTS = 48 };
    float prev_x = 0, prev_y = 0;
    for (int i = 0; i <= SEGMENTS; i++) {
        float t = (start_deg + sweep_deg * (float)i / SEGMENTS) * SDL_PI_F / 180.0f;
        float x = vx(v, cx + SDL_cosf(t) * radius);
        float y = vy(v, cy + SDL_sinf(t) * radius);
        if (i > 0) SDL_RenderLine(r, prev_x, prev_y, x, y);
        prev_x = x; prev_y = y;
    }
}

/* SDL_RenderDebugText draws at a fixed 8px cell, so the display list's font size
 * is applied with SDL_SetRenderScale and the position divided back out. The
 * anchor codes match display-list.js's ANCHORS table exactly. */
static void draw_text(SDL_Renderer *r, const nw_view *v, const char *text,
                      float x, float y, float size, uint32_t color, uint8_t anchor) {
    size_t chars = strlen(text);
    float px = size * v->scale / DEBUG_GLYPH_PX;   /* glyph scale factor */
    float w = (float)chars * DEBUG_GLYPH_PX * px;
    float h = DEBUG_GLYPH_PX * px;
    float sx = vx(v, x), sy = vy(v, y);

    switch (anchor % 3) {                 /* 0 left, 1 center, 2 right */
        case 1: sx -= w * 0.5f; break;
        case 2: sx -= w;        break;
    }
    switch (anchor / 3) {                 /* 0 bottom, 1 middle, 2 top */
        case 0: sy -= h;        break;
        case 1: sy -= h * 0.5f; break;
    }

    set_color(r, color);
    SDL_SetRenderScale(r, px, px);
    SDL_RenderDebugText(r, sx / px, sy / px, text);
    SDL_SetRenderScale(r, 1.0f, 1.0f);
}

typedef struct { int verdict; int sounds; char last_marker[64]; } nw_events;

static void render_frame(SDL_Renderer *r, const nw_view *v, const nw_frame *frame,
                         nw_events *events) {
    /* POLYGON announces a vertex count; the POLY_POINTs that follow are its
     * vertices. Fanned from the first point, which is what the canvas shell's
     * closePath+fill does for the convex shapes the core emits. */
    int poly_remaining = 0;
    uint32_t poly_color = 0;
    float poly_x0 = 0, poly_y0 = 0, poly_prev_x = 0, poly_prev_y = 0;
    int poly_seen = 0;
    int poly_open = 0;   /* a MULTILINE run: stroked and open, not filled */
    char text_buffer[512];

    events->verdict = -1;
    events->sounds = 0;
    events->last_marker[0] = '\0';

    for (uint32_t i = 0; i < frame->count; i++) {
        const nw_cmd *cmd = &frame->commands[i];
        switch (cmd->kind) {
        case NW_RECT: {
            /* `e`, `f` are the anchor inside the rectangle and `ref` carries
             * the BITS of the angle about it. Both are zero for all but two
             * screens, so the ordinary rectangle stays one FillRect. */
            float turn = nw_bits_to_f32(cmd->ref);
            if (turn == 0.0f && cmd->e == 0.0f && cmd->f == 0.0f) {
                set_color(r, cmd->color);
                SDL_FRect box = rect_of(v, cmd->a, cmd->b, cmd->c, cmd->d);
                SDL_RenderFillRect(r, &box);
                break;
            }
            /* Clockwise about the anchor, which is what pyglet's `rotation`
             * means and what the recorder the core was checked against read
             * back. Reference space is y-up, so clockwise is the NEGATIVE
             * mathematical direction. */
            float rad = turn * 3.14159265358979323846f / 180.0f;
            float co = SDL_cosf(rad), si = SDL_sinf(rad);
            float lx[4] = { -cmd->e, cmd->c - cmd->e, cmd->c - cmd->e, -cmd->e };
            float ly[4] = { -cmd->f, -cmd->f, cmd->d - cmd->f, cmd->d - cmd->f };
            float px[4], py[4];
            for (int k = 0; k < 4; k++) {
                px[k] = cmd->a + lx[k] * co + ly[k] * si;
                py[k] = cmd->b - lx[k] * si + ly[k] * co;
            }
            fill_triangle(r, v, px[0], py[0], px[1], py[1], px[2], py[2], cmd->color);
            fill_triangle(r, v, px[0], py[0], px[2], py[2], px[3], py[3], cmd->color);
            break;
        }
        case NW_BORDERED_RECT: {
            SDL_FRect box = rect_of(v, cmd->a, cmd->b, cmd->c, cmd->d);
            set_color(r, cmd->color);
            SDL_RenderFillRect(r, &box);
            set_color(r, cmd->ref);          /* border colour rides in `ref` */
            SDL_RenderRect(r, &box);
            break;
        }
        case NW_BOX: {
            set_color(r, cmd->color);
            SDL_FRect box = rect_of(v, cmd->a, cmd->b, cmd->c, cmd->d);
            SDL_RenderRect(r, &box);
            break;
        }
        case NW_CIRCLE:
            fill_circle(r, v, cmd->a, cmd->b, cmd->c, cmd->color);
            break;
        case NW_ARC:
            set_color(r, cmd->color);
            stroke_arc(r, v, cmd->a, cmd->b, cmd->c, cmd->e, cmd->f);
            break;
        case NW_LINE:
            set_color(r, cmd->color);
            SDL_RenderLine(r, vx(v, cmd->a), vy(v, cmd->b), vx(v, cmd->c), vy(v, cmd->d));
            break;
        case NW_TRIANGLE:
            fill_triangle(r, v, cmd->a, cmd->b, cmd->c, cmd->d, cmd->e, cmd->f, cmd->color);
            break;
        case NW_POLYGON:
            poly_remaining = (int)cmd->len;
            poly_color = cmd->color;
            poly_seen = 0;
            poly_open = 0;
            break;
        case NW_MULTILINE:
            /* The same header-and-points shape as a polygon, drawn as an OPEN
             * stroked run. Thickness is not honoured: SDL_RenderLine draws one
             * pixel, and a wide run wants a quad per segment. Named here
             * rather than pretended away. */
            poly_remaining = (int)cmd->len;
            poly_color = cmd->color;
            poly_seen = 0;
            poly_open = 1;
            break;
        case NW_STAR: {
            /* `spikes` points alternating outer and inner radius, the first
             * one straight up and turned by `f` degrees -- pyglet's Star. */
            int spikes = (int)(cmd->e + 0.5f);
            if (spikes < 2) break;
            float base = cmd->f * 3.14159265358979323846f / 180.0f;
            float step = 3.14159265358979323846f / (float)spikes;
            float prev_x = 0.0f, prev_y = 0.0f;
            for (int k = 0; k <= spikes * 2; k++) {
                float radius = (k % 2 == 0) ? cmd->c : cmd->d;
                float turn = base + (float)k * step;
                float px = cmd->a + radius * SDL_sinf(turn);
                float py = cmd->b + radius * SDL_cosf(turn);
                if (k > 0) {
                    fill_triangle(r, v, cmd->a, cmd->b, prev_x, prev_y, px, py,
                                  cmd->color);
                }
                prev_x = px; prev_y = py;
            }
            break;
        }
        case NW_POLY_POINT:
            if (poly_remaining > 0) {
                if (poly_open) {
                    if (poly_seen > 0) {
                        set_color(r, poly_color);
                        SDL_RenderLine(r, vx(v, poly_prev_x), vy(v, poly_prev_y),
                                       vx(v, cmd->a), vy(v, cmd->b));
                    }
                } else {
                    if (poly_seen == 0) { poly_x0 = cmd->a; poly_y0 = cmd->b; }
                    else if (poly_seen >= 2) {
                        fill_triangle(r, v, poly_x0, poly_y0, poly_prev_x, poly_prev_y,
                                      cmd->a, cmd->b, poly_color);
                    }
                }
                poly_prev_x = cmd->a; poly_prev_y = cmd->b;
                poly_seen++;
                if (--poly_remaining == 0) { poly_seen = 0; poly_open = 0; }
            }
            break;
        case NW_TEXT: {
            const uint8_t *text;
            uint32_t len = nw_text_of(frame, cmd, &text);
            if (text && len < sizeof text_buffer) {
                memcpy(text_buffer, text, len);
                text_buffer[len] = '\0';
                draw_text(r, v, text_buffer, cmd->a, cmd->b, cmd->c, cmd->color,
                          NW_ANCHOR_OF(cmd));
            }
            break;
        }
        case NW_VERDICT:
            events->verdict = (int)cmd->ref;
            break;
        case NW_SOUND:
            events->sounds++;              /* audio is a later phase */
            break;
        case NW_MARKER: {
            const uint8_t *text;
            uint32_t len = nw_text_of(frame, cmd, &text);
            if (text && len < sizeof events->last_marker) {
                memcpy(events->last_marker, text, len);
                events->last_marker[len] = '\0';
            }
            break;
        }
        case NW_SPRITE:
        case NW_SPRITE_FIT:
        default:
            break;                          /* no atlas yet */
        }
    }
}

/* Headless verification: decode N frames through the SAME code the window path
 * uses and report what came back. No SDL_Init, so it runs anywhere -- CI, a
 * terminal over ssh, a machine with no display. Without this, "it compiles" was
 * the only claim the shell could make about itself. */
static int selftest(int frames) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    if (!buffer) { printf("selftest: nw_frame_alloc failed\n"); return 1; }

    nw_cmd scratch[MAX_COMMANDS];
    nw_events events = { -1, 0, { 0 } };
    int64_t trial = 1, seed = 1, mode = 2, verdict = -1;
    int bad = 0;

    for (int i = 0; i < frames; i++) {
        int64_t length = nw_batch_write(buffer, FRAME_CAPACITY, trial, 2,
                                        seed, mode, 0, 1, 0, 0, 0, 0, 1, 0,
                                        0, 0, verdict, 0);
        nw_frame frame;
        if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer, (size_t)length,
                                      scratch, MAX_COMMANDS, &frame)) {
            printf("frame %lld: DECODE FAILED (%lld bytes)\n",
                   (long long)trial, (long long)length);
            bad++;
        } else {
            /* Count text commands and confirm the pool strings survived: the
             * wasm build corrupted exactly these while geometry stayed correct,
             * so a shell that only checked command COUNT would have passed. */
            int texts = 0, markers = 0;
            for (uint32_t c = 0; c < frame.count; c++) {
                if (frame.commands[c].kind == NW_TEXT) texts++;
                if (frame.commands[c].kind == NW_MARKER) markers++;
            }
            if (i == 0 || i == frames - 1) {
                printf("frame %-3lld  bytes=%-4lld cmds=%-3u text=%d marker=%d",
                       (long long)trial, (long long)length, frame.count, texts, markers);
                for (uint32_t c = 0; c < frame.count; c++) {
                    const nw_cmd *cmd = &frame.commands[c];
                    if (cmd->kind != NW_TEXT) continue;
                    /* Low 24 bits are the length; the top byte is the anchor. */
                    uint32_t n = cmd->len & 0xffffffu;
                    if (cmd->ref + n <= frame.pool_len) {
                        printf(" \"%.*s\"", (int)n, (const char *)frame.pool + cmd->ref);
                    } else {
                        printf(" <pool overrun ref=%u len=%u of %u>",
                               cmd->ref, n, frame.pool_len);
                        bad++;
                    }
                }
                printf("\n");
            }
            if (texts == 0) { printf("frame %lld: NO TEXT COMMANDS\n", (long long)trial); bad++; }
        }
        trial += 1;
    }
    printf("selftest: %d frames, %d bad\n", frames, bad);
    return bad ? 1 : 0;
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--selftest") == 0) {
        return selftest(argc > 2 ? atoi(argv[2]) : 180);
    }
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        SDL_Log("SDL_Init failed: %s", SDL_GetError());
        return 1;
    }
    SDL_Window *window = SDL_CreateWindow("Neural Workshop",
        (int)NW_REFERENCE_WIDTH, (int)NW_REFERENCE_HEIGHT, SDL_WINDOW_RESIZABLE);
    if (!window) { SDL_Log("CreateWindow: %s", SDL_GetError()); SDL_Quit(); return 1; }

    SDL_Renderer *renderer = SDL_CreateRenderer(window, NULL);
    if (!renderer) { SDL_Log("CreateRenderer: %s", SDL_GetError()); SDL_Quit(); return 1; }
    SDL_SetRenderDrawBlendMode(renderer, SDL_BLENDMODE_BLEND);

    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    if (!buffer) { SDL_Log("nw_frame_alloc failed"); SDL_Quit(); return 1; }

    nw_cmd scratch[MAX_COMMANDS];
    nw_events events = { -1, 0, { 0 } };

    /* The same seeded session path used by the web and Python shells. */
    int64_t trial = 1, seed = 1, mode = 2, verdict = -1;
    Uint64 last_step = SDL_GetTicks();
    bool playing = false, running = true;

    while (running) {
        SDL_Event event;
        bool step = false;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) running = false;
            if (event.type == SDL_EVENT_KEY_DOWN) {
                if (event.key.key == SDLK_ESCAPE || event.key.key == SDLK_Q) running = false;
                if (event.key.key == SDLK_SPACE) playing = !playing;
                if (event.key.key == SDLK_RIGHT) step = true;
            }
        }
        if (playing && SDL_GetTicks() - last_step > 700) { step = true; last_step = SDL_GetTicks(); }
        if (step) {
            trial += 1;
        }

        int64_t length = nw_batch_write(buffer, FRAME_CAPACITY, trial, 2,
                                        seed, mode, 0, 1, 0, 0, 0, 0, 1, 0,
                                        0, 0, verdict, 0);
        int width = 0, height = 0;
        SDL_GetWindowSizeInPixels(window, &width, &height);
        nw_view v = view_for(width, height);

        SDL_SetRenderDrawColor(renderer, 20, 22, 26, 255);
        SDL_RenderClear(renderer);

        nw_frame frame;
        if (length > 0 && nw_decode((const uint8_t *)(uintptr_t)buffer, (size_t)length,
                                    scratch, MAX_COMMANDS, &frame)) {
            render_frame(renderer, &v, &frame, &events);
        } else {
            SDL_Log("frame %lld: decode failed (%lld bytes)", (long long)trial, (long long)length);
        }
        SDL_RenderPresent(renderer);
        SDL_Delay(16);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
