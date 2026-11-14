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
#include <errno.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#endif
#include "display_list.h"

/* The core's C ABI, the same surface the wasm build exports (src/wasm/
 * wasm_exports.elisa). Everything is scalar: aggregates do not cross it. */
extern int64_t nw_frame_alloc(int64_t size);
extern int64_t nw_title_write(int64_t dest, int64_t capacity, int64_t banner_code,
                              int64_t black_background, int64_t jaeggi_mode,
                              int64_t clinical_mode);
extern int64_t nw_taskhub_write(int64_t dest, int64_t capacity, int64_t category,
                                int64_t selected, int64_t black,
                                int64_t width, int64_t height);
extern int64_t nw_you_are_here_create(int64_t rung, int64_t trials,
                                      int64_t adaptive, int64_t show_marks,
                                      int64_t seed);
extern int64_t nw_you_are_here_action(int64_t handle, int64_t action,
                                      int64_t now_ms);
extern int64_t nw_you_are_here_info(int64_t handle, int64_t field);
extern int64_t nw_you_are_here_frame_write(int64_t dest, int64_t capacity,
                                           int64_t handle, int64_t black,
                                           int64_t width, int64_t height);
extern int64_t nw_you_are_here_destroy(int64_t handle);
extern int64_t nw_sokoban_create(int64_t rung, int64_t trials,
                                 int64_t adaptive, int64_t show_traps,
                                 int64_t seed);
extern int64_t nw_sokoban_action(int64_t handle, int64_t action,
                                 int64_t now_ms);
extern int64_t nw_sokoban_info(int64_t handle, int64_t field);
extern int64_t nw_sokoban_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_sokoban_destroy(int64_t handle);
extern int64_t nw_monkey_ladder_create(int64_t grid, int64_t start_level,
                                       int64_t adaptive, int64_t show_ms,
                                       int64_t per_tile_ms, int64_t reveal,
                                       int64_t seed);
extern int64_t nw_monkey_ladder_action(int64_t handle, int64_t action,
                                       int64_t value, int64_t now_ms);
extern int64_t nw_monkey_ladder_info(int64_t handle, int64_t field);
extern int64_t nw_monkey_ladder_frame_write(int64_t dest, int64_t capacity,
                                            int64_t handle, int64_t black,
                                            int64_t width, int64_t height);
extern int64_t nw_monkey_ladder_destroy(int64_t handle);
extern int64_t nw_nback3d_create(int64_t nback, int64_t cubes, int64_t total_trials,
                                 int64_t interval_ms, int64_t stimulus_ms,
                                 int64_t feedback_ms, int64_t seed);
extern int64_t nw_nback3d_action(int64_t handle, int64_t action,
                                 int64_t value, int64_t now_ms);
extern int64_t nw_nback3d_info(int64_t handle, int64_t field);
extern int64_t nw_nback3d_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_nback3d_destroy(int64_t handle);
extern int64_t nw_marble_create(int64_t start_rung, int64_t trials,
                                int64_t adaptive, int64_t feedback_ms,
                                int64_t time_override_ms, int64_t seed);
extern int64_t nw_marble_action(int64_t handle, int64_t action,
                                int64_t value, int64_t aux);
extern int64_t nw_marble_release(int64_t handle, int64_t key);
extern int64_t nw_marble_advance(int64_t handle, int64_t elapsed_ms);
extern int64_t nw_marble_info(int64_t handle, int64_t field);
extern int64_t nw_marble_board_write(int64_t dest, int64_t capacity,
                                     int64_t rung, int64_t seed);
extern int64_t nw_marble_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_marble_destroy(int64_t handle);
static void marble_handle_start_key(int64_t handle, SDL_Keycode key) {
    if (key != SDLK_SPACE) return;
    int64_t phase = nw_marble_info(handle, 0);
    nw_marble_action(handle, phase == 2 ? 5 : 0, 0, 0);
}
static void marble_release_all(int64_t handle) {
    if (!handle) return;
    nw_marble_release(handle, 3);
    nw_marble_release(handle, 4);
    nw_marble_release(handle, 5);
    nw_marble_release(handle, 6);
}
extern int64_t nw_tetris_create(int64_t rung, int64_t pieces,
                                int64_t queue, int64_t seed);
extern int64_t nw_tetris_action(int64_t handle, int64_t action);
extern int64_t nw_tetris_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_tetris_destroy(int64_t handle);
extern int64_t nw_count_create(int64_t kind, int64_t start_count,
                               int64_t trials, int64_t exposure_ms,
                               int64_t adaptive, int64_t show_answer,
                               int64_t seed);
extern int64_t nw_count_action(int64_t handle, int64_t action,
                               int64_t value, int64_t now_ms);
extern int64_t nw_count_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_count_info(int64_t handle, int64_t field);
extern int64_t nw_count_frame_write(int64_t dest, int64_t capacity,
                                    int64_t handle, int64_t black,
                                    int64_t width, int64_t height);
extern int64_t nw_count_destroy(int64_t handle);
extern int64_t nw_mr_time_create(int64_t mode, int64_t rung, int64_t trials,
                                  int64_t max_gap_ms, int64_t flash_ms,
                                  int64_t adaptive, int64_t seed);
extern int64_t nw_mr_time_action(int64_t handle, int64_t action,
                                  int64_t value, int64_t now_ms);
extern int64_t nw_mr_time_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_mr_time_info(int64_t handle, int64_t field);
extern int64_t nw_mr_time_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_mr_time_destroy(int64_t handle);
extern int64_t nw_graph_mapping_create(int64_t nodes, int64_t density,
                                        int64_t trials, int64_t exposure_ms,
                                        int64_t adaptive, int64_t subtle,
                                        int64_t seed);
extern int64_t nw_graph_mapping_action(int64_t handle, int64_t action,
                                       int64_t now_ms);
extern int64_t nw_graph_mapping_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_graph_mapping_info(int64_t handle, int64_t field);
extern int64_t nw_graph_mapping_frame_write(int64_t dest, int64_t capacity,
                                            int64_t handle, int64_t black,
                                            int64_t width, int64_t height);
extern int64_t nw_graph_mapping_destroy(int64_t handle);
extern int64_t nw_matrix_reasoning_create(int64_t level, int64_t trials,
                                          int64_t exposure_ms, int64_t adaptive,
                                          int64_t flags, int64_t color,
                                          int64_t seed);
extern int64_t nw_matrix_reasoning_action(int64_t handle, int64_t action,
                                          int64_t value, int64_t now_ms);
extern int64_t nw_matrix_reasoning_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_matrix_reasoning_info(int64_t handle, int64_t field);
extern int64_t nw_matrix_reasoning_frame_write(int64_t dest, int64_t capacity,
                                               int64_t handle, int64_t black,
                                               int64_t width, int64_t height);
extern int64_t nw_matrix_reasoning_destroy(int64_t handle);
extern int64_t nw_in_the_dark_create(int64_t rung, int64_t trials,
                                     int64_t room_ms, int64_t adaptive,
                                     int64_t seed);
extern int64_t nw_in_the_dark_action(int64_t handle, int64_t action,
                                     int64_t value, int64_t now_ms);
extern int64_t nw_in_the_dark_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_in_the_dark_info(int64_t handle, int64_t field);
extern int64_t nw_in_the_dark_frame_write(int64_t dest, int64_t capacity,
                                          int64_t handle, int64_t black,
                                          int64_t width, int64_t height);
extern int64_t nw_in_the_dark_destroy(int64_t handle);
extern int64_t nw_fog_create(int64_t radius, int64_t moves_allowed,
                             int64_t trials, int64_t persist, int64_t seed);
extern int64_t nw_fog_action(int64_t handle, int64_t action);
extern int64_t nw_fog_info(int64_t handle, int64_t field);
extern int64_t nw_fog_frame_write(int64_t dest, int64_t capacity,
                                  int64_t handle, int64_t black,
                                  int64_t width, int64_t height);
extern int64_t nw_fog_destroy(int64_t handle);
extern int64_t nw_removals_create(int64_t start_rung, int64_t trials,
                                  int64_t move_ms, int64_t adaptive,
                                  int64_t seed);
extern int64_t nw_removals_action(int64_t handle, int64_t action,
                                  int64_t value, int64_t now_ms);
extern int64_t nw_removals_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_removals_info(int64_t handle, int64_t field);
extern int64_t nw_removals_frame_write(int64_t dest, int64_t capacity,
                                       int64_t handle, int64_t black,
                                       int64_t width, int64_t height);
extern int64_t nw_removals_destroy(int64_t handle);
extern int64_t nw_custody_create(int64_t start_rung, int64_t trials,
                                 int64_t belt_ms, int64_t mark_ms,
                                 int64_t adaptive, int64_t seed);
extern int64_t nw_custody_action(int64_t handle, int64_t action,
                                 int64_t value, int64_t now_ms);
extern int64_t nw_custody_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_custody_info(int64_t handle, int64_t field);
extern int64_t nw_custody_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_custody_destroy(int64_t handle);
extern int64_t nw_concentration_create(int64_t pairs, int64_t medium,
                                       int64_t peek_ms, int64_t hide_ms,
                                       int64_t show_turns, int64_t coach,
                                       int64_t seed);
extern int64_t nw_concentration_action(int64_t handle, int64_t action,
                                       int64_t value, int64_t now_ms);
extern int64_t nw_concentration_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_concentration_info(int64_t handle, int64_t field);
extern int64_t nw_concentration_frame_write(int64_t dest, int64_t capacity,
                                            int64_t handle, int64_t black,
                                            int64_t width, int64_t height);
extern int64_t nw_concentration_destroy(int64_t handle);
extern int64_t nw_recognition_create(int64_t total_trials, int64_t medium,
                                     int64_t repeat_percent, int64_t min_lag,
                                     int64_t study_ms, int64_t feedback,
                                     int64_t seed);
extern int64_t nw_recognition_action(int64_t handle, int64_t action,
                                     int64_t value, int64_t now_ms);
extern int64_t nw_recognition_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_recognition_info(int64_t handle, int64_t field);
extern int64_t nw_recognition_frame_write(int64_t dest, int64_t capacity,
                                          int64_t handle, int64_t black,
                                          int64_t width, int64_t height);
extern int64_t nw_recognition_destroy(int64_t handle);
extern int64_t nw_trivia_create(int64_t start_rung, int64_t total_trials,
                                int64_t show_answer, int64_t adaptive,
                                int64_t seed);
extern int64_t nw_trivia_action(int64_t handle, int64_t action, int64_t value);
extern int64_t nw_trivia_info(int64_t handle, int64_t field);
extern int64_t nw_trivia_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_trivia_destroy(int64_t handle);
extern int64_t nw_reflex_create(int64_t total_targets, int64_t lifetime_ms,
                                int64_t spawn_gap_ms, int64_t max_active,
                                int64_t start_size, int64_t adaptive,
                                int64_t seed);
extern int64_t nw_reflex_action(int64_t handle, int64_t action,
                                int64_t value, int64_t now_ms);
extern int64_t nw_reflex_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_reflex_info(int64_t handle, int64_t field);
extern int64_t nw_reflex_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_reflex_pointer(int64_t handle, int64_t x_millionths,
                                 int64_t y_millionths, int64_t now_ms);
extern int64_t nw_reflex_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_reflex_destroy(int64_t handle);
extern int64_t nw_algebra_create(int64_t level, int64_t trials, int64_t seed);
extern int64_t nw_algebra_create_options(int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_numberology_options_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_algebra_options_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_algebra_action(int64_t handle, int64_t action,
                                 int64_t value, int64_t now_ms);
extern int64_t nw_algebra_info(int64_t handle, int64_t field);
extern int64_t nw_algebra_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_algebra_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_algebra_destroy(int64_t handle);
extern int64_t nw_numberology_create(int64_t start_level, int64_t trials,
                                     int64_t adaptive, int64_t seed);
extern int64_t nw_numberology_action(int64_t handle, int64_t action,
                                     int64_t value, int64_t now_ms);
extern int64_t nw_numberology_info(int64_t handle, int64_t field);
extern int64_t nw_numberology_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_numberology_frame_write(int64_t dest, int64_t capacity,
                                          int64_t handle, int64_t black,
                                          int64_t width, int64_t height);
extern int64_t nw_numberology_destroy(int64_t handle);
extern int64_t nw_jigsaw_create(int64_t start_side, int64_t puzzles,
                                int64_t adaptive, int64_t preview, int64_t seed);
extern int64_t nw_jigsaw_create_options(int64_t start_side, int64_t puzzles,
                                        int64_t adaptive, int64_t preview,
                                        int64_t mark_placed, int64_t seed);
extern int64_t nw_jigsaw_action(int64_t handle, int64_t action,
                                int64_t value, int64_t now_ms);
extern int64_t nw_jigsaw_info(int64_t handle, int64_t field);
extern int64_t nw_jigsaw_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_jigsaw_pointer(int64_t handle, int64_t x_millionths,
                                 int64_t y_millionths, int64_t width,
                                 int64_t height, int64_t now_ms);
extern int64_t nw_jigsaw_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_jigsaw_destroy(int64_t handle);
extern int64_t nw_sudoku_create(int64_t start_rung, int64_t trials,
                                int64_t show_clashes, int64_t adaptive, int64_t seed);
extern int64_t nw_sudoku_action(int64_t handle, int64_t action,
                                int64_t value, int64_t now_ms);
extern int64_t nw_sudoku_info(int64_t handle, int64_t field);
extern int64_t nw_sudoku_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_sudoku_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_sudoku_destroy(int64_t handle);
extern int64_t nw_go_create(int64_t difficulty, int64_t trials, int64_t seed);
extern int64_t nw_go_action(int64_t handle, int64_t action, int64_t value, int64_t now_ms);
extern int64_t nw_go_info(int64_t handle, int64_t field);
extern int64_t nw_go_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_go_pointer(int64_t handle, int64_t x_millionths, int64_t y_millionths,
                             int64_t width, int64_t height, int64_t now_ms);
extern int64_t nw_go_frame_write(int64_t dest, int64_t capacity, int64_t handle,
                                 int64_t black, int64_t width, int64_t height);
extern int64_t nw_go_destroy(int64_t handle);
extern int64_t nw_scrabble_create(int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scramble_create(int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scramble_set_corpus(int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scramble_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scramble_info(int64_t, int64_t);
extern int64_t nw_scramble_value(int64_t, int64_t, int64_t);
extern int64_t nw_scramble_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scramble_destroy(int64_t);
extern int64_t nw_scramble_options_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scrabble_set_lexicon(int64_t, int64_t, int64_t);
extern int64_t nw_scrabble_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scrabble_info(int64_t, int64_t);
extern int64_t nw_scrabble_value(int64_t, int64_t, int64_t);
extern int64_t nw_scrabble_pointer(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scrabble_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_scrabble_destroy(int64_t);
extern int64_t nw_scrabble_options_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_crossword_create(int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_crossword_set_lexicon(int64_t, int64_t, int64_t);
extern int64_t nw_crossword_action(int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_crossword_info(int64_t, int64_t);
extern int64_t nw_crossword_pointer(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_crossword_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_crossword_destroy(int64_t);
extern int64_t nw_crossword_options_frame_write(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
extern int64_t nw_crossed_wires_create(int64_t start_rung, int64_t trials,
                                       int64_t adaptive, int64_t show_grid,
                                       int64_t seed);
extern int64_t nw_crossed_wires_action(int64_t handle, int64_t action,
                                       int64_t value, int64_t now_ms);
extern int64_t nw_crossed_wires_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_crossed_wires_info(int64_t handle, int64_t field);
extern int64_t nw_crossed_wires_frame_write(int64_t dest, int64_t capacity,
                                            int64_t handle, int64_t black,
                                            int64_t width, int64_t height);
extern int64_t nw_crossed_wires_destroy(int64_t handle);
extern int64_t nw_ncup_monte_create(int64_t start_cups, int64_t max_cups,
                                    int64_t adaptive, int64_t swap_count,
                                    int64_t swap_ms, int64_t reveal_ms, int64_t seed);
extern int64_t nw_ncup_monte_action(int64_t handle, int64_t action, int64_t value, int64_t now_ms);
extern int64_t nw_ncup_monte_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_ncup_monte_info(int64_t handle, int64_t field);
extern int64_t nw_ncup_monte_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_ncup_monte_pointer(int64_t handle, int64_t x_millionths, int64_t y_millionths, int64_t now_ms);
extern int64_t nw_ncup_monte_frame_write(int64_t dest, int64_t capacity, int64_t handle,
                                         int64_t black, int64_t width, int64_t height);
extern int64_t nw_ncup_monte_destroy(int64_t handle);
extern int64_t nw_tracking_create(int64_t balls, int64_t targets, int64_t seconds,
                                  int64_t speed, int64_t rounds, int64_t adaptive, int64_t seed);
extern int64_t nw_tracking_action(int64_t handle, int64_t action, int64_t value, int64_t now_ms);
extern int64_t nw_tracking_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_tracking_info(int64_t handle, int64_t field);
extern int64_t nw_tracking_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_tracking_pointer(int64_t handle, int64_t x_millionths, int64_t y_millionths, int64_t now_ms);
extern int64_t nw_tracking_frame_write(int64_t dest, int64_t capacity, int64_t handle,
                                       int64_t black, int64_t width, int64_t height);
extern int64_t nw_tracking_destroy(int64_t handle);
extern int64_t nw_lookout_create(int64_t start_count, int64_t watching,
                                 int64_t speed, int64_t morph_ms,
                                 int64_t total_cues, int64_t adaptive,
                                 int64_t seed);
extern int64_t nw_lookout_action(int64_t handle, int64_t action,
                                 int64_t value, int64_t now_ms);
extern int64_t nw_lookout_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_lookout_info(int64_t handle, int64_t field);
extern int64_t nw_lookout_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_lookout_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_lookout_destroy(int64_t handle);
extern int64_t nw_pursuit_create(int64_t speed, int64_t surge, int64_t turn_ms,
                                 int64_t turn_degrees, int64_t size,
                                 int64_t packed_extra, int64_t seed);
extern int64_t nw_pursuit_action(int64_t handle, int64_t action,
                                 int64_t value, int64_t now_ms);
extern int64_t nw_pursuit_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_pursuit_info(int64_t handle, int64_t field);
extern int64_t nw_pursuit_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_pursuit_pointer(int64_t handle, int64_t x_millionths,
                                  int64_t y_millionths);
extern int64_t nw_pursuit_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_pursuit_destroy(int64_t handle);
extern int64_t nw_out_of_sight_create(int64_t dots, int64_t targets,
                                      int64_t speed, int64_t cross_ms,
                                      int64_t blinds, int64_t packed_extra,
                                      int64_t seed);
extern int64_t nw_out_of_sight_action(int64_t handle, int64_t action,
                                      int64_t value, int64_t now_ms);
extern int64_t nw_out_of_sight_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_out_of_sight_info(int64_t handle, int64_t field);
extern int64_t nw_out_of_sight_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_out_of_sight_frame_write(int64_t dest, int64_t capacity,
                                           int64_t handle, int64_t black,
                                           int64_t width, int64_t height);
extern int64_t nw_out_of_sight_destroy(int64_t handle);
extern int64_t nw_buzz_wire_create(int64_t rung, int64_t trials,
                                   int64_t adaptive, int64_t meter,
                                   int64_t beads, int64_t sight, int64_t seed);
extern int64_t nw_buzz_wire_action(int64_t handle, int64_t action,
                                   int64_t value, int64_t now_ms);
extern int64_t nw_buzz_wire_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_buzz_wire_info(int64_t handle, int64_t field);
extern int64_t nw_buzz_wire_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_buzz_wire_frame_write(int64_t dest, int64_t capacity,
                                        int64_t handle, int64_t black,
                                        int64_t width, int64_t height);
extern int64_t nw_buzz_wire_destroy(int64_t handle);
extern int64_t nw_donkey_create(int64_t rung, int64_t trials, int64_t beat_ms,
                                int64_t set_ms, int64_t adaptive,
                                int64_t unused, int64_t seed);
extern int64_t nw_donkey_action(int64_t handle, int64_t action,
                                int64_t value, int64_t now_ms);
extern int64_t nw_donkey_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_donkey_info(int64_t handle, int64_t field);
extern int64_t nw_donkey_frame_write(int64_t dest, int64_t capacity,
                                     int64_t handle, int64_t black,
                                     int64_t width, int64_t height);
extern int64_t nw_donkey_destroy(int64_t handle);
extern int64_t nw_two_hands_create(int64_t rung, int64_t trials, int64_t beat_ms,
                                   int64_t set_ms, int64_t adaptive,
                                   int64_t unused, int64_t seed);
extern int64_t nw_two_hands_action(int64_t handle, int64_t action,
                                   int64_t value, int64_t now_ms);
extern int64_t nw_two_hands_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_two_hands_info(int64_t handle, int64_t field);
extern int64_t nw_two_hands_pointer(int64_t handle, int64_t x_millionths,
                                    int64_t y_millionths, int64_t pressed,
                                    int64_t now_ms);
extern int64_t nw_two_hands_frame_write(int64_t dest, int64_t capacity,
                                        int64_t handle, int64_t black,
                                        int64_t width, int64_t height);
extern int64_t nw_two_hands_destroy(int64_t handle);
extern int64_t nw_overrun_create(int64_t rung, int64_t waves, int64_t adaptive,
                                 int64_t unused_d, int64_t unused_e,
                                 int64_t unused_f, int64_t seed);
extern int64_t nw_overrun_action(int64_t handle, int64_t action,
                                 int64_t value, int64_t now_ms);
extern int64_t nw_overrun_advance(int64_t handle, int64_t now_ms);
extern int64_t nw_overrun_info(int64_t handle, int64_t field);
extern int64_t nw_overrun_value(int64_t handle, int64_t field, int64_t at);
extern int64_t nw_overrun_frame_write(int64_t dest, int64_t capacity,
                                      int64_t handle, int64_t black,
                                      int64_t width, int64_t height);
extern int64_t nw_overrun_destroy(int64_t handle);

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
    char text_buffer[4096];

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
                int rows = 1;
                for (uint32_t j = 0; j < len; j++) if (text_buffer[j] == '\n') rows++;
                int row = 0;
                char *line = text_buffer;
                for (uint32_t j = 0; j <= len; j++) {
                    if (text_buffer[j] != '\n' && text_buffer[j] != '\0') continue;
                    text_buffer[j] = '\0';
                    float line_y = cmd->b + ((rows - 1) * 0.5f - row) * cmd->c * 1.25f;
                    draw_text(r, v, line, cmd->a, line_y, cmd->c, cmd->color,
                              NW_ANCHOR_OF(cmd));
                    line = text_buffer + j + 1;
                    row++;
                }
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
    int64_t trial = 1;
    int bad = 0;

    for (int i = 0; i < frames; i++) {
        int64_t length = nw_title_write(buffer, FRAME_CAPACITY, trial % 4, 0, 1, 1);
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

static int selftest_you_are_here(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int bad = 0;
    int64_t handle = nw_you_are_here_create(1, 1, 0, 1, 17);
    if (!buffer || !handle) {
        printf("3d-maze selftest: allocation failed\n");
        if (handle) nw_you_are_here_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_events events = { -1, 0, { 0 } };
    int64_t length = nw_you_are_here_frame_write(buffer, FRAME_CAPACITY,
                                                  handle, 0, 912, 684);
    nw_frame frame;
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) {
        printf("3d-maze selftest: READY frame decode failed\n");
        bad++;
    }
    int64_t phase_ready = nw_you_are_here_info(handle, 0);
    int64_t start_result = nw_you_are_here_action(handle, 0, 0);
    int64_t phase_walking = nw_you_are_here_info(handle, 0);
    int64_t turn_result = nw_you_are_here_action(handle, 3, 10);
    int64_t steps_after_turn = nw_you_are_here_info(handle, 6);
    if (phase_ready != 0 || start_result != 1 || phase_walking != 1 ||
        turn_result != 1 || steps_after_turn != 1) {
        printf("3d-maze state: ready=%lld start=%lld walking=%lld turn=%lld steps=%lld\n",
               (long long)phase_ready, (long long)start_result,
               (long long)phase_walking, (long long)turn_result,
               (long long)steps_after_turn);
        bad++;
    }
    length = nw_you_are_here_frame_write(buffer, FRAME_CAPACITY, handle,
                                         0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) {
        printf("3d-maze selftest: WALKING frame decode failed\n");
        bad++;
    }
    if (nw_you_are_here_destroy(handle) != 0) bad++;
    (void)events;
    printf("3d-maze selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_taskhub(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    if (!buffer) {
        printf("taskhub selftest: allocation failed\n");
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int bad = 0;
    int64_t length = nw_taskhub_write(buffer, FRAME_CAPACITY, 5, 4,
                                      0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) {
        printf("taskhub selftest: frame decode failed\n");
        bad++;
    } else {
        int texts = 0;
        for (uint32_t c = 0; c < frame.count; c++) {
            const nw_cmd *cmd = &frame.commands[c];
            if (cmd->kind != NW_TEXT) continue;
            texts++;
            uint32_t n = cmd->len & 0xffffffu;
            if (cmd->ref + n > frame.pool_len) bad++;
        }
        if (texts < 3) bad++;
    }
    printf("taskhub selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_sokoban(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_sokoban_create(1, 1, 0, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("sokoban selftest: allocation failed\n");
        if (handle) nw_sokoban_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_sokoban_frame_write(buffer, FRAME_CAPACITY, handle,
                                             0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) {
        printf("sokoban selftest: READY frame decode failed\n");
        bad++;
    }
    nw_sokoban_action(handle, 0, 0);
    int64_t phase = nw_sokoban_info(handle, 0);
    int64_t width = nw_sokoban_info(handle, 8);
    int64_t height = nw_sokoban_info(handle, 9);
    if (phase != 1 || width < 5 || height < 5) {
        printf("sokoban selftest: invalid started state phase=%lld size=%lldx%lld\n",
               (long long)phase, (long long)width, (long long)height);
        bad++;
    }
    nw_sokoban_action(handle, 3, 10);
    nw_sokoban_action(handle, 5, 20);
    nw_sokoban_action(handle, 6, 30);
    length = nw_sokoban_frame_write(buffer, FRAME_CAPACITY, handle,
                                    0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) {
        printf("sokoban selftest: PLAYING frame decode failed\n");
        bad++;
    }
    if (nw_sokoban_destroy(handle) != 0) bad++;
    printf("sokoban selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_monkey_ladder(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_monkey_ladder_create(5, 2, 1, 300, 120, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("monkey ladder selftest: allocation failed\n");
        if (handle) nw_monkey_ladder_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_monkey_ladder_frame_write(buffer, FRAME_CAPACITY,
                                                   handle, 0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_monkey_ladder_info(handle, 0) != 0) bad++;
    nw_monkey_ladder_action(handle, 0, 0, 1000);
    if (nw_monkey_ladder_info(handle, 0) != 1) bad++;
    nw_monkey_ladder_action(handle, 1, 0, 2000);
    if (nw_monkey_ladder_info(handle, 0) != 2) bad++;
    int64_t answer = nw_monkey_ladder_info(handle, 4);
    int64_t cell = nw_monkey_ladder_info(handle, 7);
    (void)cell;
    if (answer < 2 || answer > 25) bad++;
    nw_monkey_ladder_action(handle, 2, 0, 2001);
    length = nw_monkey_ladder_frame_write(buffer, FRAME_CAPACITY, handle,
                                          0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_monkey_ladder_destroy(handle) != 0) bad++;
    printf("monkey ladder selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_nback3d(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_nback3d_create(2, 3, 20, 3000, 500, 200, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("3D N-Back selftest: allocation failed\n");
        if (handle) nw_nback3d_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_nback3d_frame_write(buffer, FRAME_CAPACITY, handle,
                                             0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_nback3d_info(handle, 0) != 0) bad++;
    nw_nback3d_action(handle, 0, 0, 0);
    nw_nback3d_action(handle, 2, 0, 1000);
    if (nw_nback3d_info(handle, 0) != 1 || nw_nback3d_info(handle, 2) != 1) bad++;
    length = nw_nback3d_frame_write(buffer, FRAME_CAPACITY, handle, 0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    nw_nback3d_action(handle, 2, 0, 1600);
    if (nw_nback3d_info(handle, 0) != 2) bad++;
    nw_nback3d_action(handle, 1, 0, 1700);
    if (nw_nback3d_info(handle, 8) != 1) bad++;
    if (nw_nback3d_destroy(handle) != 0) bad++;
    printf("3D N-Back selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_marble(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_marble_create(1, 1, 0, 2600, 15000, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Marble Maze selftest: allocation failed\n");
        if (handle) nw_marble_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_marble_frame_write(buffer, FRAME_CAPACITY, handle,
                                            0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_marble_info(handle, 0) != 0) bad++;
    marble_handle_start_key(handle, SDLK_RETURN);
    if (nw_marble_info(handle, 0) != 0) bad++;
    marble_handle_start_key(handle, SDLK_SPACE);
    if (nw_marble_info(handle, 0) != 1) bad++;
    int64_t board_length = nw_marble_board_write(buffer, FRAME_CAPACITY, 1,
                                                 889418965);
    const uint8_t *board = (const uint8_t *)(uintptr_t)buffer;
    if (board_length < 68 || memcmp(board, "MWC1", 4) != 0 ||
        board[4] != 1 || board[8] != 1 || board[12] != 1) bad++;
    if (nw_marble_action(handle, 6, 0, 0) != 1 ||
        nw_marble_action(handle, 7, 0, 0) != 1 ||
        nw_marble_info(handle, 11) != 3) bad++;
    marble_release_all(handle);
    if (nw_marble_info(handle, 11) != 0) bad++;
    if (nw_marble_advance(handle, 15000) != 1 || nw_marble_info(handle, 0) != 2) bad++;
    length = nw_marble_frame_write(buffer, FRAME_CAPACITY, handle, 0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_marble_destroy(handle) != 0) bad++;
    printf("Marble Maze selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_tetris(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_tetris_create(1, 3, 5, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("tetris selftest: allocation failed\n");
        if (handle) nw_tetris_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_tetris_frame_write(buffer, FRAME_CAPACITY, handle,
                                           0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_tetris_action(handle, 0) != 1) bad++;
    if (nw_tetris_action(handle, 3) != 1) bad++;
    if (nw_tetris_action(handle, 6) != 1) bad++;
    if (nw_tetris_action(handle, 4) != 1) bad++;
    length = nw_tetris_frame_write(buffer, FRAME_CAPACITY, handle,
                                   0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_tetris_destroy(handle) != 0) bad++;
    printf("tetris selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_count(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_count_create(0, 8, 5, 200, 1, 1, 23);
    int bad = 0;
    if (!buffer || !handle) {
        printf("count selftest: allocation failed\n");
        if (handle) nw_count_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_count_frame_write(buffer, FRAME_CAPACITY, handle,
                                          0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_count_info(handle, 0) != 0) bad++;
    if (nw_count_action(handle, 0, 0, 1000) != 1) bad++;
    if (nw_count_info(handle, 0) != 1 || nw_count_info(handle, 2) != 8) bad++;
    if (nw_count_advance(handle, 1200) != 1 || nw_count_info(handle, 0) != 2) bad++;
    if (nw_count_action(handle, 1, 8, 1201) != 1) bad++;
    if (nw_count_action(handle, 3, 0, 1202) != 1 || nw_count_info(handle, 9) != 1) bad++;
    length = nw_count_frame_write(buffer, FRAME_CAPACITY, handle,
                                  0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_count_destroy(handle) != 0) bad++;
    printf("count selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_mr_time(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_mr_time_create(0, 1, 5, 3000, 400, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Mr. Time selftest: allocation failed\n");
        if (handle) nw_mr_time_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_mr_time_frame_write(buffer, FRAME_CAPACITY, handle,
                                             0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_mr_time_info(handle, 0) != 0) bad++;
    nw_mr_time_action(handle, 0, 0, 1000);
    if (nw_mr_time_info(handle, 0) != 1) bad++;
    nw_mr_time_advance(handle, 11000);
    if (nw_mr_time_info(handle, 0) != 3) bad++;
    nw_mr_time_action(handle, 1, 0, 12000);
    nw_mr_time_action(handle, 4, 0, 12001);
    if (nw_mr_time_info(handle, 0) != 5) bad++;
    length = nw_mr_time_frame_write(buffer, FRAME_CAPACITY, handle,
                                    0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_mr_time_destroy(handle) != 0) bad++;
    printf("Mr. Time selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_graph_mapping(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_graph_mapping_create(4, 0, 5, 3000, 1, 0, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Graph Mapping selftest: allocation failed\n");
        if (handle) nw_graph_mapping_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_graph_mapping_frame_write(buffer, FRAME_CAPACITY,
                                                   handle, 0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_graph_mapping_info(handle, 0) != 0) bad++;
    if (nw_graph_mapping_action(handle, 0, 1000) != 1) bad++;
    if (nw_graph_mapping_info(handle, 0) != 1) bad++;
    int64_t truth = nw_graph_mapping_info(handle, 21);
    int64_t choice = truth ? 1 : 2;
    if (nw_graph_mapping_action(handle, choice, 1200) != 1) bad++;
    if (nw_graph_mapping_info(handle, 0) != 3) bad++;
    length = nw_graph_mapping_frame_write(buffer, FRAME_CAPACITY, handle,
                                          0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_graph_mapping_advance(handle, nw_graph_mapping_info(handle, 16)) != 1) bad++;
    if (nw_graph_mapping_info(handle, 0) != 1 || nw_graph_mapping_info(handle, 4) != 2) bad++;
    if (nw_graph_mapping_destroy(handle) != 0) bad++;
    printf("Graph Mapping selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_matrix_reasoning(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_matrix_reasoning_create(1, 5, 0, 1, 1, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Matrix Reasoning selftest: allocation failed\n");
        if (handle) nw_matrix_reasoning_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_matrix_reasoning_frame_write(buffer, FRAME_CAPACITY,
                                                      handle, 0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_matrix_reasoning_info(handle, 0) != 0) bad++;
    if (nw_matrix_reasoning_action(handle, 0, 0, 1000) != 1) bad++;
    if (nw_matrix_reasoning_info(handle, 0) != 1) bad++;
    int64_t answer = nw_matrix_reasoning_info(handle, 6);
    if (answer < 0 || answer >= nw_matrix_reasoning_info(handle, 5)) bad++;
    if (nw_matrix_reasoning_action(handle, 1, answer, 1200) != 1) bad++;
    if (nw_matrix_reasoning_info(handle, 0) != 3) bad++;
    int64_t deadline = nw_matrix_reasoning_info(handle, 21);
    if (nw_matrix_reasoning_advance(handle, deadline) != 1) bad++;
    length = nw_matrix_reasoning_frame_write(buffer, FRAME_CAPACITY, handle,
                                             0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_matrix_reasoning_destroy(handle) != 0) bad++;
    printf("Matrix Reasoning selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_in_the_dark(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_in_the_dark_create(1, 1, 500, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("In the Dark selftest: allocation failed\n");
        if (handle) nw_in_the_dark_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_in_the_dark_frame_write(buffer, FRAME_CAPACITY,
                                                 handle, 0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_in_the_dark_info(handle, 0) != 0) bad++;
    if (nw_in_the_dark_action(handle, 0, 0, 0) != 1) bad++;
    for (int64_t now = 500; now <= 20000 && nw_in_the_dark_info(handle, 0) == 1; now += 500)
        nw_in_the_dark_advance(handle, now);
    if (nw_in_the_dark_info(handle, 0) != 2) bad++;
    int64_t asks = nw_in_the_dark_info(handle, 22);
    for (int64_t at = 0; at < asks; at++) {
        int64_t answer = nw_in_the_dark_info(handle, 16 + at);
        (void)answer;
        nw_in_the_dark_action(handle, 1, 0, 21000 + at);
    }
    length = nw_in_the_dark_frame_write(buffer, FRAME_CAPACITY, handle,
                                        0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_in_the_dark_destroy(handle) != 0) bad++;
    printf("In the Dark selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_fog(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_fog_create(2, 100, 1, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Fog of War selftest: allocation failed\n");
        if (handle) nw_fog_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_fog_frame_write(buffer, FRAME_CAPACITY, handle,
                                        0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_fog_info(handle, 0) != 0) bad++;
    if (nw_fog_action(handle, 0) != 1 || nw_fog_info(handle, 0) != 1) bad++;
    if (nw_fog_info(handle, 6) != 25 || nw_fog_info(handle, 7) != 15) bad++;
    if (nw_fog_action(handle, 2) != 1 || nw_fog_info(handle, 4) != 1) bad++;
    length = nw_fog_frame_write(buffer, FRAME_CAPACITY, handle, 0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_fog_destroy(handle) != 0) bad++;
    printf("Fog of War selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_removals(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_removals_create(1, 1, 500, 1, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Removals selftest: allocation failed\n");
        if (handle) nw_removals_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_removals_frame_write(buffer, FRAME_CAPACITY, handle,
                                             0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_removals_info(handle, 0) != 0) bad++;
    if (nw_removals_action(handle, 0, 0, 0) != 1) bad++;
    for (int64_t now = 500; now <= 25000 && nw_removals_info(handle, 0) == 1; now += 500)
        nw_removals_advance(handle, now);
    if (nw_removals_info(handle, 0) != 2) bad++;
    int64_t asks = nw_removals_info(handle, 13);
    int64_t vans = nw_removals_info(handle, 4);
    for (int64_t at = 0; at < asks; at++)
        nw_removals_action(handle, 1, 0, 30000 + at);
    if (vans <= 0) bad++;
    length = nw_removals_frame_write(buffer, FRAME_CAPACITY, handle,
                                     0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_removals_destroy(handle) != 0) bad++;
    printf("Removals selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_custody(void) {
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_custody_create(1, 1, 900, 1200, 0, 17);
    int bad = 0;
    if (!buffer || !handle) {
        printf("Chain of Custody selftest: allocation failed\n");
        if (handle) nw_custody_destroy(handle);
        return 1;
    }
    nw_cmd scratch[MAX_COMMANDS];
    nw_frame frame;
    int64_t length = nw_custody_frame_write(buffer, FRAME_CAPACITY, handle,
                                            0, 912, 684);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    if (nw_custody_info(handle, 0) != 0) bad++;
    if (nw_custody_action(handle, 0, 0, 0) != 1) bad++;
    nw_custody_advance(handle, 1200);
    if (nw_custody_info(handle, 0) != 2) bad++;
    length = nw_custody_frame_write(buffer, FRAME_CAPACITY, handle,
                                    0, 1280, 720);
    if (length <= 0 || !nw_decode((const uint8_t *)(uintptr_t)buffer,
                                  (size_t)length, scratch, MAX_COMMANDS, &frame)) bad++;
    for (int64_t now = 2100; now <= 50000 && nw_custody_info(handle, 0) == 2; now += 900)
        nw_custody_advance(handle, now);
    if (nw_custody_info(handle, 0) != 3 && nw_custody_info(handle, 0) != 4) bad++;
    if (nw_custody_destroy(handle) != 0) bad++;
    printf("Chain of Custody selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_concentration(void) {
    int bad = 0;
    int64_t handle = nw_concentration_create(4, 0, 0, 900, 1, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_concentration_destroy(handle);
        free(buffer);
        printf("Concentration selftest: allocation failed\n");
        return 1;
    }
    if (nw_concentration_info(handle, 0) != 0) bad++;
    if (nw_concentration_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_concentration_info(handle, 0) != 2) bad++;
    if (nw_concentration_action(handle, 2, 3, 0) != 1) bad++;
    if (nw_concentration_info(handle, 9) != 3) bad++;
    if (nw_concentration_action(handle, 1, 3, 0) != 1) bad++;
    if (nw_concentration_info(handle, 6) != 1) bad++;
    if (nw_concentration_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                      handle, 0, 912, 684) <= 0) bad++;
    if (nw_concentration_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Concentration selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_recognition(void) {
    int bad = 0;
    int64_t handle = nw_recognition_create(10, 0, 40, 4, 500, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_recognition_destroy(handle);
        free(buffer);
        printf("Seen It Before selftest: allocation failed\n");
        return 1;
    }
    if (nw_recognition_info(handle, 0) != 0) bad++;
    if (nw_recognition_action(handle, 0, 0, 100) != 1) bad++;
    if (nw_recognition_info(handle, 0) != 1) bad++;
    if (nw_recognition_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                   handle, 0, 912, 684) <= 0) bad++;
    if (nw_recognition_action(handle, 2, 0, 200) != 1) bad++;
    if (nw_recognition_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Seen It Before selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_trivia(void) {
    int bad = 0;
    int64_t handle = nw_trivia_create(1, 1, 1, 0, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_trivia_destroy(handle);
        free(buffer);
        printf("Trivia selftest: allocation failed\n");
        return 1;
    }
    if (nw_trivia_info(handle, 0) != 0) bad++;
    if (nw_trivia_action(handle, 0, 0) != 1) bad++;
    if (nw_trivia_info(handle, 0) != 1) bad++;
    if (nw_trivia_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                              handle, 0, 912, 684) <= 0) bad++;
    int64_t choice = nw_trivia_info(handle, 6);
    if (nw_trivia_action(handle, 4 + choice, 0) != 1) bad++;
    if (nw_trivia_action(handle, 12, 0) != 1) bad++;
    if (nw_trivia_info(handle, 0) != 3) bad++;
    if (nw_trivia_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Trivia selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_reflex(void) {
    int bad = 0;
    int64_t handle = nw_reflex_create(10, 1200, 400, 3, 100, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_reflex_destroy(handle);
        free(buffer);
        printf("Reflex selftest: allocation failed\n");
        return 1;
    }
    if (nw_reflex_info(handle, 0) != 0) bad++;
    if (nw_reflex_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_reflex_info(handle, 0) != 1) bad++;
    if (nw_reflex_advance(handle, 0) != 1) bad++;
    if (nw_reflex_info(handle, 3) != 3) bad++;
    int64_t x = nw_reflex_value(handle, 1, 0);
    int64_t y = nw_reflex_value(handle, 2, 0);
    if (nw_reflex_pointer(handle, x, y, 100) < 0) bad++;
    if (nw_reflex_info(handle, 9) != 1) bad++;
    if (nw_reflex_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                              handle, 0, 912, 684) <= 0) bad++;
    if (nw_reflex_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Reflex selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_algebra(void) {
    int bad = 0;
    int64_t handle = nw_algebra_create(1, 2, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_algebra_destroy(handle);
        free(buffer);
        printf("Algebra selftest: allocation failed\n");
        return 1;
    }
    if (nw_algebra_info(handle, 0) != 0) bad++;
    if (nw_algebra_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_algebra_info(handle, 0) != 1) bad++;
    if (nw_algebra_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                               handle, 0, 912, 684) <= 0) bad++;
    if (nw_algebra_action(handle, 2, 0, 0) != 2) bad++;
    if (nw_algebra_destroy(handle) != 0) bad++;
    /* Independent source-derived fractional and large CRT feedback cases. */
    static const struct { int level; const char *working; } examples[] = {
        {5, "over 14: 6 + 7\nwhich is 13/14"},
        {12, "the moduli are coprime, so there is one n below 1936894310792171506455569293\nafter mod 44371:  n = 40522 (mod 44371)\nafter mod 31699:  n = 1220287393 (mod 1406516329)\nafter mod 18311:  n = 21173510587830 (mod 25754720500319)\nafter mod 55661:  n = 1208793225472559776 (mod 1433533497768255859)\nafter mod 14249:  n = 4059542125407404896605 (mod 20426418809699877734891)\nafter mod 94823:  n = 1313075539886062647836894758 (mod 1936894310792171506455569293)"}
    };
    for (size_t i = 0; i < sizeof(examples) / sizeof(examples[0]); i++) {
        handle = nw_algebra_create(examples[i].level, 1, 19);
        if (!handle) { bad++; continue; }
        if (nw_algebra_action(handle, 0, 0, 0) != 1 || nw_algebra_info(handle, 11) != 0 ||
            nw_algebra_value(handle, 3, 0) != -1 || nw_algebra_action(handle, 1, 'x', 0) != 1 ||
            nw_algebra_action(handle, 3, 0, 0) != 1) bad++;
        int64_t count = nw_algebra_info(handle, 11);
        if (count != (int64_t)strlen(examples[i].working)) bad++;
        else for (int64_t j = 0; j < count; j++) {
            if (nw_algebra_value(handle, 3, j) != (unsigned char)examples[i].working[j]) bad++;
        }
        if (nw_algebra_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                   handle, 0, 912, 684) <= 0) bad++;
        if (nw_algebra_destroy(handle) != 0) bad++;
    }
    free(buffer);
    printf("Algebra selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_numberology(void) {
    int bad = 0;
    int64_t handle = nw_numberology_create(1, 2, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_numberology_destroy(handle);
        free(buffer);
        printf("Numberology selftest: allocation failed\n");
        return 1;
    }
    if (nw_numberology_info(handle, 0) != 0) bad++;
    if (nw_numberology_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_numberology_info(handle, 0) != 1) bad++;
    if (nw_numberology_info(handle, 4) < 4) bad++;
    if (nw_numberology_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                   handle, 0, 912, 684) <= 0) bad++;
    if (nw_numberology_action(handle, 1, 45, 0) != 1) bad++;
    if (nw_numberology_action(handle, 2, 0, 0) != 1) bad++;
    if (nw_numberology_destroy(handle) != 0) bad++;
    handle = nw_numberology_create(1000, 1, 0, 19);
    const char *exact = "96448543405967464215539390836603148782077915887889532192857920126483182449263992839";
    if (!handle) bad++;
    if (handle) {
        if (nw_numberology_action(handle, 0, 0, 0) != 1 || nw_numberology_info(handle, 4) != 29 || nw_numberology_info(handle, 17) != 0) bad++;
        for (size_t i = 0; i < strlen(exact); i++)
            if (nw_numberology_action(handle, 1, (unsigned char)exact[i], 0) != 1) bad++;
        if (nw_numberology_action(handle, 3, 0, 0) != 1 || nw_numberology_info(handle, 8) != 1 ||
            nw_numberology_info(handle, 15) != (int64_t)strlen(exact)) bad++;
        for (size_t i = 0; i < strlen(exact); i++)
            if (nw_numberology_value(handle, 2, (int64_t)i) != (unsigned char)exact[i]) bad++;
        if (nw_numberology_destroy(handle) != 0) bad++;
    }
    free(buffer);
    printf("Numberology selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_jigsaw(void) {
    int bad = 0;
    int64_t handle = nw_jigsaw_create_options(3, 2, 1, 1, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_jigsaw_destroy(handle);
        free(buffer);
        printf("Jigsaw selftest: allocation failed\n");
        return 1;
    }
    if (nw_jigsaw_info(handle, 0) != 0) bad++;
    if (nw_jigsaw_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_jigsaw_info(handle, 0) != 1) bad++;
    if (nw_jigsaw_info(handle, 1) != 3) bad++;
    if (nw_jigsaw_info(handle, 14) != 1) bad++;
    if (nw_jigsaw_value(handle, 0, 0) < 0) bad++;
    if (nw_jigsaw_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                              handle, 0, 912, 684) <= 0) bad++;
    if (nw_jigsaw_action(handle, 1, 0, 0) != 1) bad++;
    if (nw_jigsaw_action(handle, 1, 0, 1) != 1) bad++;
    if (nw_jigsaw_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Jigsaw selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_sudoku(void) {
    int bad = 0;
    int64_t handle = nw_sudoku_create(1, 2, 1, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_sudoku_destroy(handle);
        free(buffer);
        printf("Sudoku selftest: allocation failed\n");
        return 1;
    }
    if (nw_sudoku_info(handle, 0) != 0) bad++;
    if (nw_sudoku_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_sudoku_info(handle, 0) != 1) bad++;
    if (nw_sudoku_info(handle, 5) < 4) bad++;
    if (nw_sudoku_value(handle, 0, 0) < 0) bad++;
    if (nw_sudoku_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                              handle, 0, 912, 684) <= 0) bad++;
    if (nw_sudoku_action(handle, 1, 0, 0) != 1) bad++;
    if (nw_sudoku_action(handle, 5, 1, 0) < 1) bad++;
    if (nw_sudoku_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Sudoku selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_go(void) {
    int bad = 0;
    int64_t handle = nw_go_create(1, 3, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_go_destroy(handle);
        free(buffer);
        printf("Go selftest: allocation failed\n");
        return 1;
    }
    if (nw_go_info(handle, 0) != 0) bad++;
    if (nw_go_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_go_info(handle, 0) != 1) bad++;
    if (nw_go_info(handle, 4) <= 0) bad++;
    if (nw_go_value(handle, 0, 0) < 0) bad++;
    if (nw_go_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                          handle, 0, 912, 684) <= 0) bad++;
    if (nw_go_action(handle, 3, 0, 0) != 1) bad++;
    if (nw_go_action(handle, 1, 0, 0) != 1) bad++;
    if (nw_go_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Go selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_crossed_wires(void) {
    int bad = 0;
    int64_t handle = nw_crossed_wires_create(3, 5, 1, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_crossed_wires_destroy(handle);
        free(buffer);
        printf("Crossed Wires selftest: allocation failed\n");
        return 1;
    }
    if (nw_crossed_wires_info(handle, 0) != 0) bad++;
    if (nw_crossed_wires_action(handle, 0, 0, 100) != 1) bad++;
    if (nw_crossed_wires_info(handle, 0) != 1) bad++;
    if (nw_crossed_wires_info(handle, 4) != 4) bad++;
    if (nw_crossed_wires_frame_write((int64_t)(uintptr_t)buffer,
                                     FRAME_CAPACITY, handle, 0, 912, 684) <= 0) bad++;
    if (nw_crossed_wires_action(handle, 1, 7, 101) != 2) bad++;
    if (nw_crossed_wires_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Crossed Wires selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_ncup_monte(void) {
    int bad = 0;
    int64_t handle = nw_ncup_monte_create(3, 10, 1, 4, 160, 750, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_ncup_monte_destroy(handle);
        free(buffer);
        printf("N-Cup Monte selftest: allocation failed\n");
        return 1;
    }
    if (nw_ncup_monte_info(handle, 0) != 0) bad++;
    if (nw_ncup_monte_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_ncup_monte_info(handle, 0) != 1) bad++;
    if (nw_ncup_monte_advance(handle, 750) < 1) bad++;
    if (nw_ncup_monte_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                  handle, 0, 912, 684) <= 0) bad++;
    if (nw_ncup_monte_destroy(handle) != 0) bad++;
    free(buffer);
    printf("N-Cup Monte selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_tracking(void) {
    int bad = 0;
    int64_t handle = nw_tracking_create(8, 2, 3, 30, 5, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_tracking_destroy(handle);
        free(buffer);
        printf("Moving Targets selftest: allocation failed\n");
        return 1;
    }
    if (nw_tracking_info(handle, 0) != 0) bad++;
    if (nw_tracking_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_tracking_info(handle, 0) != 1) bad++;
    if (nw_tracking_advance(handle, 2000) < 1) bad++;
    if (nw_tracking_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                handle, 0, 912, 684) <= 0) bad++;
    if (nw_tracking_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Moving Targets selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_lookout(void) {
    int bad = 0;
    int64_t handle = nw_lookout_create(8, 2, 30, 1200, 10, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_lookout_destroy(handle);
        free(buffer);
        printf("Lookout selftest: allocation failed\n");
        return 1;
    }
    if (nw_lookout_info(handle, 0) != 0) bad++;
    if (nw_lookout_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_lookout_info(handle, 0) != 1) bad++;
    if (nw_lookout_info(handle, 20) != 8) bad++;
    if (nw_lookout_advance(handle, 100) < 1) bad++;
    if (nw_lookout_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                               handle, 0, 912, 684) <= 0) bad++;
    if (nw_lookout_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Lookout selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_pursuit(void) {
    int bad = 0;
    int64_t handle = nw_pursuit_create(20, 40, 400, 90, 16, 0, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_pursuit_destroy(handle);
        free(buffer);
        printf("Pursuit selftest: allocation failed\n");
        return 1;
    }
    if (nw_pursuit_info(handle, 0) != 0) bad++;
    if (nw_pursuit_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_pursuit_info(handle, 0) != 1) bad++;
    if (nw_pursuit_advance(handle, 100) != 1) bad++;
    if (nw_pursuit_pointer(handle, 500000, 500000) != 1) bad++;
    if (nw_pursuit_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                               handle, 0, 912, 684) <= 0) bad++;
    if (nw_pursuit_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Pursuit selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_out_of_sight(void) {
    int bad = 0;
    int64_t handle = nw_out_of_sight_create(8, 2, 30, 1200, 2, 460, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_out_of_sight_destroy(handle);
        free(buffer);
        printf("Out of Sight selftest: allocation failed\n");
        return 1;
    }
    if (nw_out_of_sight_info(handle, 0) != 0) bad++;
    if (nw_out_of_sight_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_out_of_sight_info(handle, 0) != 1) bad++;
    if (nw_out_of_sight_advance(handle, 100) < 1) bad++;
    if (nw_out_of_sight_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                    handle, 0, 912, 684) <= 0) bad++;
    if (nw_out_of_sight_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Out of Sight selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_buzz_wire(void) {
    int bad = 0;
    int64_t handle = nw_buzz_wire_create(1, 1, 1, 1, 1, 1, 17);
    uint8_t *buffer = (uint8_t *)(uintptr_t)malloc(FRAME_CAPACITY);
    if (!handle || !buffer) {
        if (handle) nw_buzz_wire_destroy(handle);
        free(buffer);
        printf("Buzz Wire selftest: allocation failed\n");
        return 1;
    }
    if (nw_buzz_wire_info(handle, 0) != 0) bad++;
    if (nw_buzz_wire_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_buzz_wire_info(handle, 0) != 1) bad++;
    if (nw_buzz_wire_advance(handle, 100) < 1) bad++;
    if (nw_buzz_wire_frame_write((int64_t)(uintptr_t)buffer, FRAME_CAPACITY,
                                 handle, 0, 912, 684) <= 0) bad++;
    if (nw_buzz_wire_destroy(handle) != 0) bad++;
    free(buffer);
    printf("Buzz Wire selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_donkey(void) {
    int bad = 0;
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_donkey_create(1, 1, 180, 400, 1, 0, 17);
    if (!buffer || !handle) {
        printf("Donkey selftest: allocation failed\n");
        if (handle) nw_donkey_destroy(handle);
        return 1;
    }
    if (nw_donkey_info(handle, 0) != 0) bad++;
    if (nw_donkey_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_donkey_info(handle, 0) != 1) bad++;
    if (nw_donkey_advance(handle, 500) < 1) bad++;
    if (nw_donkey_info(handle, 0) != 2) bad++;
    if (nw_donkey_frame_write(buffer, FRAME_CAPACITY, handle, 0, 912, 684) <= 0) bad++;
    if (nw_donkey_destroy(handle) != 0) bad++;
    free((void *)(uintptr_t)buffer);
    printf("Donkey selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_two_hands(void) {
    int bad = 0;
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_two_hands_create(3, 1, 400, 1200, 1, 0, 17);
    if (!buffer || !handle) {
        printf("Two Hands selftest: allocation failed\n");
        if (handle) nw_two_hands_destroy(handle);
        return 1;
    }
    if (nw_two_hands_info(handle, 0) != 0) bad++;
    if (nw_two_hands_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_two_hands_info(handle, 0) != 1) bad++;
    if (nw_two_hands_advance(handle, 1300) < 1) bad++;
    if (nw_two_hands_info(handle, 0) != 2) bad++;
    if (nw_two_hands_pointer(handle, 500000, 500000, 1, 1300) < 0) bad++;
    if (nw_two_hands_frame_write(buffer, FRAME_CAPACITY, handle, 0, 912, 684) <= 0) bad++;
    if (nw_two_hands_destroy(handle) != 0) bad++;
    free((void *)(uintptr_t)buffer);
    printf("Two Hands selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_overrun(void) {
    int bad = 0;
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    int64_t handle = nw_overrun_create(1, 3, 1, 0, 0, 0, 17);
    if (!buffer || !handle) {
        printf("Overrun selftest: allocation failed\n");
        if (handle) nw_overrun_destroy(handle);
        return 1;
    }
    if (nw_overrun_info(handle, 0) != 0) bad++;
    if (nw_overrun_action(handle, 0, 0, 0) != 1) bad++;
    if (nw_overrun_info(handle, 0) != 1) bad++;
    if (nw_overrun_action(handle, 1, nw_overrun_value(handle, 3, 0), 1) < 0) bad++;
    if (nw_overrun_advance(handle, 100) < 0) bad++;
    if (nw_overrun_frame_write(buffer, FRAME_CAPACITY, handle, 0, 912, 684) <= 0) bad++;
    if (nw_overrun_destroy(handle) != 0) bad++;
    free((void *)(uintptr_t)buffer);
    printf("Overrun selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static bool value_in_set(int64_t value, const int64_t *allowed, size_t count) {
    for (size_t index = 0; index < count; index++) {
        if (allowed[index] == value) return true;
    }
    return false;
}

typedef struct {
    int64_t level, trials, show_mistakes, adaptive;
    const char *lexicon;
} crossword_options;

/* Python and SDL share this compact, validated settings file. */
static bool crossword_settings_path(char *path, size_t capacity, bool create_dir) {
    const char *override = getenv("NW_CROSSWORD_SETTINGS_PATH");
    if (override && *override) return snprintf(path, capacity, "%s", override) < (int)capacity;
#ifdef _WIN32
    const char *base = getenv("APPDATA");
    if (!base) base = getenv("USERPROFILE");
    const char *folder = "/Neural Workshop";
#else
    const char *base = getenv("HOME");
    const char *folder = "/.neural-workshop";
#endif
    if (!base) return false;
    char directory[4096];
    if (snprintf(directory, sizeof(directory), "%s%s", base, folder) >= (int)sizeof(directory)) return false;
    if (create_dir && !SDL_CreateDirectory(directory)) return false;
    return snprintf(path, capacity, "%s/crossword-options", directory) < (int)capacity;
}

static void crossword_read_settings(crossword_options *options) {
    char path[4096], line[256];
    if (!crossword_settings_path(path, sizeof(path), false)) return;
    FILE *file = fopen(path, "r");
    if (!file) return;
    bool complete = fgets(line, sizeof(line), file) != NULL && fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!complete) return;
    long long fields[4];
    char *cursor = line;
    for (int i = 0; i < 4; i++) {
        while (isspace((unsigned char)*cursor)) cursor++;
        errno = 0;
        char *end = NULL;
        fields[i] = strtoll(cursor, &end, 10);
        if (errno == ERANGE || end == cursor || (*end && !isspace((unsigned char)*end))) return;
        cursor = end;
    }
    while (isspace((unsigned char)*cursor)) cursor++;
    static const int64_t trial_choices[] = {1,2,3,5,8,10};
    if (*cursor == '\0' && fields[0] >= 1 && fields[0] <= 10 &&
        value_in_set(fields[1], trial_choices, 6) &&
        (fields[2] == 0 || fields[2] == 1) && (fields[3] == 0 || fields[3] == 1)) {
        options->level = fields[0]; options->trials = fields[1];
        options->show_mistakes = fields[2]; options->adaptive = fields[3];
    }
}

static bool crossword_write_settings(const crossword_options *options) {
    char path[4096], temporary[4200];
    if (!crossword_settings_path(path, sizeof(path), true) ||
        snprintf(temporary, sizeof(temporary), "%s.%llu.tmp", path,
                 (unsigned long long)SDL_GetTicksNS()) >= (int)sizeof(temporary)) return false;
    FILE *file = fopen(temporary, "w");
    if (!file) return false;
    bool ok = fprintf(file, "%lld %lld %lld %lld\n", (long long)options->level,
                      (long long)options->trials, (long long)options->show_mistakes,
                      (long long)options->adaptive) > 0;
    if (fclose(file) != 0) ok = false;
#ifdef _WIN32
    if (ok) ok = MoveFileExA(temporary, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    if (ok) ok = rename(temporary, path) == 0;
#endif
    if (!ok) remove(temporary);
    return ok;
}

static bool scrabble_settings_path(char *path, size_t capacity, bool create_dir) {
    const char *override = getenv("NW_SCRABBLE_SETTINGS_PATH");
    if (override && *override) return snprintf(path, capacity, "%s", override) < (int)capacity;
#ifdef _WIN32
    const char *base = getenv("APPDATA");
    if (!base) base = getenv("USERPROFILE");
    const char *folder = "/Neural Workshop";
#else
    const char *base = getenv("HOME");
    const char *folder = "/.neural-workshop";
#endif
    if (!base) return false;
    char directory[4096];
    if (snprintf(directory, sizeof(directory), "%s%s", base, folder) >= (int)sizeof(directory)) return false;
    if (create_dir && !SDL_CreateDirectory(directory)) return false;
    return snprintf(path, capacity, "%s/scrabble-options", directory) < (int)capacity;
}

static void scrabble_read_settings(crossword_options *options) {
    char path[4096], line[256];
    if (!scrabble_settings_path(path, sizeof(path), false)) return;
    FILE *file = fopen(path, "r");
    if (!file) return;
    bool complete = fgets(line, sizeof(line), file) != NULL && fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!complete) return;
    long long fields[4];
    char *cursor = line;
    for (int i = 0; i < 4; i++) {
        while (isspace((unsigned char)*cursor)) cursor++;
        errno = 0;
        char *end = NULL;
        fields[i] = strtoll(cursor, &end, 10);
        if (errno == ERANGE || end == cursor || (*end && !isspace((unsigned char)*end))) return;
        cursor = end;
    }
    while (isspace((unsigned char)*cursor)) cursor++;
    static const int64_t trial_choices[] = {1,2,3,5,8,10,15};
    if (*cursor == '\0' && fields[0] >= 1 && fields[0] <= 10 &&
        value_in_set(fields[1], trial_choices, 7) &&
        (fields[2] == 0 || fields[2] == 1) && (fields[3] == 0 || fields[3] == 1)) {
        options->level = fields[0]; options->trials = fields[1];
        options->show_mistakes = fields[2]; options->adaptive = fields[3];
    }
}

static bool scrabble_write_settings(const crossword_options *options) {
    char path[4096], temporary[4200];
    if (!scrabble_settings_path(path, sizeof(path), true) ||
        snprintf(temporary, sizeof(temporary), "%s.%llu.tmp", path,
                 (unsigned long long)SDL_GetTicksNS()) >= (int)sizeof(temporary)) return false;
    FILE *file = fopen(temporary, "w");
    if (!file) return false;
    bool ok = fprintf(file, "%lld %lld %lld %lld\n", (long long)options->level,
                      (long long)options->trials, (long long)options->show_mistakes,
                      (long long)options->adaptive) > 0;
    if (fclose(file) != 0) ok = false;
#ifdef _WIN32
    if (ok) ok = MoveFileExA(temporary, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    if (ok) ok = rename(temporary, path) == 0;
#endif
    if (!ok) remove(temporary);
    return ok;
}

static bool numberology_settings_path(char *path, size_t capacity, bool create_dir) {
    const char *override = getenv("NW_NUMBEROLOGY_SETTINGS_PATH");
    if (override && *override) return snprintf(path, capacity, "%s", override) < (int)capacity;
#ifdef _WIN32
    const char *base = getenv("APPDATA");
    if (!base) base = getenv("USERPROFILE");
    const char *folder = "/Neural Workshop";
#else
    const char *base = getenv("HOME");
    const char *folder = "/.neural-workshop";
#endif
    if (!base) return false;
    char directory[4096];
    if (snprintf(directory, sizeof(directory), "%s%s", base, folder) >= (int)sizeof(directory)) return false;
    if (create_dir && !SDL_CreateDirectory(directory)) return false;
    return snprintf(path, capacity, "%s/numberology-options", directory) < (int)capacity;
}

static void numberology_read_settings(crossword_options *options) {
    char path[4096], line[256], *cursor;
    if (!numberology_settings_path(path, sizeof(path), false)) return;
    FILE *file = fopen(path, "r");
    if (!file) return;
    bool complete = fgets(line, sizeof(line), file) != NULL && fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!complete) return;
    long long fields[3]; cursor = line;
    for (int i = 0; i < 3; i++) {
        while (isspace((unsigned char)*cursor)) cursor++;
        errno = 0; char *end = NULL; fields[i] = strtoll(cursor, &end, 10);
        if (errno == ERANGE || end == cursor || (*end && !isspace((unsigned char)*end))) return;
        cursor = end;
    }
    while (isspace((unsigned char)*cursor)) cursor++;
    static const int64_t choices[] = {1,2,3,5,6,8,10,15};
    if (!*cursor && fields[0] >= 1 && value_in_set(fields[1], choices, 8) && (fields[2] == 0 || fields[2] == 1)) {
        options->level = fields[0]; options->trials = fields[1]; options->adaptive = fields[2];
    }
}

static bool numberology_write_settings(const crossword_options *options) {
    char path[4096], temporary[4200];
    if (!numberology_settings_path(path, sizeof(path), true) ||
        snprintf(temporary, sizeof(temporary), "%s.%llu.tmp", path,
                 (unsigned long long)SDL_GetTicksNS()) >= (int)sizeof(temporary)) return false;
    FILE *file = fopen(temporary, "w");
    if (!file) return false;
    bool ok = fprintf(file, "%lld %lld %lld\n", (long long)options->level,
                      (long long)options->trials, (long long)options->adaptive) > 0;
    if (fclose(file) != 0) ok = false;
#ifdef _WIN32
    if (ok) ok = MoveFileExA(temporary, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    if (ok) ok = rename(temporary, path) == 0;
#endif
    if (!ok) remove(temporary);
    return ok;
}

static bool algebra_settings_path(char *path, size_t capacity, bool create_dir) {
    const char *override = getenv("NW_ALGEBRA_SETTINGS_PATH");
    if (override && *override) return snprintf(path, capacity, "%s", override) < (int)capacity;
#ifdef _WIN32
    const char *base = getenv("APPDATA");
    if (!base) base = getenv("USERPROFILE");
    const char *folder = "/Neural Workshop";
#else
    const char *base = getenv("HOME");
    const char *folder = "/.neural-workshop";
#endif
    if (!base) return false;
    char directory[4096];
    if (snprintf(directory, sizeof(directory), "%s%s", base, folder) >= (int)sizeof(directory)) return false;
    if (create_dir && !SDL_CreateDirectory(directory)) return false;
    return snprintf(path, capacity, "%s/algebra-options", directory) < (int)capacity;
}

static void algebra_read_settings(crossword_options *options) {
    char path[4096], line[256];
    if (!algebra_settings_path(path, sizeof(path), false)) return;
    FILE *file = fopen(path, "r");
    if (!file) return;
    bool complete = fgets(line, sizeof(line), file) != NULL && fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!complete) return;
    long long fields[4];
    char *cursor = line;
    for (int i = 0; i < 4; i++) {
        while (isspace((unsigned char)*cursor)) cursor++;
        errno = 0;
        char *end = NULL;
        fields[i] = strtoll(cursor, &end, 10);
        if (errno == ERANGE || end == cursor || (*end && !isspace((unsigned char)*end))) return;
        cursor = end;
    }
    while (isspace((unsigned char)*cursor)) cursor++;
    static const int64_t trial_choices[] = {1,2,3,5,6,8,10,15};
    if (*cursor == '\0' && fields[0] >= 1 && fields[0] <= 12 &&
        value_in_set(fields[1], trial_choices, 8) &&
        (fields[2] == 0 || fields[2] == 1) && (fields[3] == 0 || fields[3] == 1)) {
        options->level = fields[0]; options->trials = fields[1];
        options->show_mistakes = fields[2]; options->adaptive = fields[3];
    }
}

static bool algebra_write_settings(const crossword_options *options) {
    char path[4096], temporary[4200];
    if (!algebra_settings_path(path, sizeof(path), true) ||
        snprintf(temporary, sizeof(temporary), "%s.%llu.tmp", path,
                 (unsigned long long)SDL_GetTicksNS()) >= (int)sizeof(temporary)) return false;
    FILE *file = fopen(temporary, "w");
    if (!file) return false;
    bool ok = fprintf(file, "%lld %lld %lld %lld\n", (long long)options->level,
                      (long long)options->trials, (long long)options->show_mistakes,
                      (long long)options->adaptive) > 0;
    if (fclose(file) != 0) ok = false;
#ifdef _WIN32
    if (ok) ok = MoveFileExA(temporary, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    if (ok) ok = rename(temporary, path) == 0;
#endif
    if (!ok) remove(temporary);
    return ok;
}

static bool scramble_settings_path(char *path, size_t capacity, bool create_dir) {
    const char *override = getenv("NW_SCRAMBLE_SETTINGS_PATH");
    if (override && *override) return snprintf(path, capacity, "%s", override) < (int)capacity;
#ifdef _WIN32
    const char *base = getenv("APPDATA");
    if (!base) base = getenv("USERPROFILE");
    const char *folder = "/Neural Workshop";
#else
    const char *base = getenv("HOME");
    const char *folder = "/.neural-workshop";
#endif
    if (!base) return false;
    char directory[4096];
    if (snprintf(directory, sizeof(directory), "%s%s", base, folder) >= (int)sizeof(directory)) return false;
    if (create_dir && !SDL_CreateDirectory(directory)) return false;
    return snprintf(path, capacity, "%s/scramble-options", directory) < (int)capacity;
}

static void scramble_read_settings(crossword_options *options) {
    char path[4096], line[256];
    if (!scramble_settings_path(path, sizeof(path), false)) return;
    FILE *file = fopen(path, "r");
    if (!file) return;
    bool complete = fgets(line, sizeof(line), file) != NULL && fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!complete) return;
    long long fields[4];
    char *cursor = line;
    for (int i = 0; i < 4; i++) {
        while (isspace((unsigned char)*cursor)) cursor++;
        errno = 0;
        char *end = NULL;
        fields[i] = strtoll(cursor, &end, 10);
        if (errno == ERANGE || end == cursor || (*end && !isspace((unsigned char)*end))) return;
        cursor = end;
    }
    while (isspace((unsigned char)*cursor)) cursor++;
    static const int64_t trial_choices[] = {1,2,3,5,8,10,15};
    if (*cursor == '\0' && fields[0] >= 1 && fields[0] <= 12 &&
        value_in_set(fields[1], trial_choices, 7) &&
        (fields[2] == 0 || fields[2] == 1) && (fields[3] == 0 || fields[3] == 1)) {
        options->level = fields[0]; options->trials = fields[1];
        options->show_mistakes = fields[2]; options->adaptive = fields[3];
    }
}

static bool scramble_write_settings(const crossword_options *options) {
    char path[4096], temporary[4200];
    if (!scramble_settings_path(path, sizeof(path), true) ||
        snprintf(temporary, sizeof(temporary), "%s.%llu.tmp", path,
                 (unsigned long long)SDL_GetTicksNS()) >= (int)sizeof(temporary)) return false;
    FILE *file = fopen(temporary, "w");
    if (!file) return false;
    bool ok = fprintf(file, "%lld %lld %lld %lld\n", (long long)options->level,
                      (long long)options->trials, (long long)options->show_mistakes,
                      (long long)options->adaptive) > 0;
    if (fclose(file) != 0) ok = false;
#ifdef _WIN32
    if (ok) ok = MoveFileExA(temporary, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    if (ok) ok = rename(temporary, path) == 0;
#endif
    if (!ok) remove(temporary);
    return ok;
}

static int parse_crossword_options(int argc, char **argv, crossword_options *options, bool use_saved) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10};
    static const int64_t trials[] = {1,2,3,5,8,10};
    *options = (crossword_options){2, 3, 1, 1, NULL};
    if (use_saved) crossword_read_settings(options);
    for (int i = 1; i < argc; i++) {
        const char *name = argv[i];
        if (!strcmp(name, "--crossword-no-mistakes")) { options->show_mistakes = 0; continue; }
        if (!strcmp(name, "--crossword-no-adaptive")) { options->adaptive = 0; continue; }
        bool is_level = !strcmp(name, "--crossword-level");
        bool is_trials = !strcmp(name, "--crossword-trials");
        bool is_path = !strcmp(name, "--crossword-lexicon");
        if (!is_level && !is_trials && !is_path) continue;
        if (++i >= argc) { fprintf(stderr, "%s requires a value\n", name); return 2; }
        if (is_path) { options->lexicon = argv[i]; continue; }
        errno = 0;
        char *end = NULL;
        long long value = strtoll(argv[i], &end, 10);
        const int64_t *allowed = is_level ? levels : trials;
        size_t count = is_level ? sizeof(levels)/sizeof(*levels) : sizeof(trials)/sizeof(*trials);
        if (errno == ERANGE || end == argv[i] || *end || !value_in_set(value, allowed, count)) {
            fprintf(stderr, "invalid value for %s: %s\n", name, argv[i]); return 2;
        }
        if (is_level) options->level = value; else options->trials = value;
    }
    return 0;
}

/* The controller owns its copy. A missing default index leaves the task ready
 * with its on-screen recovery message; an explicit bad path is an error. */
static int load_word_index(int64_t handle, const char *explicit_path, bool scrabble) {
    char default_path[4096];
    const char *path = explicit_path;
    if (!path) {
#ifdef _WIN32
        const char *base = getenv("APPDATA");
        const char *suffix = "/Brain Workshop/data/words/lexicon.tsv";
#elif defined(__APPLE__)
        const char *base = getenv("HOME");
        const char *suffix = "/Library/Application Support/Brain Workshop/data/words/lexicon.tsv";
#else
        const char *base = getenv("HOME");
        const char *suffix = "/.brainworkshop/data/words/lexicon.tsv";
#endif
        if (!base || snprintf(default_path, sizeof(default_path), "%s%s", base, suffix) >= (int)sizeof(default_path)) return 0;
        path = default_path;
    }
    FILE *file = fopen(path, "rb");
    if (!file) {
        if (explicit_path) fprintf(stderr, "Cannot open %s lexicon %s: %s\n", scrabble ? "Scrabble" : "Crossword", path, strerror(errno));
        return explicit_path ? -1 : 0;
    }
    if (fseek(file, 0, SEEK_END) != 0) { fclose(file); return -1; }
    long length = ftell(file);
    if (length <= 0 || length > 67108864 || fseek(file, 0, SEEK_SET) != 0) {
        fprintf(stderr, "Invalid %s lexicon size: %s\n", scrabble ? "Scrabble" : "Crossword", path); fclose(file); return -1;
    }
    void *data = malloc((size_t)length);
    if (!data) { fclose(file); return -1; }
    size_t read_count = fread(data, 1, (size_t)length, file);
    fclose(file);
    int64_t result = read_count == (size_t)length
        ? (scrabble ? nw_scrabble_set_lexicon(handle, (int64_t)(uintptr_t)data, length)
                    : nw_crossword_set_lexicon(handle, (int64_t)(uintptr_t)data, length)) : -1;
    free(data);
    if (result != 0) { fprintf(stderr, "Invalid or unreadable %s lexicon: %s\n", scrabble ? "Scrabble" : "Crossword", path); return -1; }
    return 0;
}

static int64_t create_crossword(const crossword_options *options) {
    int64_t handle = nw_crossword_create(options->level, options->trials,
                                         options->show_mistakes, options->adaptive, 23);
    if (handle && load_word_index(handle, options->lexicon, false) != 0) {
        nw_crossword_destroy(handle); return 0;
    }
    return handle;
}

static int parse_scrabble_options(int argc, char **argv, crossword_options *options, bool use_saved) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10};
    static const int64_t trials[] = {1,2,3,5,8,10,15};
    *options = (crossword_options){3, 5, 1, 1, NULL};
    if (use_saved) scrabble_read_settings(options);
    for (int i = 1; i < argc; i++) {
        const char *name = argv[i];
        if (!strcmp(name, "--scrabble-no-premiums")) { options->show_mistakes = 0; continue; }
        if (!strcmp(name, "--scrabble-no-adaptive")) { options->adaptive = 0; continue; }
        bool level = !strcmp(name, "--scrabble-level"), count = !strcmp(name, "--scrabble-trials");
        bool path = !strcmp(name, "--scrabble-lexicon");
        if (!level && !count && !path) continue;
        if (++i >= argc) { fprintf(stderr, "%s requires a value\n", name); return 2; }
        if (path) { options->lexicon = argv[i]; continue; }
        errno = 0; char *end = NULL; long long value = strtoll(argv[i], &end, 10);
        if (errno == ERANGE || end == argv[i] || *end ||
            !value_in_set(value, level ? levels : trials, level ? 10 : 7)) {
            fprintf(stderr, "invalid value for %s: %s\n", name, argv[i]); return 2;
        }
        if (level) options->level = value; else options->trials = value;
    }
    return 0;
}

static int64_t create_scrabble(const crossword_options *options) {
    int64_t handle = nw_scrabble_create(options->level, options->trials,
                                        options->show_mistakes, options->adaptive, 23);
    if (handle && load_word_index(handle, options->lexicon, true) != 0) {
        nw_scrabble_destroy(handle); return 0;
    }
    return handle;
}

static int parse_numberology_options(int argc, char **argv, crossword_options *options, bool use_saved) {
    static const int64_t trials[] = {1,2,3,5,6,8,10,15};
    *options = (crossword_options){1, 6, 0, 1, NULL};
    if (use_saved) numberology_read_settings(options);
    for (int i = 1; i < argc; i++) {
        const char *name = argv[i];
        if (!strcmp(name, "--numberology-no-adaptive")) { options->adaptive = 0; continue; }
        bool level = !strcmp(name, "--numberology-level"), count = !strcmp(name, "--numberology-trials");
        if (!level && !count) continue;
        if (++i >= argc) { fprintf(stderr, "%s requires a value\n", name); return 2; }
        errno = 0; char *end = NULL; long long value = strtoll(argv[i], &end, 10);
        if (errno == ERANGE || end == argv[i] || *end || (level ? value < 1 : !value_in_set(value, trials, 8))) {
            fprintf(stderr, "invalid value for %s: %s\n", name, argv[i]); return 2;
        }
        if (level) options->level = value; else options->trials = value;
    }
    return 0;
}

static int parse_algebra_options(int argc, char **argv, crossword_options *options, bool use_saved) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10,11,12};
    static const int64_t trials[] = {1,2,3,5,6,8,10,15};
    *options = (crossword_options){3, 6, 1, 1, NULL};
    if (use_saved) algebra_read_settings(options);
    for (int i = 1; i < argc; i++) {
        const char *name = argv[i];
        if (!strcmp(name, "--algebra-no-working")) { options->show_mistakes = 0; continue; }
        if (!strcmp(name, "--algebra-no-adaptive")) { options->adaptive = 0; continue; }
        bool level = !strcmp(name, "--algebra-level"), count = !strcmp(name, "--algebra-trials");
        if (!level && !count) continue;
        if (++i >= argc) { fprintf(stderr, "%s requires a value\n", name); return 2; }
        errno = 0; char *end = NULL; long long value = strtoll(argv[i], &end, 10);
        if (errno == ERANGE || end == argv[i] || *end ||
            !value_in_set(value, level ? levels : trials, level ? 12 : 8)) {
            fprintf(stderr, "invalid value for %s: %s\n", name, argv[i]); return 2;
        }
        if (level) options->level = value; else options->trials = value;
    }
    return 0;
}

static int parse_scramble_options(int argc, char **argv, crossword_options *options, bool use_saved) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10,11,12};
    static const int64_t trials[] = {1,2,3,5,8,10,15};
    *options = (crossword_options){3, 5, 1, 1, NULL};
    if (use_saved) scramble_read_settings(options);
    for (int i = 1; i < argc; i++) {
        const char *name = argv[i];
        if (!strcmp(name, "--scramble-no-count")) { options->show_mistakes = 0; continue; }
        if (!strcmp(name, "--scramble-no-adaptive")) { options->adaptive = 0; continue; }
        bool level = !strcmp(name, "--scramble-level"), count = !strcmp(name, "--scramble-trials");
        if (!level && !count) continue;
        if (++i >= argc) { fprintf(stderr, "%s requires a value\n", name); return 2; }
        errno = 0; char *end = NULL; long long value = strtoll(argv[i], &end, 10);
        if (errno == ERANGE || end == argv[i] || *end ||
            !value_in_set(value, level ? levels : trials, level ? 12 : 7)) {
            fprintf(stderr, "invalid value for %s: %s\n", name, argv[i]); return 2;
        }
        if (level) options->level = value; else options->trials = value;
    }
    return 0;
}

static void *scramble_read_file(const char *path, long *length) {
    FILE *file = fopen(path, "rb");
    if (!file) return NULL;
    if (fseek(file, 0, SEEK_END) != 0 || (*length = ftell(file)) <= 0 ||
        *length > 67108864 || fseek(file, 0, SEEK_SET) != 0) { fclose(file); return NULL; }
    void *data = malloc((size_t)*length);
    if (!data) { fclose(file); return NULL; }
    size_t read_count = fread(data, 1, (size_t)*length, file);
    fclose(file);
    if (read_count != (size_t)*length) { free(data); return NULL; }
    return data;
}

static int64_t create_scramble(const crossword_options *options, const char *explicit_index, const char *explicit_sentences) {
    int64_t handle = nw_scramble_create(options->level, options->trials, options->show_mistakes, options->adaptive, 17);
    if (handle <= 0) return 0;
    char index_path[4096], sentence_path[4096];
#ifdef _WIN32
    const char *base = getenv("APPDATA"), *folder = "/Brain Workshop/data/words";
#elif defined(__APPLE__)
    const char *base = getenv("HOME"), *folder = "/Library/Application Support/Brain Workshop/data/words";
#else
    const char *base = getenv("HOME"), *folder = "/.brainworkshop/data/words";
#endif
    if (!base) base = "";
    if (snprintf(index_path, sizeof(index_path), "%s%s/lexicon.tsv", base, folder) >= (int)sizeof(index_path) ||
        snprintf(sentence_path, sizeof(sentence_path), "%s%s/sentences.txt", base, folder) >= (int)sizeof(sentence_path)) {
        nw_scramble_destroy(handle); return 0;
    }
    const char *index = explicit_index ? explicit_index : index_path;
    const char *sentences = explicit_sentences ? explicit_sentences : sentence_path;
    long index_length = 0, sentence_length = 0;
    void *index_data = scramble_read_file(index, &index_length);
    void *sentence_data = scramble_read_file(sentences, &sentence_length);
    if ((!index_data && explicit_index) || (!sentence_data && explicit_sentences)) {
        free(index_data); free(sentence_data);
        fprintf(stderr, "Cannot load Scramble corpus: requested file must exist and be readable\n");
        nw_scramble_destroy(handle); return 0;
    }
    if (!explicit_sentences && sentence_data && sentence_length <= 4096) {
        free(sentence_data); sentence_data = NULL; sentence_length = 0;
    }
    if (!index_data && !sentence_data) return handle;
    int64_t result = nw_scramble_set_corpus(handle, (int64_t)(uintptr_t)index_data, index_length,
                                            (int64_t)(uintptr_t)sentence_data, sentence_length);
    free(index_data); free(sentence_data);
    if (result != 0) { fprintf(stderr, "Invalid Scramble corpus\n"); nw_scramble_destroy(handle); return 0; }
    return handle;
}

static void numberology_text(int64_t handle, const char *text, int64_t now_ms) {
    const unsigned char *at = (const unsigned char *)text;
    while (*at) nw_numberology_action(handle, 1, *at++, now_ms);
}

static void numberology_advance(int64_t handle, crossword_options *options) {
    int64_t before = nw_numberology_info(handle, 0);
    nw_numberology_action(handle, 0, 0, (int64_t)SDL_GetTicks());
    if (before != 3 && nw_numberology_info(handle, 0) == 3 && options->adaptive) {
        int64_t next = nw_numberology_info(handle, 13);
        if (next > options->level) {
            options->level = next;
            if (!numberology_write_settings(options)) SDL_Log("Could not save Numberology settings");
        }
    }
}

static void algebra_text(int64_t handle, const char *text, int64_t now_ms) {
    const unsigned char *at = (const unsigned char *)text;
    while (*at) nw_algebra_action(handle, 1, *at++, now_ms);
}

static void algebra_start(int64_t handle) {
    nw_algebra_action(handle, 0, 0, (int64_t)SDL_GetTicks());
    if (nw_algebra_info(handle, 0) == 1)
        nw_algebra_action(handle, 4, 0, (int64_t)SDL_GetTicks());
}

static void scramble_text(int64_t handle, const char *text, int64_t now_ms) {
    const unsigned char *p = (const unsigned char *)text;
    while (*p) {
        unsigned char c = *p++;
        int64_t value = c == ' ' ? 26 : c >= 'A' && c <= 'Z' ? c - 'A' :
                        c >= 'a' && c <= 'z' ? c - 'a' : 27;
        if (c >= 0x80) while ((*p & 0xc0) == 0x80) p++;
        nw_scramble_action(handle, 1, value, now_ms);
    }
}

static int selftest_scramble(void) {
    int bad = 0;
    crossword_options options;
    char *args[] = {"test", "--scramble-level", "12", "--scramble-trials", "15",
                    "--scramble-no-count", "--scramble-no-adaptive"};
    if (parse_scramble_options(7, args, &options, false) || options.level != 12 || options.trials != 15 ||
        options.show_mistakes != 0 || options.adaptive != 0) bad++;
    int64_t handle = nw_scramble_create(1, 1, 1, 1, 17);
    uint8_t *frame = malloc(FRAME_CAPACITY);
    if (!handle || !frame) bad++;
    if (handle && frame) {
        const char *shown = "we saw mnay pepole on the ctiy street";
        if (nw_scramble_action(handle, 0, 0, 0) != 1 || nw_scramble_info(handle, 4) != (int64_t)strlen(shown)) bad++;
        if (nw_scramble_action(handle, 5, 0, 100) != 1 || nw_scramble_action(handle, 5, 0, 101) != 2) bad++;
        for (size_t i = 0; i < strlen(shown); i++) {
            int64_t value = nw_scramble_value(handle, 0, (int64_t)i);
            if ((value == 26 ? ' ' : 'a' + value) != shown[i]) bad++;
        }
        scramble_text(handle, "WE\nSAW MANY PEOPLE ON THE CITY STREET", 102);
        if (nw_scramble_action(handle, 3, 0, 2600) != 1 || nw_scramble_info(handle, 6) != 1 ||
            nw_scramble_info(handle, 16) != 2) bad++;
        if (nw_scramble_frame_write((int64_t)(uintptr_t)frame, FRAME_CAPACITY, handle, 0, 912, 684) <= 0) bad++;
        if (nw_scramble_action(handle, 0, 0, 3) != 1 || nw_scramble_info(handle, 0) != 3) bad++;
        const char *index = "cat\t1\t\na\t2\t\n", *sentences = "a cat a cat a cat\n";
        if (nw_scramble_set_corpus(handle, (int64_t)(uintptr_t)index, (int64_t)strlen(index),
                                   (int64_t)(uintptr_t)sentences, (int64_t)strlen(sentences)) != 0 ||
            nw_scramble_info(handle, 13) != 1) bad++;
        if (nw_scramble_action(handle, 0, 0, 4) != 1 || nw_scramble_info(handle, 0) != 1) bad++;
        scramble_text(handle, "a cat a cat a cat", 5);
        if (nw_scramble_action(handle, 3, 0, 6) != 1 || nw_scramble_info(handle, 6) != 1) bad++;
        if (nw_scramble_set_corpus(handle, 0, 0, (int64_t)(uintptr_t)sentences, (int64_t)strlen(sentences)) != 0 ||
            nw_scramble_info(handle, 14) != 0 || nw_scramble_info(handle, 15) != 1) bad++;
        if (nw_scramble_action(handle, 0, 0, 7) != 1 || nw_scramble_info(handle, 0) != 1) bad++;
        scramble_text(handle, "a cat a cat a cat", 8);
        if (nw_scramble_action(handle, 3, 0, 9) != 1 || nw_scramble_info(handle, 6) != 1) bad++;
        if (nw_scramble_set_corpus(handle, (int64_t)(uintptr_t)index, (int64_t)strlen(index), 0, 0) != 0 ||
            nw_scramble_info(handle, 14) != 1 || nw_scramble_info(handle, 15) != 0) bad++;
        if (nw_scramble_action(handle, 0, 0, 10) != 1 || nw_scramble_info(handle, 0) != 3) bad++;
        if (nw_scramble_options_frame_write((int64_t)(uintptr_t)frame, FRAME_CAPACITY, 0, 0, 12, 15, 0, 1) <= 0) bad++;
        if (nw_scramble_action(handle, 4, 12 | (6 << 4) | 256, 4) != 1 ||
            nw_scramble_info(handle, 0) != 0 || nw_scramble_info(handle, 1) != 12 ||
            nw_scramble_info(handle, 3) != 15 || nw_scramble_info(handle, 11) != 0 || nw_scramble_info(handle, 12) != 1) bad++;
        nw_scramble_destroy(handle);
    }
    free(frame);
    SDL_Log("Scramble selftest: %s", bad ? "FAIL" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_scrabble(void) {
    int bad = 0;
    crossword_options options;
    char *args[] = {"test", "--scrabble-level", "2", "--scrabble-trials", "1",
                    "--scrabble-no-premiums", "--scrabble-no-adaptive"};
    if (parse_scrabble_options(7, args, &options, false) || options.level != 2 || options.trials != 1 ||
        options.show_mistakes || options.adaptive) bad++;
    int64_t h = nw_scrabble_create(1, 1, 1, 1, 17);
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    if (!h || !buffer) bad++;
    else {
        if (nw_scrabble_action(h, 0, 0, 100) != 1 || nw_scrabble_info(h, 0) != 1) bad++;
        if (nw_scrabble_action(h, 10, 0, 1100) != 1 || nw_scrabble_action(h, 10, 0, 1101) != 2) bad++;
        /* Original offline seed-17 level-1 deal: CAT and rack GLST. */
        if (nw_scrabble_info(h, 9) != 8 || nw_scrabble_info(h, 10) <= 0) bad++;
        if (nw_scrabble_value(h, 0, 23) != 'c' || nw_scrabble_value(h, 0, 24) != 'a' ||
            nw_scrabble_value(h, 0, 25) != 't' || nw_scrabble_value(h, 2, 0) != 'g' ||
            nw_scrabble_value(h, 2, 1) != 'l' || nw_scrabble_value(h, 2, 2) != 's' ||
            nw_scrabble_value(h, 2, 3) != 't') bad++;
        if (nw_scrabble_frame_write(buffer, FRAME_CAPACITY, h, 0, 912, 684) <= 0) bad++;
        if (nw_scrabble_options_frame_write(buffer, FRAME_CAPACITY, 0, 0, 2, 15, 0, 0) <= 0) bad++;
        if (nw_scrabble_action(h, 9, 2 | (6 << 4), 101) != 1 ||
            nw_scrabble_info(h, 0) != 0 || nw_scrabble_info(h, 1) != 2 ||
            nw_scrabble_info(h, 3) != 15 || nw_scrabble_info(h, 17) != 0 || nw_scrabble_info(h, 18) != 0) bad++;
        if (nw_scrabble_action(h, 0, 0, 102) != 1) bad++;
        if (nw_scrabble_pointer(h, 500000, 500000, 912, 684, 2, 0, 103) != 1) bad++;
        if (nw_scrabble_destroy(h) != 0) bad++;
    }
    free((void *)(uintptr_t)buffer);
    printf("Scrabble selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static void crossword_modify_option(crossword_options *draft, int selected, int step) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10};
    static const int64_t trials[] = {1,2,3,5,8,10};
    if (selected >= 2) {
        if (selected == 2) draft->show_mistakes = !draft->show_mistakes;
        else draft->adaptive = !draft->adaptive;
        return;
    }
    const int64_t *choices = selected == 0 ? levels : trials;
    int count = selected == 0 ? 10 : 6;
    int64_t *value = selected == 0 ? &draft->level : &draft->trials;
    int at = 0;
    while (at < count && choices[at] != *value) at++;
    *value = choices[(at + step + count) % count];
}

static int64_t crossword_pack_options(const crossword_options *options) {
    static const int64_t trials[] = {1,2,3,5,8,10};
    int at = 0;
    while (at < 5 && trials[at] != options->trials) at++;
    return options->level | ((int64_t)at << 4) | (options->show_mistakes << 7) | (options->adaptive << 8);
}

static void numberology_edit_digit(crossword_options *draft, bool *editing, int64_t *value, int digit) {
    int64_t current = *editing ? *value : 0;
    if (digit < 0 || digit > 9 || current > (INT64_MAX - digit) / 10) return;
    *value = current * 10 + digit;
    draft->level = *value > 0 ? *value : 1;
    *editing = true;
}

static void numberology_edit_backspace(crossword_options *draft, bool *editing, int64_t *value) {
    int64_t current = *editing ? *value : draft->level;
    *value = current / 10;
    draft->level = *value > 0 ? *value : 1;
    *editing = true;
}

static void numberology_modify_option(crossword_options *draft, int selected, int step) {
    static const int64_t choices[] = {1, 2, 3, 5, 6, 8, 10, 15};
    if (selected == 0) {
        if (step < 0 && draft->level > 1) draft->level--;
        if (step > 0 && draft->level < INT64_MAX) draft->level++;
    } else if (selected == 1) {
        int i = 0; while (i < 8 && choices[i] != draft->trials) i++;
        draft->trials = choices[(i + (step < 0 ? 7 : 1)) % 8];
    } else draft->adaptive = !draft->adaptive;
}

static void algebra_modify_option(crossword_options *draft, int selected, int step) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10,11,12};
    static const int64_t trials[] = {1,2,3,5,6,8,10,15};
    if (selected >= 2) {
        if (selected == 2) draft->show_mistakes = !draft->show_mistakes;
        else draft->adaptive = !draft->adaptive;
        return;
    }
    const int64_t *choices = selected == 0 ? levels : trials;
    int count = selected == 0 ? 12 : 8;
    int64_t *value = selected == 0 ? &draft->level : &draft->trials;
    int at = 0;
    while (at < count && choices[at] != *value) at++;
    *value = choices[(at + step + count) % count];
}

static void scramble_modify_option(crossword_options *draft, int selected, int step) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10,11,12};
    static const int64_t trials[] = {1,2,3,5,8,10,15};
    if (selected >= 2) {
        if (selected == 2) draft->show_mistakes = !draft->show_mistakes;
        else draft->adaptive = !draft->adaptive;
        return;
    }
    const int64_t *choices = selected == 0 ? levels : trials;
    int count = selected == 0 ? 12 : 7;
    int64_t *value = selected == 0 ? &draft->level : &draft->trials;
    int at = 0;
    while (at < count && choices[at] != *value) at++;
    *value = choices[(at + step + count) % count];
}

static void scrabble_modify_option(crossword_options *draft, int selected, int step) {
    static const int64_t levels[] = {1,2,3,4,5,6,7,8,9,10};
    static const int64_t trials[] = {1,2,3,5,8,10,15};
    if (selected >= 2) {
        if (selected == 2) draft->show_mistakes = !draft->show_mistakes;
        else draft->adaptive = !draft->adaptive;
        return;
    }
    const int64_t *choices = selected == 0 ? levels : trials;
    int count = selected == 0 ? 10 : 7;
    int64_t *value = selected == 0 ? &draft->level : &draft->trials;
    int at = 0;
    while (at < count && choices[at] != *value) at++;
    *value = choices[(at + step + count) % count];
}

static int64_t scrabble_pack_options(const crossword_options *options) {
    static const int64_t trials[] = {1,2,3,5,8,10,15};
    int at = 0;
    while (at < 6 && trials[at] != options->trials) at++;
    return options->level | ((int64_t)at << 4) | (options->show_mistakes << 7) | (options->adaptive << 8);
}

static bool shell_exit_key(SDL_Keycode key, bool crossword, bool crossed_wires) {
    return key == SDLK_ESCAPE || (key == SDLK_Q && !crossword && !crossed_wires);
}

static int selftest_crossword(void) {
    static const char index[] = "aaa\t1\tThree-letter fixture clue\naaaa\t2\tFour-letter fixture clue\n";
    int bad = 0;
    if (shell_exit_key(SDLK_Q, true, false) || shell_exit_key(SDLK_Q, false, true) ||
        !shell_exit_key(SDLK_ESCAPE, true, false) || !shell_exit_key(SDLK_Q, false, false)) bad++;
    crossword_options options;
    char *defaults[] = {"test"};
    char *custom[] = {"test", "--crossword-level", "10", "--crossword-trials", "5",
                      "--crossword-no-mistakes", "--crossword-no-adaptive"};
    if (parse_crossword_options(1, defaults, &options, false) || options.level != 2 || options.trials != 3 ||
        !options.show_mistakes || !options.adaptive) bad++;
    if (parse_crossword_options(7, custom, &options, false) || options.level != 10 || options.trials != 5 ||
        options.show_mistakes || options.adaptive) bad++;
    int64_t handle = nw_crossword_create(1, 1, 1, 1, 17);
    int64_t buffer = nw_frame_alloc(FRAME_CAPACITY);
    if (!handle || !buffer) bad++;
    else {
        if (nw_crossword_action(handle, 0, 0, 100) != 2 || nw_crossword_info(handle, 0) != 0) bad++;
        if (nw_crossword_action(handle, 10, 2 | (3 << 4), 101) != 1 ||
            nw_crossword_info(handle, 1) != 2 || nw_crossword_info(handle, 3) != 5 ||
            nw_crossword_info(handle, 13) != 0 || nw_crossword_info(handle, 14) != 0) bad++;
        if (nw_crossword_action(handle, 10, 1 | (1 << 7) | (1 << 8), 102) != 1) bad++;
        if (nw_crossword_set_lexicon(handle, (int64_t)(uintptr_t)"bad", 3) == 0) bad++;
        if (nw_crossword_set_lexicon(handle, (int64_t)(uintptr_t)index, sizeof(index)-1) != 0) bad++;
        if (nw_crossword_info(handle, 12) != 1) bad++;
        if (nw_crossword_frame_write(buffer, FRAME_CAPACITY, handle, 0, 912, 684) <= 0) bad++;
        if (nw_crossword_options_frame_write(buffer, FRAME_CAPACITY, 0, 0, 2, 3, 1, 1) <= 0) bad++;
        crossword_modify_option(&options, 0, 1);
        if (options.level != 1 || crossword_pack_options(&options) != (1 | (3 << 4))) bad++;
        if (nw_crossword_action(handle, 0, 0, 1000) != 1 || nw_crossword_info(handle, 0) != 1) bad++;
        if (nw_crossword_action(handle, 7, 1, 1001) != 1 || nw_crossword_info(handle, 10) != 1) bad++;
        int64_t facing = nw_crossword_info(handle, 7);
        if (nw_crossword_pointer(handle, 500000, 500000, 912, 684, 2, 1002) != 1 ||
            nw_crossword_info(handle, 7) == facing) bad++;
        if (nw_crossword_destroy(handle) != 0) bad++;
    }
    free((void *)(uintptr_t)buffer);
    printf("Crossword selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int parse_task_options(int argc, char **argv,
                              int64_t *sudoku_level, int64_t *sudoku_puzzles,
                              int64_t *sudoku_show_clashes,
                              int64_t *sudoku_adaptive,
                              int64_t *jigsaw_side, int64_t *jigsaw_puzzles,
                              int64_t *jigsaw_adaptive, int64_t *jigsaw_preview,
                              int64_t *jigsaw_mark_placed,
                              int64_t *go_level, int64_t *go_trials,
                              int64_t *crossed_wires_level,
                              int64_t *crossed_wires_rounds,
                              int64_t *crossed_wires_adaptive,
                              int64_t *crossed_wires_show_grid) {
    static const int64_t sudoku_levels[] = { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };
    static const int64_t sudoku_trials[] = { 1, 2, 3, 5, 8, 10 };
    static const int64_t jigsaw_sides[] = { 2, 3, 4, 5, 6, 7, 8, 10 };
    static const int64_t jigsaw_trials[] = { 1, 2, 3, 5, 8, 12, 20 };
    static const int64_t go_levels[] = { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 };
    static const int64_t go_trials_allowed[] = { 1, 3, 5, 8, 10, 15, 20, 30, 50 };
    static const int64_t crossed_wires_levels[] = { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 };
    static const int64_t crossed_wires_round_choices[] = { 1, 2, 3, 5, 8, 10, 15, 20 };

    *sudoku_level = 3;
    *sudoku_puzzles = 3;
    *sudoku_show_clashes = 1;
    *sudoku_adaptive = 1;
    *jigsaw_side = 3;
    *jigsaw_puzzles = 3;
    *jigsaw_adaptive = 1;
    *jigsaw_preview = 1;
    *jigsaw_mark_placed = 0;
    *go_level = 1;
    *go_trials = 10;
    *crossed_wires_level = 3;
    *crossed_wires_rounds = 5;
    *crossed_wires_adaptive = 1;
    *crossed_wires_show_grid = 1;

    for (int index = 1; index < argc; index++) {
        const char *name = argv[index];
        int64_t *target = NULL;
        const int64_t *allowed = NULL;
        size_t allowed_count = 0;

        if (strcmp(name, "--sudoku-level") == 0) {
            target = sudoku_level;
            allowed = sudoku_levels;
            allowed_count = sizeof(sudoku_levels) / sizeof(sudoku_levels[0]);
        } else if (strcmp(name, "--sudoku-puzzles") == 0) {
            target = sudoku_puzzles;
            allowed = sudoku_trials;
            allowed_count = sizeof(sudoku_trials) / sizeof(sudoku_trials[0]);
        } else if (strcmp(name, "--jigsaw-side") == 0) {
            target = jigsaw_side;
            allowed = jigsaw_sides;
            allowed_count = sizeof(jigsaw_sides) / sizeof(jigsaw_sides[0]);
        } else if (strcmp(name, "--jigsaw-puzzles") == 0) {
            target = jigsaw_puzzles;
            allowed = jigsaw_trials;
            allowed_count = sizeof(jigsaw_trials) / sizeof(jigsaw_trials[0]);
        } else if (strcmp(name, "--go-level") == 0) {
            target = go_level;
            allowed = go_levels;
            allowed_count = sizeof(go_levels) / sizeof(go_levels[0]);
        } else if (strcmp(name, "--go-trials") == 0) {
            target = go_trials;
            allowed = go_trials_allowed;
            allowed_count = sizeof(go_trials_allowed) / sizeof(go_trials_allowed[0]);
        } else if (strcmp(name, "--crossed-wires-level") == 0) {
            target = crossed_wires_level;
            allowed = crossed_wires_levels;
            allowed_count = sizeof(crossed_wires_levels) / sizeof(crossed_wires_levels[0]);
        } else if (strcmp(name, "--crossed-wires-rounds") == 0) {
            target = crossed_wires_rounds;
            allowed = crossed_wires_round_choices;
            allowed_count = sizeof(crossed_wires_round_choices) / sizeof(crossed_wires_round_choices[0]);
        } else if (strcmp(name, "--sudoku-no-clashes") == 0) {
            *sudoku_show_clashes = 0;
            continue;
        } else if (strcmp(name, "--sudoku-no-adaptive") == 0) {
            *sudoku_adaptive = 0;
            continue;
        } else if (strcmp(name, "--jigsaw-no-adaptive") == 0) {
            *jigsaw_adaptive = 0;
            continue;
        } else if (strcmp(name, "--jigsaw-no-preview") == 0) {
            *jigsaw_preview = 0;
            continue;
        } else if (strcmp(name, "--jigsaw-mark-placed") == 0) {
            *jigsaw_mark_placed = 1;
            continue;
        } else if (strcmp(name, "--crossed-wires-no-adaptive") == 0) {
            *crossed_wires_adaptive = 0;
            continue;
        } else if (strcmp(name, "--crossed-wires-no-grid") == 0) {
            *crossed_wires_show_grid = 0;
            continue;
        } else {
            continue;
        }

        if (index + 1 >= argc) {
            fprintf(stderr, "%s requires a value\n", name);
            return 2;
        }
        errno = 0;
        char *end = NULL;
        long long parsed = strtoll(argv[++index], &end, 10);
        if (errno == ERANGE || end == argv[index] || *end != '\0' ||
            !value_in_set((int64_t)parsed, allowed, allowed_count)) {
            fprintf(stderr, "invalid value for %s: %s\n", name, argv[index]);
            return 2;
        }
        *target = (int64_t)parsed;
    }
    return 0;
}

static int selftest_algebra_options(void) {
    int bad = 0;
    crossword_options options;
    char *args[] = {"test", "--algebra-level", "12", "--algebra-trials", "6", "--algebra-no-working", "--algebra-no-adaptive"};
    if (parse_algebra_options(7, args, &options, false) || options.level != 12 || options.trials != 6 || options.show_mistakes || options.adaptive) bad++;
    algebra_modify_option(&options, 0, 1);
    if (options.level != 1) bad++;
    algebra_modify_option(&options, 1, 1);
    if (options.trials != 8) bad++;
    algebra_modify_option(&options, 2, 1);
    algebra_modify_option(&options, 3, 1);
    if (!options.show_mistakes || !options.adaptive) bad++;
    int64_t handle = nw_algebra_create_options(12, 1, 0, 1, 19);
    uint8_t *frame = malloc(FRAME_CAPACITY);
    if (!handle || !frame) bad++;
    if (handle && frame) {
        if (nw_algebra_options_frame_write((int64_t)(uintptr_t)frame, FRAME_CAPACITY, 0, 2, 12, 6, 0, 1) <= 0 ||
            nw_algebra_action(handle, 0, 0, 0) != 1 || nw_algebra_action(handle, 1, 'x', 0) != 1 ||
            nw_algebra_action(handle, 3, 0, 0) != 1 || nw_algebra_info(handle, 1) != 11 ||
            nw_algebra_info(handle, 11) != 0) bad++;
        algebra_start(handle);
        algebra_start(handle);
        algebra_text(handle, "X + Y/2", 100);
        const char *expected = "x + y/2";
        if (nw_algebra_info(handle, 6) != (int64_t)strlen(expected)) bad++;
        else for (size_t j = 0; j < strlen(expected); j++)
            if (nw_algebra_value(handle, 1, (int64_t)j) != (unsigned char)expected[j]) bad++;
    }
    if (handle) nw_algebra_destroy(handle);
    free(frame);
    printf("Algebra options selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

static int selftest_task_options(void) {
    int bad = 0;
    int64_t sudoku_level, sudoku_puzzles, sudoku_show_clashes, sudoku_adaptive;
    int64_t jigsaw_side, jigsaw_puzzles, jigsaw_adaptive, jigsaw_preview;
    int64_t jigsaw_mark_placed, go_level, go_trials;
    int64_t crossed_wires_level, crossed_wires_rounds;
    int64_t crossed_wires_adaptive, crossed_wires_show_grid;
    char *defaults[] = { "nw-sdl3" };
    if (parse_task_options(1, defaults, &sudoku_level, &sudoku_puzzles,
                           &sudoku_show_clashes, &sudoku_adaptive,
                           &jigsaw_side, &jigsaw_puzzles, &jigsaw_adaptive,
                           &jigsaw_preview, &jigsaw_mark_placed,
                           &go_level, &go_trials, &crossed_wires_level,
                           &crossed_wires_rounds, &crossed_wires_adaptive,
                           &crossed_wires_show_grid) != 0 ||
        sudoku_level != 3 || sudoku_puzzles != 3 || !sudoku_show_clashes ||
        !sudoku_adaptive || jigsaw_side != 3 || jigsaw_puzzles != 3 ||
        !jigsaw_adaptive || !jigsaw_preview || jigsaw_mark_placed ||
        go_level != 1 || go_trials != 10 || crossed_wires_level != 3 ||
        crossed_wires_rounds != 5 || !crossed_wires_adaptive ||
        !crossed_wires_show_grid) {
        bad++;
    }

    char *configured[] = {
        "nw-sdl3", "--screen", "sudoku", "--sudoku-level", "12",
        "--sudoku-puzzles", "10", "--sudoku-no-clashes",
        "--sudoku-no-adaptive", "--jigsaw-side", "10", "--jigsaw-puzzles",
        "20", "--go-level", "10", "--go-trials", "50",
        "--crossed-wires-level", "12", "--crossed-wires-rounds", "20",
        "--crossed-wires-no-adaptive", "--crossed-wires-no-grid",
        "--jigsaw-no-adaptive", "--jigsaw-no-preview",
        "--jigsaw-mark-placed"
    };
    if (parse_task_options((int)(sizeof(configured) / sizeof(configured[0])),
                           configured, &sudoku_level, &sudoku_puzzles,
                           &sudoku_show_clashes, &sudoku_adaptive,
                           &jigsaw_side, &jigsaw_puzzles, &jigsaw_adaptive,
                           &jigsaw_preview, &jigsaw_mark_placed,
                           &go_level, &go_trials, &crossed_wires_level,
                           &crossed_wires_rounds, &crossed_wires_adaptive,
                           &crossed_wires_show_grid) != 0 ||
        sudoku_level != 12 || sudoku_puzzles != 10 || sudoku_show_clashes ||
        sudoku_adaptive || jigsaw_side != 10 || jigsaw_puzzles != 20 ||
        jigsaw_adaptive || jigsaw_preview || !jigsaw_mark_placed ||
        go_level != 10 || go_trials != 50 || crossed_wires_level != 12 ||
        crossed_wires_rounds != 20 || crossed_wires_adaptive ||
        crossed_wires_show_grid) {
        bad++;
    }
    crossword_options numberology;
    char *numberology_args[] = {"nw-sdl3", "--numberology-level", "10000",
                                "--numberology-trials", "3", "--numberology-no-adaptive"};
    if (parse_numberology_options(1, defaults, &numberology, false) != 0 ||
        numberology.level != 1 || numberology.trials != 6 || !numberology.adaptive ||
        parse_numberology_options(6, numberology_args, &numberology, false) != 0 ||
        numberology.level != 10000 || numberology.trials != 3 || numberology.adaptive)
        bad++;
    numberology_modify_option(&numberology, 0, 1);
    numberology_modify_option(&numberology, 1, 1);
    numberology_modify_option(&numberology, 2, 1);
    if (numberology.level != 10001 || numberology.trials != 5 || !numberology.adaptive) bad++;
    bool editing = false; int64_t edit_value = 0;
    numberology_edit_digit(&numberology, &editing, &edit_value, 0);
    numberology_edit_digit(&numberology, &editing, &edit_value, 5);
    if (numberology.level != 5) bad++;
    numberology_edit_backspace(&numberology, &editing, &edit_value);
    numberology_edit_digit(&numberology, &editing, &edit_value, 7);
    if (numberology.level != 7) bad++;
    edit_value = INT64_MAX; numberology.level = INT64_MAX;
    numberology_edit_digit(&numberology, &editing, &edit_value, 9);
    if (numberology.level != INT64_MAX) bad++;
    printf("SDL task-options selftest: %s\n", bad ? "FAILED" : "PASS");
    return bad ? 1 : 0;
}

int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--selftest-algebra-options") == 0) return selftest_algebra_options();
    if (argc > 1 && strcmp(argv[1], "--selftest-task-options") == 0) {
        return selftest_task_options();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest") == 0) {
        return selftest(argc > 2 ? atoi(argv[2]) : 180);
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-3d-maze") == 0) {
        return selftest_you_are_here();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-taskhub") == 0) {
        return selftest_taskhub();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-sokoban") == 0) {
        return selftest_sokoban();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-monkey-ladder") == 0) {
        return selftest_monkey_ladder();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-nback3d") == 0) {
        return selftest_nback3d();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-marble") == 0) {
        return selftest_marble();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-tetris") == 0) {
        return selftest_tetris();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-count") == 0) {
        return selftest_count();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-mr-time") == 0) {
        return selftest_mr_time();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-graph-mapping") == 0) {
        return selftest_graph_mapping();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-matrix-reasoning") == 0) {
        return selftest_matrix_reasoning();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-in-the-dark") == 0) {
        return selftest_in_the_dark();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-fog") == 0) {
        return selftest_fog();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-removals") == 0) {
        return selftest_removals();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-custody") == 0) {
        return selftest_custody();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-concentration") == 0) {
        return selftest_concentration();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-recognition") == 0) {
        return selftest_recognition();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-trivia") == 0) {
        return selftest_trivia();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-reflex") == 0) {
        return selftest_reflex();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-algebra") == 0) {
        return selftest_algebra();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-numberology") == 0) {
        return selftest_numberology();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-jigsaw") == 0) {
        return selftest_jigsaw();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-sudoku") == 0) {
        return selftest_sudoku();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-go") == 0) {
        return selftest_go();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-crossword-settings-write") == 0) {
        crossword_options saved = {7, 8, 0, 1, NULL};
        return crossword_write_settings(&saved) ? 0 : 1;
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-crossword-settings-read") == 0) {
        crossword_options saved;
        if (parse_crossword_options(argc, argv, &saved, true)) return 2;
        printf("%lld %lld %lld %lld\n", (long long)saved.level, (long long)saved.trials,
               (long long)saved.show_mistakes, (long long)saved.adaptive);
        return 0;
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-scrabble-settings-write") == 0) {
        crossword_options saved = {7, 15, 0, 1, NULL};
        return scrabble_write_settings(&saved) ? 0 : 1;
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-scramble-settings-write") == 0) {
        crossword_options saved = {12, 15, 0, 1, NULL};
        return scramble_write_settings(&saved) ? 0 : 1;
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-scramble-settings-read") == 0) {
        crossword_options saved;
        if (parse_scramble_options(argc, argv, &saved, true)) return 2;
        printf("%lld %lld %lld %lld\n", (long long)saved.level, (long long)saved.trials,
               (long long)saved.show_mistakes, (long long)saved.adaptive);
        return 0;
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-scrabble-settings-read") == 0) {
        crossword_options saved;
        if (parse_scrabble_options(argc, argv, &saved, true)) return 2;
        printf("%lld %lld %lld %lld\n", (long long)saved.level, (long long)saved.trials,
               (long long)saved.show_mistakes, (long long)saved.adaptive);
        return 0;
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-scrabble") == 0) return selftest_scrabble();
    if (argc > 1 && strcmp(argv[1], "--selftest-scramble") == 0) return selftest_scramble();
    if (argc > 1 && strcmp(argv[1], "--selftest-crossword") == 0) return selftest_crossword();
    if (argc > 1 && strcmp(argv[1], "--selftest-crossed-wires") == 0) {
        return selftest_crossed_wires();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-ncup-monte") == 0) {
        return selftest_ncup_monte();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-moving-targets") == 0) {
        return selftest_tracking();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-lookout") == 0) {
        return selftest_lookout();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-pursuit") == 0) {
        return selftest_pursuit();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-out-of-sight") == 0) {
        return selftest_out_of_sight();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-buzz-wire") == 0) {
        return selftest_buzz_wire();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-donkey") == 0) {
        return selftest_donkey();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-two-hands") == 0) {
        return selftest_two_hands();
    }
    if (argc > 1 && strcmp(argv[1], "--selftest-overrun") == 0) {
        return selftest_overrun();
    }
    int64_t sudoku_level, sudoku_puzzles, sudoku_show_clashes, sudoku_adaptive;
    int64_t jigsaw_side, jigsaw_puzzles, jigsaw_adaptive, jigsaw_preview;
    int64_t jigsaw_mark_placed, go_level, go_trials;
    int64_t crossed_wires_level, crossed_wires_rounds;
    int64_t crossed_wires_adaptive, crossed_wires_show_grid;
    int options_status = parse_task_options(
        argc, argv, &sudoku_level, &sudoku_puzzles, &sudoku_show_clashes,
        &sudoku_adaptive, &jigsaw_side, &jigsaw_puzzles, &jigsaw_adaptive,
        &jigsaw_preview, &jigsaw_mark_placed, &go_level, &go_trials,
        &crossed_wires_level, &crossed_wires_rounds,
        &crossed_wires_adaptive, &crossed_wires_show_grid);
    if (options_status != 0) return options_status;
    crossword_options crossword_config;
    if (parse_crossword_options(argc, argv, &crossword_config, true)) return 2;
    crossword_options scrabble_config;
    if (parse_scrabble_options(argc, argv, &scrabble_config, true)) return 2;
    crossword_options numberology_config;
    if (parse_numberology_options(argc, argv, &numberology_config, true)) return 2;
    crossword_options algebra_config;
    if (parse_algebra_options(argc, argv, &algebra_config, true)) return 2;
    crossword_options scramble_config;
    if (parse_scramble_options(argc, argv, &scramble_config, true)) return 2;
    const char *scramble_index_path = NULL, *scramble_sentence_path = NULL;
    for (int i = 1; i < argc; i++) {
        bool index = !strcmp(argv[i], "--scramble-index");
        bool sentences = !strcmp(argv[i], "--scramble-sentences");
        if (index || sentences) {
            if (++i >= argc) { fprintf(stderr, "Scramble corpus option requires a path\n"); return 2; }
            if (index) scramble_index_path = argv[i]; else scramble_sentence_path = argv[i];
        }
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

    bool taskhub_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "taskhub") == 0;
    bool maze_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                     strcmp(argv[2], "3d-maze") == 0;
    bool sokoban_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "sokoban") == 0;
    bool monkey_ladder_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                              strcmp(argv[2], "monkey-ladder") == 0;
    bool nback3d_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "nback3d") == 0;
    bool marble_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "marble") == 0;
    bool tetris_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "tetris") == 0;
    bool count_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                      strcmp(argv[2], "count") == 0;
    bool mr_time_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "mr-time") == 0;
    bool graph_mapping_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                              strcmp(argv[2], "graph-mapping") == 0;
    bool matrix_reasoning_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                                 strcmp(argv[2], "matrix-reasoning") == 0;
    bool in_the_dark_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                            strcmp(argv[2], "in-the-dark") == 0;
    bool fog_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                    strcmp(argv[2], "fog-of-war") == 0;
    bool removals_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                         strcmp(argv[2], "removals") == 0;
    bool custody_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "chain-of-custody") == 0;
    bool concentration_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                              strcmp(argv[2], "concentration") == 0;
    bool recognition_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                            strcmp(argv[2], "recognition") == 0;
    bool trivia_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "trivia") == 0;
    bool reflex_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "reflex") == 0;
    bool algebra_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "algebra") == 0;
    bool numberology_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                            strcmp(argv[2], "numberology") == 0;
    bool jigsaw_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "jigsaw") == 0;
    bool sudoku_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "sudoku") == 0;
    bool go_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                   strcmp(argv[2], "go") == 0;
    bool crossed_wires_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                              strcmp(argv[2], "crossed-wires") == 0;
    bool scrabble_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                         strcmp(argv[2], "scrabble") == 0;
    bool scramble_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                         strcmp(argv[2], "scramble") == 0;
    bool crossword_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                          strcmp(argv[2], "crossword") == 0;
    bool ncup_monte_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                           strcmp(argv[2], "ncup-monte") == 0;
    bool tracking_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                         strcmp(argv[2], "moving-targets") == 0;
    bool lookout_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "lookout") == 0;
    bool pursuit_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "pursuit") == 0;
    bool out_of_sight_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                             strcmp(argv[2], "out-of-sight") == 0;
    bool buzz_wire_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                          strcmp(argv[2], "buzz-wire") == 0;
    bool donkey_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                       strcmp(argv[2], "donkey") == 0;
    bool two_hands_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                          strcmp(argv[2], "two-hands") == 0;
    bool overrun_mode = argc > 2 && strcmp(argv[1], "--screen") == 0 &&
                        strcmp(argv[2], "overrun") == 0;
    int64_t maze_handle = maze_mode ? nw_you_are_here_create(1, 1, 0, 1, 17) : 0;
    int64_t sokoban_handle = sokoban_mode ? nw_sokoban_create(1, 1, 0, 1, 17) : 0;
    int64_t monkey_ladder_handle = monkey_ladder_mode
        ? nw_monkey_ladder_create(5, 2, 1, 300, 120, 1, 17) : 0;
    int64_t nback3d_handle = nback3d_mode
        ? nw_nback3d_create(2, 3, 20, 3000, 500, 200, 17) : 0;
    int64_t marble_handle = marble_mode
        ? nw_marble_create(1, 1, 0, 2600, 15000, 17) : 0;
    int64_t tetris_handle = tetris_mode
        ? nw_tetris_create(1, 25, 5, 17) : 0;
    int64_t count_handle = count_mode
        ? nw_count_create(0, 8, 5, 200, 1, 1, 23) : 0;
    int64_t mr_time_handle = mr_time_mode
        ? nw_mr_time_create(0, 1, 5, 3000, 400, 1, 23) : 0;
    int64_t graph_mapping_handle = graph_mapping_mode
        ? nw_graph_mapping_create(4, 0, 5, 3000, 1, 0, 23) : 0;
    int64_t matrix_reasoning_handle = matrix_reasoning_mode
        ? nw_matrix_reasoning_create(1, 5, 0, 1, 1, 1, 23) : 0;
    int64_t in_the_dark_handle = in_the_dark_mode
        ? nw_in_the_dark_create(1, 1, 1000, 1, 23) : 0;
    int64_t fog_handle = fog_mode ? nw_fog_create(2, 100, 1, 1, 23) : 0;
    int64_t removals_handle = removals_mode
        ? nw_removals_create(1, 1, 1000, 1, 23) : 0;
    int64_t custody_handle = custody_mode
        ? nw_custody_create(1, 1, 900, 1200, 1, 23) : 0;
    int64_t concentration_handle = concentration_mode
        ? nw_concentration_create(4, 0, 0, 900, 1, 1, 23) : 0;
    int64_t recognition_handle = recognition_mode
        ? nw_recognition_create(10, 0, 40, 4, 500, 1, 23) : 0;
    int64_t trivia_handle = trivia_mode
        ? nw_trivia_create(1, 1, 1, 1, 23) : 0;
    int64_t reflex_handle = reflex_mode
        ? nw_reflex_create(10, 1200, 400, 3, 100, 1, 23) : 0;
    int64_t algebra_handle = algebra_mode
        ? nw_algebra_create_options(algebra_config.level, algebra_config.trials, algebra_config.show_mistakes, algebra_config.adaptive, 23) : 0;
    if (algebra_handle) SDL_StartTextInput(window);
    int64_t numberology_handle = numberology_mode
        ? nw_numberology_create(numberology_config.level, numberology_config.trials, numberology_config.adaptive, 23) : 0;
    if (numberology_handle) SDL_StartTextInput(window);
    int64_t jigsaw_handle = jigsaw_mode
        ? nw_jigsaw_create_options(jigsaw_side, jigsaw_puzzles,
                                   jigsaw_adaptive, jigsaw_preview,
                                   jigsaw_mark_placed, 23) : 0;
    int64_t sudoku_handle = sudoku_mode
        ? nw_sudoku_create(sudoku_level, sudoku_puzzles,
                           sudoku_show_clashes, sudoku_adaptive, 23) : 0;
    int64_t go_handle = go_mode ? nw_go_create(go_level, go_trials, 23) : 0;
    int64_t crossed_wires_handle = crossed_wires_mode
        ? nw_crossed_wires_create(crossed_wires_level, crossed_wires_rounds,
                                  crossed_wires_adaptive,
                                  crossed_wires_show_grid, 23) : 0;
    int64_t scrabble_handle = scrabble_mode ? create_scrabble(&scrabble_config) : 0;
    int64_t scramble_handle = scramble_mode ? create_scramble(&scramble_config, scramble_index_path, scramble_sentence_path) : 0;
    int64_t crossword_handle = crossword_mode ? create_crossword(&crossword_config) : 0;
    int64_t ncup_monte_handle = ncup_monte_mode
        ? nw_ncup_monte_create(3, 10, 1, 4, 160, 750, 23) : 0;
    int64_t tracking_handle = tracking_mode
        ? nw_tracking_create(8, 2, 3, 30, 5, 1, 23) : 0;
    int64_t lookout_handle = lookout_mode
        ? nw_lookout_create(8, 2, 30, 1200, 10, 1, 23) : 0;
    int64_t pursuit_handle = pursuit_mode
        ? nw_pursuit_create(20, 40, 400, 90, 16, 0, 23) : 0;
    int64_t out_of_sight_handle = out_of_sight_mode
        ? nw_out_of_sight_create(8, 2, 30, 1200, 2, 460, 23) : 0;
    int64_t buzz_wire_handle = buzz_wire_mode
        ? nw_buzz_wire_create(1, 1, 1, 1, 1, 1, 23) : 0;
    int64_t donkey_handle = donkey_mode
        ? nw_donkey_create(1, 1, 180, 400, 1, 0, 23) : 0;
    int64_t two_hands_handle = two_hands_mode
        ? nw_two_hands_create(3, 1, 400, 1200, 1, 0, 23) : 0;
    int64_t overrun_handle = overrun_mode
        ? nw_overrun_create(1, 3, 1, 0, 0, 0, 23) : 0;
    if (maze_mode && !maze_handle) {
        SDL_Log("3D Maze controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (sokoban_mode && !sokoban_handle) {
        SDL_Log("Sokoban controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (lookout_mode && !lookout_handle) {
        SDL_Log("Lookout controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (pursuit_mode && !pursuit_handle) {
        SDL_Log("Pursuit controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (out_of_sight_mode && !out_of_sight_handle) {
        SDL_Log("Out of Sight controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (buzz_wire_mode && !buzz_wire_handle) {
        SDL_Log("Buzz Wire controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (donkey_mode && !donkey_handle) {
        SDL_Log("Donkey controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (two_hands_mode && !two_hands_handle) {
        SDL_Log("Two Hands controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (overrun_mode && !overrun_handle) {
        SDL_Log("Overrun controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (monkey_ladder_mode && !monkey_ladder_handle) {
        SDL_Log("Monkey Ladder controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (mr_time_mode && !mr_time_handle) {
        SDL_Log("Mr. Time controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (graph_mapping_mode && !graph_mapping_handle) {
        SDL_Log("Graph Mapping controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (matrix_reasoning_mode && !matrix_reasoning_handle) {
        SDL_Log("Matrix Reasoning controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (in_the_dark_mode && !in_the_dark_handle) {
        SDL_Log("In the Dark controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (fog_mode && !fog_handle) {
        SDL_Log("Fog of War controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (removals_mode && !removals_handle) {
        SDL_Log("Removals controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (custody_mode && !custody_handle) {
        SDL_Log("Chain of Custody controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (concentration_mode && !concentration_handle) {
        SDL_Log("Concentration controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (recognition_mode && !recognition_handle) {
        SDL_Log("Seen It Before controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (trivia_mode && !trivia_handle) {
        SDL_Log("Trivia controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (reflex_mode && !reflex_handle) {
        SDL_Log("Reflex controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (algebra_mode && !algebra_handle) {
        SDL_Log("Algebra controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (numberology_mode && !numberology_handle) {
        SDL_Log("Numberology controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (jigsaw_mode && !jigsaw_handle) {
        SDL_Log("Jigsaw controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (sudoku_mode && !sudoku_handle) {
        SDL_Log("Sudoku controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (go_mode && !go_handle) {
        SDL_Log("Go controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (crossed_wires_mode && !crossed_wires_handle) {
        SDL_Log("Crossed Wires controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (scrabble_mode && !scrabble_handle) {
        SDL_Log("Scrabble controller creation or index loading failed");
        SDL_DestroyRenderer(renderer); SDL_DestroyWindow(window); SDL_Quit(); return 1;
    }
    if (scramble_mode && !scramble_handle) {
        SDL_Log("Scramble controller creation failed");
        SDL_DestroyRenderer(renderer); SDL_DestroyWindow(window); SDL_Quit(); return 1;
    }
    if (crossword_mode && !crossword_handle) {
        SDL_Log("Crossword controller creation or index loading failed");
        SDL_DestroyRenderer(renderer); SDL_DestroyWindow(window); SDL_Quit(); return 1;
    }
    if (ncup_monte_mode && !ncup_monte_handle) {
        SDL_Log("N-Cup Monte controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (tracking_mode && !tracking_handle) {
        SDL_Log("Moving Targets controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (nback3d_mode && !nback3d_handle) {
        SDL_Log("3D N-Back controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (marble_mode && !marble_handle) {
        SDL_Log("Marble Maze controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (tetris_mode && !tetris_handle) {
        SDL_Log("Freeform Tetris controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    if (count_mode && !count_handle) {
        SDL_Log("Count controller creation failed");
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 1;
    }
    int64_t trial = 1;
    int64_t category = 0, selected = 0;
    Uint64 last_step = SDL_GetTicks();
    Uint64 last_marble_tick = SDL_GetTicks();
    bool playing = false, running = true;
    bool scrabble_options_open = false;
    bool numberology_options_open = false, numberology_options_from_hub = false, numberology_level_editing = false;
    int numberology_options_selected = 0;
    int64_t numberology_level_edit_value = 0;
    crossword_options numberology_draft = numberology_config;
    bool algebra_options_open = false, algebra_options_from_hub = false;
    int algebra_options_selected = 0;
    crossword_options algebra_draft = algebra_config;
    bool scramble_options_open = false, scramble_options_from_hub = false;
    int scramble_options_selected = 0;
    crossword_options scramble_draft = scramble_config;
    bool scramble_suppress_space = false;
    bool scrabble_options_from_hub = false;
    int scrabble_options_selected = 0;
    crossword_options scrabble_draft = scrabble_config;
    bool crossword_options_open = false;
    int crossword_options_selected = 0;
    crossword_options crossword_draft = crossword_config;

    while (running) {
        SDL_Event event;
        bool step = false;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_EVENT_QUIT) running = false;
            if (event.type == SDL_EVENT_TEXT_INPUT && scramble_mode && !scramble_options_open && nw_scramble_info(scramble_handle, 0) == 1) {
                const char *text = event.text.text;
                if (scramble_suppress_space && text[0] == ' ') text++;
                scramble_suppress_space = false;
                scramble_text(scramble_handle, text, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_TEXT_INPUT && numberology_mode) {
                if (numberology_options_open && numberology_options_selected == 0) {
                    for (const char *p = event.text.text; *p; p++) if (*p >= '0' && *p <= '9') {
                        numberology_edit_digit(&numberology_draft, &numberology_level_editing,
                                               &numberology_level_edit_value, *p - '0');
                    }
                } else if (!numberology_options_open && nw_numberology_info(numberology_handle, 0) == 1)
                    numberology_text(numberology_handle, event.text.text, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_TEXT_INPUT && algebra_mode && !algebra_options_open && nw_algebra_info(algebra_handle, 0) == 1) {
                algebra_text(algebra_handle, event.text.text, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_WINDOW_FOCUS_LOST && marble_mode)
                marble_release_all(marble_handle);
            if (event.type == SDL_EVENT_KEY_DOWN) {
                if (numberology_mode && numberology_options_open && event.key.key == SDLK_ESCAPE) {
                    numberology_options_open = false;
                    if (numberology_options_from_hub) {
                        nw_numberology_destroy(numberology_handle); numberology_handle = 0;
                        numberology_mode = false; numberology_options_from_hub = false;
                        SDL_StopTextInput(window);
                    }
                    continue;
                }
                if (algebra_mode && algebra_options_open && event.key.key == SDLK_ESCAPE) {
                    algebra_options_open = false;
                    if (algebra_options_from_hub) {
                        nw_algebra_destroy(algebra_handle);
                        algebra_handle = 0; algebra_mode = false; algebra_options_from_hub = false;
                        SDL_StopTextInput(window);
                    }
                    continue;
                }
                if (scramble_mode && scramble_options_open && event.key.key == SDLK_ESCAPE) {
                    scramble_options_open = false;
                    if (scramble_options_from_hub) {
                        nw_scramble_destroy(scramble_handle);
                        scramble_handle = 0; scramble_mode = false; scramble_options_from_hub = false;
                    }
                    continue;
                }
                if (scrabble_mode && scrabble_options_open && event.key.key == SDLK_ESCAPE) {
                    scrabble_options_open = false;
                    if (scrabble_options_from_hub) {
                        nw_scrabble_destroy(scrabble_handle);
                        scrabble_handle = 0; scrabble_mode = false; scrabble_options_from_hub = false;
                    }
                    continue;
                }
                if (crossword_mode && crossword_options_open && event.key.key == SDLK_ESCAPE) {
                    crossword_options_open = false;
                    continue;
                }
                if (shell_exit_key(event.key.key, crossword_mode || scrabble_mode || scramble_mode, crossed_wires_mode)) {
                    if (taskhub_mode && maze_mode) {
                        nw_you_are_here_destroy(maze_handle);
                        maze_handle = 0;
                        maze_mode = false;
                    } else if (taskhub_mode && sokoban_mode) {
                        nw_sokoban_destroy(sokoban_handle);
                        sokoban_handle = 0;
                        sokoban_mode = false;
                    } else if (taskhub_mode && monkey_ladder_mode) {
                        nw_monkey_ladder_destroy(monkey_ladder_handle);
                        monkey_ladder_handle = 0;
                        monkey_ladder_mode = false;
                    } else if (taskhub_mode && nback3d_mode) {
                        nw_nback3d_destroy(nback3d_handle);
                        nback3d_handle = 0;
                        nback3d_mode = false;
                    } else if (taskhub_mode && marble_mode) {
                        nw_marble_destroy(marble_handle);
                        marble_handle = 0;
                        marble_mode = false;
                    } else if (taskhub_mode && tetris_mode) {
                        nw_tetris_destroy(tetris_handle);
                        tetris_handle = 0;
                        tetris_mode = false;
                    } else if (taskhub_mode && count_mode) {
                        nw_count_destroy(count_handle);
                        count_handle = 0;
                        count_mode = false;
                    } else if (taskhub_mode && mr_time_mode) {
                        nw_mr_time_destroy(mr_time_handle);
                        mr_time_handle = 0;
                        mr_time_mode = false;
                    } else if (taskhub_mode && graph_mapping_mode) {
                        nw_graph_mapping_destroy(graph_mapping_handle);
                        graph_mapping_handle = 0;
                        graph_mapping_mode = false;
                    } else if (taskhub_mode && matrix_reasoning_mode) {
                        nw_matrix_reasoning_destroy(matrix_reasoning_handle);
                        matrix_reasoning_handle = 0;
                        matrix_reasoning_mode = false;
                    } else if (taskhub_mode && in_the_dark_mode) {
                        nw_in_the_dark_destroy(in_the_dark_handle);
                        in_the_dark_handle = 0;
                        in_the_dark_mode = false;
                    } else if (taskhub_mode && fog_mode) {
                        nw_fog_destroy(fog_handle);
                        fog_handle = 0;
                        fog_mode = false;
                    } else if (taskhub_mode && removals_mode) {
                        nw_removals_destroy(removals_handle);
                        removals_handle = 0;
                        removals_mode = false;
                    } else if (taskhub_mode && custody_mode) {
                        nw_custody_destroy(custody_handle);
                        custody_handle = 0;
                        custody_mode = false;
                    } else if (taskhub_mode && concentration_mode) {
                        nw_concentration_destroy(concentration_handle);
                        concentration_handle = 0;
                        concentration_mode = false;
                    } else if (taskhub_mode && recognition_mode) {
                        nw_recognition_destroy(recognition_handle);
                        recognition_handle = 0;
                        recognition_mode = false;
                    } else if (taskhub_mode && trivia_mode) {
                        nw_trivia_destroy(trivia_handle);
                        trivia_handle = 0;
                        trivia_mode = false;
                    } else if (taskhub_mode && reflex_mode) {
                        nw_reflex_destroy(reflex_handle);
                        reflex_handle = 0;
                        reflex_mode = false;
                    } else if (taskhub_mode && algebra_mode) {
                        nw_algebra_destroy(algebra_handle);
                        algebra_handle = 0;
                        algebra_mode = false;
                        SDL_StopTextInput(window);
                    } else if (taskhub_mode && numberology_mode) {
                        nw_numberology_destroy(numberology_handle);
                        numberology_handle = 0;
                        numberology_mode = false;
                        SDL_StopTextInput(window);
                    } else if (taskhub_mode && jigsaw_mode) {
                        nw_jigsaw_destroy(jigsaw_handle);
                        jigsaw_handle = 0;
                        jigsaw_mode = false;
                    } else if (taskhub_mode && sudoku_mode) {
                        nw_sudoku_destroy(sudoku_handle);
                        sudoku_handle = 0;
                        sudoku_mode = false;
                    } else if (taskhub_mode && go_mode) {
                        nw_go_destroy(go_handle);
                        go_handle = 0;
                        go_mode = false;
                    } else if (taskhub_mode && crossed_wires_mode) {
                        nw_crossed_wires_destroy(crossed_wires_handle);
                        crossed_wires_handle = 0;
                        crossed_wires_mode = false;
                    } else if (taskhub_mode && scramble_mode) {
                        SDL_StopTextInput(window);
                        nw_scramble_destroy(scramble_handle);
                        scramble_handle = 0; scramble_mode = false;
                    } else if (taskhub_mode && scrabble_mode) {
                        nw_scrabble_destroy(scrabble_handle);
                        scrabble_handle = 0; scrabble_mode = false;
                    } else if (taskhub_mode && crossword_mode) {
                        nw_crossword_destroy(crossword_handle);
                        crossword_handle = 0; crossword_mode = false;
                    } else if (taskhub_mode && ncup_monte_mode) {
                        nw_ncup_monte_destroy(ncup_monte_handle);
                        ncup_monte_handle = 0;
                        ncup_monte_mode = false;
                    } else if (taskhub_mode && tracking_mode) {
                        nw_tracking_destroy(tracking_handle);
                        tracking_handle = 0;
                        tracking_mode = false;
                    } else if (taskhub_mode && lookout_mode) {
                        nw_lookout_destroy(lookout_handle);
                        lookout_handle = 0;
                        lookout_mode = false;
                    } else if (taskhub_mode && pursuit_mode) {
                        nw_pursuit_destroy(pursuit_handle);
                        pursuit_handle = 0;
                        pursuit_mode = false;
                    } else if (taskhub_mode && out_of_sight_mode) {
                        nw_out_of_sight_destroy(out_of_sight_handle);
                        out_of_sight_handle = 0;
                        out_of_sight_mode = false;
                    } else if (taskhub_mode && buzz_wire_mode) {
                        nw_buzz_wire_destroy(buzz_wire_handle);
                        buzz_wire_handle = 0;
                        buzz_wire_mode = false;
                    } else if (taskhub_mode && donkey_mode) {
                        nw_donkey_destroy(donkey_handle);
                        donkey_handle = 0;
                        donkey_mode = false;
                    } else if (taskhub_mode && two_hands_mode) {
                        nw_two_hands_destroy(two_hands_handle);
                        two_hands_handle = 0;
                        two_hands_mode = false;
                    } else if (taskhub_mode && overrun_mode) {
                        nw_overrun_destroy(overrun_handle);
                        overrun_handle = 0;
                        overrun_mode = false;
                    } else {
                        running = false;
                    }
                }
                if (taskhub_mode && !maze_mode && !sokoban_mode && !nback3d_mode &&
                    !marble_mode &&
                    !monkey_ladder_mode && !tetris_mode && !count_mode && !mr_time_mode &&
                    !graph_mapping_mode && !matrix_reasoning_mode && !in_the_dark_mode && !fog_mode && !removals_mode && !custody_mode && !concentration_mode && !recognition_mode && !trivia_mode && !reflex_mode && !algebra_mode && !numberology_mode && !jigsaw_mode && !sudoku_mode && !go_mode && !crossed_wires_mode && !crossword_mode && !scrabble_mode && !scramble_mode && !ncup_monte_mode && !tracking_mode && !lookout_mode && !pursuit_mode && !out_of_sight_mode && !buzz_wire_mode && !donkey_mode && !two_hands_mode && !overrun_mode) {
                    if (event.key.key == SDLK_LEFT) category = (category + 6) % 7, selected = 0;
                    if (event.key.key == SDLK_RIGHT) category = (category + 1) % 7, selected = 0;
                    if (event.key.key == SDLK_UP) selected = selected > 0 ? selected - 1 : 0;
                    if (event.key.key == SDLK_DOWN) selected += 1;
                    if (event.key.key == SDLK_C && category == 4 && selected == 7) {
                        scrabble_handle = create_scrabble(&scrabble_config);
                        scrabble_mode = scrabble_handle != 0;
                        if (scrabble_mode) {
                            scrabble_draft = scrabble_config;
                            scrabble_options_selected = 0;
                            scrabble_options_open = true;
                            scrabble_options_from_hub = true;
                        }
                    }
                    if (event.key.key == SDLK_C && category == 4 && selected == 10) {
                        numberology_handle = nw_numberology_create(numberology_config.level, numberology_config.trials, numberology_config.adaptive, 23);
                        numberology_mode = numberology_handle != 0;
                        if (numberology_mode) {
                            numberology_draft = numberology_config; numberology_options_selected = 0;
                            numberology_level_editing = false; numberology_options_open = true;
                            numberology_options_from_hub = true; SDL_StartTextInput(window);
                        }
                    }
                    if (event.key.key == SDLK_C && category == 4 && selected == 9) {
                        algebra_handle = nw_algebra_create_options(algebra_config.level, algebra_config.trials, algebra_config.show_mistakes, algebra_config.adaptive, 23);
                        algebra_mode = algebra_handle != 0;
                        if (algebra_mode) {
                            algebra_draft = algebra_config; algebra_options_selected = 0;
                            algebra_options_open = true; algebra_options_from_hub = true;
                        }
                    }
                    if (event.key.key == SDLK_C && category == 4 && selected == 8) {
                        scramble_handle = create_scramble(&scramble_config, scramble_index_path, scramble_sentence_path);
                        scramble_mode = scramble_handle != 0;
                        if (scramble_mode) {
                            scramble_draft = scramble_config;
                            scramble_options_selected = 0;
                            scramble_options_open = true;
                            scramble_options_from_hub = true;
                        }
                    }
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        if (category == 5 && selected == 4) {
                            maze_handle = nw_you_are_here_create(1, 1, 0, 1, 17);
                            maze_mode = maze_handle != 0;
                        } else if (category == 5 && selected == 2) {
                            sokoban_handle = nw_sokoban_create(1, 1, 0, 1, 17);
                            sokoban_mode = sokoban_handle != 0;
                        } else if (category == 0 && selected == 1) {
                            monkey_ladder_handle = nw_monkey_ladder_create(5, 2, 1, 300, 120, 1, 17);
                            monkey_ladder_mode = monkey_ladder_handle != 0;
                        } else if (category == 0 && selected == 0) {
                            nback3d_handle = nw_nback3d_create(2, 3, 20, 3000, 500, 200, 17);
                            nback3d_mode = nback3d_handle != 0;
                        } else if (category == 2 && selected == 10) {
                            marble_handle = nw_marble_create(1, 1, 0, 2600, 15000, 17);
                            marble_mode = marble_handle != 0;
                        } else if (category == 5 && selected == 6) {
                            tetris_handle = nw_tetris_create(1, 25, 5, 17);
                            tetris_mode = tetris_handle != 0;
                        } else if (category == 3 && selected == 0) {
                            count_handle = nw_count_create(0, 8, 5, 200, 1, 1, 23);
                            count_mode = count_handle != 0;
                        } else if (category == 3 && selected == 1) {
                            mr_time_handle = nw_mr_time_create(0, 1, 5, 3000, 400, 1, 23);
                            mr_time_mode = mr_time_handle != 0;
                        } else if (category == 4 && selected == 0) {
                            graph_mapping_handle = nw_graph_mapping_create(4, 0, 5, 3000, 1, 0, 23);
                            graph_mapping_mode = graph_mapping_handle != 0;
                        } else if (category == 4 && selected == 1) {
                            matrix_reasoning_handle = nw_matrix_reasoning_create(1, 5, 0, 1, 1, 1, 23);
                            matrix_reasoning_mode = matrix_reasoning_handle != 0;
                        } else if (category == 0 && selected == 2) {
                            in_the_dark_handle = nw_in_the_dark_create(1, 1, 1000, 1, 23);
                            in_the_dark_mode = in_the_dark_handle != 0;
                        } else if (category == 0 && selected == 3) {
                            fog_handle = nw_fog_create(2, 100, 1, 1, 23);
                            fog_mode = fog_handle != 0;
                        } else if (category == 0 && selected == 4) {
                            removals_handle = nw_removals_create(1, 1, 1000, 1, 23);
                            removals_mode = removals_handle != 0;
                        } else if (category == 0 && selected == 5) {
                            custody_handle = nw_custody_create(1, 1, 900, 1200, 1, 23);
                            custody_mode = custody_handle != 0;
                        } else if (category == 1 && selected == 0) {
                            concentration_handle = nw_concentration_create(4, 0, 0, 900, 1, 1, 23);
                            concentration_mode = concentration_handle != 0;
                        } else if (category == 1 && selected == 1) {
                            recognition_handle = nw_recognition_create(10, 0, 40, 4, 500, 1, 23);
                            recognition_mode = recognition_handle != 0;
                        } else if (category == 1 && selected == 2) {
                            trivia_handle = nw_trivia_create(1, 1, 1, 1, 23);
                            trivia_mode = trivia_handle != 0;
                        } else if (category == 2 && selected == 0) {
                            reflex_handle = nw_reflex_create(10, 1200, 400, 3, 100, 1, 23);
                            reflex_mode = reflex_handle != 0;
                        } else if (category == 4 && selected == 9) {
                            algebra_handle = nw_algebra_create_options(algebra_config.level, algebra_config.trials, algebra_config.show_mistakes, algebra_config.adaptive, 23);
                            algebra_mode = algebra_handle != 0;
                            if (algebra_mode) SDL_StartTextInput(window);
                        } else if (category == 4 && selected == 10) {
                            numberology_handle = nw_numberology_create(numberology_config.level, numberology_config.trials, numberology_config.adaptive, 23);
                            numberology_mode = numberology_handle != 0;
                            if (numberology_mode) SDL_StartTextInput(window);
                        } else if (category == 4 && selected == 2) {
                            jigsaw_handle = nw_jigsaw_create_options(
                                jigsaw_side, jigsaw_puzzles, jigsaw_adaptive,
                                jigsaw_preview, jigsaw_mark_placed, 23);
                            jigsaw_mode = jigsaw_handle != 0;
                        } else if (category == 4 && selected == 3) {
                            sudoku_handle = nw_sudoku_create(
                                sudoku_level, sudoku_puzzles,
                                sudoku_show_clashes, sudoku_adaptive, 23);
                            sudoku_mode = sudoku_handle != 0;
                        } else if (category == 4 && selected == 4) {
                            go_handle = nw_go_create(go_level, go_trials, 23);
                            go_mode = go_handle != 0;
                        } else if (category == 4 && selected == 5) {
                            crossed_wires_handle = nw_crossed_wires_create(
                                crossed_wires_level, crossed_wires_rounds,
                                crossed_wires_adaptive,
                                crossed_wires_show_grid, 23);
                            crossed_wires_mode = crossed_wires_handle != 0;
                        } else if (category == 4 && selected == 6) {
                            crossword_handle = create_crossword(&crossword_config);
                            crossword_mode = crossword_handle != 0;
                        } else if (category == 4 && selected == 7) {
                            scrabble_handle = create_scrabble(&scrabble_config);
                            scrabble_mode = scrabble_handle != 0;
                        } else if (category == 4 && selected == 8) {
                            scramble_handle = create_scramble(&scramble_config, scramble_index_path, scramble_sentence_path);
                            scramble_mode = scramble_handle != 0;
                        } else if (category == 2 && selected == 1) {
                            ncup_monte_handle = nw_ncup_monte_create(3, 10, 1, 4, 160, 750, 23);
                            ncup_monte_mode = ncup_monte_handle != 0;
                        } else if (category == 2 && selected == 2) {
                            tracking_handle = nw_tracking_create(8, 2, 3, 30, 5, 1, 23);
                            tracking_mode = tracking_handle != 0;
                        } else if (category == 2 && selected == 3) {
                            lookout_handle = nw_lookout_create(8, 2, 30, 1200, 10, 1, 23);
                            lookout_mode = lookout_handle != 0;
                        } else if (category == 2 && selected == 4) {
                            pursuit_handle = nw_pursuit_create(20, 40, 400, 90, 16, 0, 23);
                            pursuit_mode = pursuit_handle != 0;
                        } else if (category == 2 && selected == 6) {
                            out_of_sight_handle = nw_out_of_sight_create(8, 2, 30, 1200, 2, 460, 23);
                            out_of_sight_mode = out_of_sight_handle != 0;
                        } else if (category == 2 && selected == 5) {
                            buzz_wire_handle = nw_buzz_wire_create(1, 1, 1, 1, 1, 1, 23);
                            buzz_wire_mode = buzz_wire_handle != 0;
                        } else if (category == 2 && selected == 7) {
                            donkey_handle = nw_donkey_create(1, 1, 180, 400, 1, 0, 23);
                            donkey_mode = donkey_handle != 0;
                        } else if (category == 2 && selected == 8) {
                            two_hands_handle = nw_two_hands_create(3, 1, 400, 1200, 1, 0, 23);
                            two_hands_mode = two_hands_handle != 0;
                        } else if (category == 2 && selected == 9) {
                            overrun_handle = nw_overrun_create(1, 3, 1, 0, 0, 0, 23);
                            overrun_mode = overrun_handle != 0;
                        }
                    }
                } else if (maze_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_you_are_here_action(maze_handle, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_UP)
                        nw_you_are_here_action(maze_handle, 1, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_DOWN)
                        nw_you_are_here_action(maze_handle, 2, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_LEFT)
                        nw_you_are_here_action(maze_handle, 3, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_RIGHT)
                        nw_you_are_here_action(maze_handle, 4, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_R)
                        nw_you_are_here_action(maze_handle, 5, (int64_t)SDL_GetTicks());
                } else if (sokoban_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_sokoban_action(sokoban_handle, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_UP)
                        nw_sokoban_action(sokoban_handle, 1, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_DOWN)
                        nw_sokoban_action(sokoban_handle, 2, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_LEFT)
                        nw_sokoban_action(sokoban_handle, 3, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_RIGHT)
                        nw_sokoban_action(sokoban_handle, 4, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_U)
                        nw_sokoban_action(sokoban_handle, 5, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_R)
                        nw_sokoban_action(sokoban_handle, 6, (int64_t)SDL_GetTicks());
                } else if (monkey_ladder_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        int64_t phase = nw_monkey_ladder_info(monkey_ladder_handle, 0);
                        nw_monkey_ladder_action(monkey_ladder_handle,
                            phase == 2 ? 7 : 0, 0, (int64_t)SDL_GetTicks());
                    }
                    if (event.key.key == SDLK_UP)
                        nw_monkey_ladder_action(monkey_ladder_handle, 3, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_DOWN)
                        nw_monkey_ladder_action(monkey_ladder_handle, 4, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_LEFT)
                        nw_monkey_ladder_action(monkey_ladder_handle, 5, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_RIGHT)
                        nw_monkey_ladder_action(monkey_ladder_handle, 6, 0, (int64_t)SDL_GetTicks());
                } else if (nback3d_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_nback3d_action(nback3d_handle, 0, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_A)
                        nw_nback3d_action(nback3d_handle, 1, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_P)
                        nw_nback3d_action(nback3d_handle, 3, 0, (int64_t)SDL_GetTicks());
                    if (event.key.key == SDLK_R)
                        nw_nback3d_action(nback3d_handle, 4, 0, (int64_t)SDL_GetTicks());
                } else if (marble_mode) {
                    marble_handle_start_key(marble_handle, event.key.key);
                    if (event.key.key == SDLK_UP)
                        nw_marble_action(marble_handle, 6, 0, 0);
                    if (event.key.key == SDLK_RIGHT)
                        nw_marble_action(marble_handle, 7, 0, 0);
                    if (event.key.key == SDLK_DOWN)
                        nw_marble_action(marble_handle, 8, 0, 0);
                    if (event.key.key == SDLK_LEFT)
                        nw_marble_action(marble_handle, 9, 0, 0);
                    if (event.key.key == SDLK_L)
                        nw_marble_action(marble_handle, 2, 0, 0);
                    if (event.key.key == SDLK_R)
                        nw_marble_action(marble_handle, 1, 0, 0);
                } else if (tetris_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_tetris_action(tetris_handle, 0);
                    if (event.key.key == SDLK_LEFT)
                        nw_tetris_action(tetris_handle, 1);
                    if (event.key.key == SDLK_RIGHT)
                        nw_tetris_action(tetris_handle, 2);
                    if (event.key.key == SDLK_UP)
                        nw_tetris_action(tetris_handle, 3);
                    if (event.key.key == SDLK_DOWN)
                        nw_tetris_action(tetris_handle, 4);
                    if (event.key.key == SDLK_R)
                        nw_tetris_action(tetris_handle, 5);
                    if (event.key.key >= SDLK_1 && event.key.key <= SDLK_6)
                        nw_tetris_action(tetris_handle, 6 + event.key.key - SDLK_1);
                } else if (count_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        int64_t phase = nw_count_info(count_handle, 0);
                        nw_count_action(count_handle, phase == 0 || phase == 4 ? 0 : 3,
                                        0, now_ms);
                    }
                    if (event.key.key == SDLK_BACKSPACE)
                        nw_count_action(count_handle, 2, 0, now_ms);
                    if (event.key.key >= SDLK_0 && event.key.key <= SDLK_9)
                        nw_count_action(count_handle, 1,
                                        event.key.key - SDLK_0, now_ms);
                } else if (mr_time_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        int64_t phase = nw_mr_time_info(mr_time_handle, 0);
                        nw_mr_time_action(mr_time_handle,
                            phase == 3 ? 4 : 0, 0, now_ms);
                    }
                    if (event.key.key == SDLK_BACKSPACE)
                        nw_mr_time_action(mr_time_handle, 3, 0, now_ms);
                    if (event.key.key == SDLK_PERIOD || event.key.key == SDLK_KP_PERIOD)
                        nw_mr_time_action(mr_time_handle, 2, 0, now_ms);
                    if (event.key.key >= SDLK_0 && event.key.key <= SDLK_9)
                        nw_mr_time_action(mr_time_handle, 1,
                                          event.key.key - SDLK_0, now_ms);
                } else if (graph_mapping_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        int64_t phase = nw_graph_mapping_info(graph_mapping_handle, 0);
                        nw_graph_mapping_action(graph_mapping_handle,
                            phase == 0 ? 0 : 2, now_ms);
                    }
                    if (event.key.key == SDLK_Y || event.key.key == SDLK_S ||
                        event.key.key == SDLK_LEFT)
                        nw_graph_mapping_action(graph_mapping_handle, 1, now_ms);
                    if (event.key.key == SDLK_N || event.key.key == SDLK_D ||
                        event.key.key == SDLK_RIGHT)
                        nw_graph_mapping_action(graph_mapping_handle, 2, now_ms);
                } else if (matrix_reasoning_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        int64_t phase = nw_matrix_reasoning_info(matrix_reasoning_handle, 0);
                        if (phase == 0 || phase == 4)
                            nw_matrix_reasoning_action(matrix_reasoning_handle, 0, 0, now_ms);
                    }
                    if (event.key.key >= SDLK_1 && event.key.key <= SDLK_8)
                        nw_matrix_reasoning_action(matrix_reasoning_handle, 1,
                                                  event.key.key - SDLK_1, now_ms);
                } else if (in_the_dark_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_in_the_dark_action(in_the_dark_handle, 0, 0, now_ms);
                    if (event.key.key >= SDLK_1 && event.key.key <= SDLK_5)
                        nw_in_the_dark_action(in_the_dark_handle, 1 + event.key.key - SDLK_1,
                                              event.key.key - SDLK_1, now_ms);
                } else if (fog_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_fog_action(fog_handle, 0);
                    if (event.key.key == SDLK_UP) nw_fog_action(fog_handle, 2);
                    if (event.key.key == SDLK_DOWN) nw_fog_action(fog_handle, 3);
                    if (event.key.key == SDLK_LEFT) nw_fog_action(fog_handle, 4);
                    if (event.key.key == SDLK_RIGHT) nw_fog_action(fog_handle, 5);
                } else if (removals_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_removals_action(removals_handle, 0, 0, now_ms);
                    if (event.key.key >= SDLK_1 && event.key.key <= SDLK_5)
                        nw_removals_action(removals_handle, 1 + event.key.key - SDLK_1,
                                           event.key.key - SDLK_1, now_ms);
                } else if (custody_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_custody_action(custody_handle, 0, 0, now_ms);
                    if (event.key.key == SDLK_LEFT)
                        nw_custody_action(custody_handle, 1, 0, now_ms);
                    if (event.key.key == SDLK_RIGHT)
                        nw_custody_action(custody_handle, 2, 0, now_ms);
                    if (event.key.key == SDLK_Z)
                        nw_custody_action(custody_handle, 3, 0, now_ms);
                } else if (concentration_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t cursor = nw_concentration_info(concentration_handle, 9);
                    int64_t count = nw_concentration_info(concentration_handle, 2);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        nw_concentration_info(concentration_handle, 0) != 2)
                        nw_concentration_action(concentration_handle, 0, 0, now_ms);
                    else if (event.key.key == SDLK_RETURN)
                        nw_concentration_action(concentration_handle, 1, cursor, now_ms);
                    else if (event.key.key == SDLK_LEFT)
                        nw_concentration_action(concentration_handle, 2, cursor > 0 ? cursor - 1 : 0, now_ms);
                    else if (event.key.key == SDLK_RIGHT)
                        nw_concentration_action(concentration_handle, 2, cursor + 1 < count ? cursor + 1 : count - 1, now_ms);
                    else if (event.key.key == SDLK_UP)
                        nw_concentration_action(concentration_handle, 2, cursor >= 4 ? cursor - 4 : 0, now_ms);
                    else if (event.key.key == SDLK_DOWN)
                        nw_concentration_action(concentration_handle, 2, cursor + 4 < count ? cursor + 4 : count - 1, now_ms);
                } else if (recognition_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_recognition_info(recognition_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 4))
                        nw_recognition_action(recognition_handle, 0, 0, now_ms);
                    else if (event.key.key == SDLK_LEFT && (phase == 1 || phase == 2))
                        nw_recognition_action(recognition_handle, 1, 0, now_ms);
                    else if (event.key.key == SDLK_RIGHT && (phase == 1 || phase == 2))
                        nw_recognition_action(recognition_handle, 2, 0, now_ms);
                } else if (trivia_mode) {
                    int64_t phase = nw_trivia_info(trivia_handle, 0);
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        if (phase == 0 || phase == 3) nw_trivia_action(trivia_handle, 0, 0);
                        else if (phase == 1) nw_trivia_action(trivia_handle, 3, 0);
                        else if (phase == 2) nw_trivia_action(trivia_handle, 12, 0);
                    } else if (event.key.key == SDLK_UP && phase == 1) {
                        nw_trivia_action(trivia_handle, 1, 0);
                    } else if (event.key.key == SDLK_DOWN && phase == 1) {
                        nw_trivia_action(trivia_handle, 2, 0);
                    } else if (event.key.key >= SDLK_1 && event.key.key <= SDLK_8 && phase == 1) {
                        nw_trivia_action(trivia_handle, 4 + event.key.key - SDLK_1, 0);
                    }
                } else if (reflex_mode) {
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_reflex_action(reflex_handle, 0, 0, (int64_t)SDL_GetTicks());
                } else if (algebra_mode) {
                    if (algebra_options_open) {
                        if (event.key.key == SDLK_UP && algebra_options_selected > 0) algebra_options_selected--;
                        else if (event.key.key == SDLK_DOWN && algebra_options_selected < 3) algebra_options_selected++;
                        else if (event.key.key == SDLK_LEFT || event.key.key == SDLK_RIGHT || event.key.key == SDLK_SPACE)
                            algebra_modify_option(&algebra_draft, algebra_options_selected, event.key.key == SDLK_LEFT ? -1 : 1);
                        else if (event.key.key == SDLK_RETURN) {
                            int64_t fresh = nw_algebra_create_options(algebra_draft.level, algebra_draft.trials, algebra_draft.show_mistakes, algebra_draft.adaptive, 23);
                            if (fresh) {
                                nw_algebra_destroy(algebra_handle); algebra_handle = fresh;
                                algebra_config = algebra_draft;
                                if (!algebra_write_settings(&algebra_config)) SDL_Log("Could not save Algebra settings");
                            }
                            algebra_options_open = false;
                            if (algebra_options_from_hub) {
                                nw_algebra_destroy(algebra_handle); algebra_handle = 0;
                                algebra_mode = false; algebra_options_from_hub = false;
                            }
                        }
                    } else if (event.key.key == SDLK_V && nw_algebra_info(algebra_handle, 0) == 1 &&
#ifdef __APPLE__
                               (event.key.mod & SDL_KMOD_GUI)) {
#else
                               (event.key.mod & SDL_KMOD_CTRL)) {
#endif
                        char *clipboard = SDL_GetClipboardText();
                        if (clipboard) { algebra_text(algebra_handle, clipboard, (int64_t)SDL_GetTicks()); SDL_free(clipboard); }
                    } else if (event.key.key == SDLK_O && nw_algebra_info(algebra_handle, 0) != 1) {
                        algebra_draft = algebra_config; algebra_options_selected = 0; algebra_options_open = true;
                    } else if (event.key.key == SDLK_SPACE && nw_algebra_info(algebra_handle, 0) != 1)
                        algebra_start(algebra_handle);
                    else if (event.key.key == SDLK_RETURN) {
                        int64_t phase = nw_algebra_info(algebra_handle, 0);
                        if (phase == 1) nw_algebra_action(algebra_handle, 3, 0, (int64_t)SDL_GetTicks());
                    } else if (event.key.key == SDLK_BACKSPACE) {
                        nw_algebra_action(algebra_handle, 2, 0, (int64_t)SDL_GetTicks());
                    }
                } else if (numberology_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_numberology_info(numberology_handle, 0);
                    if (numberology_options_open) {
                        if (event.key.key == SDLK_UP && numberology_options_selected > 0) { numberology_options_selected--; numberology_level_editing = false; }
                        else if (event.key.key == SDLK_DOWN && numberology_options_selected < 2) { numberology_options_selected++; numberology_level_editing = false; }
                        else if (event.key.key == SDLK_LEFT || event.key.key == SDLK_RIGHT || event.key.key == SDLK_SPACE) {
                            numberology_modify_option(&numberology_draft, numberology_options_selected, event.key.key == SDLK_LEFT ? -1 : 1);
                            numberology_level_editing = false;
                        } else if ((event.key.key == SDLK_BACKSPACE || event.key.key == SDLK_DELETE) && numberology_options_selected == 0) {
                            numberology_edit_backspace(&numberology_draft, &numberology_level_editing,
                                                       &numberology_level_edit_value);
                        } else if (event.key.key == SDLK_RETURN) {
                            int64_t fresh = nw_numberology_create(numberology_draft.level, numberology_draft.trials, numberology_draft.adaptive, 23);
                            if (fresh) {
                                nw_numberology_destroy(numberology_handle); numberology_handle = fresh;
                                numberology_config = numberology_draft;
                                if (!numberology_write_settings(&numberology_config)) SDL_Log("Could not save Numberology settings");
                            }
                            numberology_options_open = false;
                            if (numberology_options_from_hub) {
                                nw_numberology_destroy(numberology_handle); numberology_handle = 0;
                                numberology_mode = false; numberology_options_from_hub = false; SDL_StopTextInput(window);
                            }
                        }
                    } else if (event.key.key == SDLK_O && phase != 1) {
                        numberology_draft = numberology_config; numberology_options_selected = 0;
                        numberology_level_editing = false; numberology_options_open = true;
                    } else if (event.key.key == SDLK_SPACE && phase != 1)
                        numberology_advance(numberology_handle, &numberology_config);
                    else if (event.key.key == SDLK_RETURN && phase == 1)
                        nw_numberology_action(numberology_handle, 3, 0, now_ms);
                    else if (event.key.key == SDLK_BACKSPACE || event.key.key == SDLK_DELETE)
                        nw_numberology_action(numberology_handle, 2, 0, now_ms);
                    else if (event.key.key == SDLK_V && phase == 1 &&
#ifdef __APPLE__
                             (event.key.mod & SDL_KMOD_GUI)) {
#else
                             (event.key.mod & SDL_KMOD_CTRL)) {
#endif
                        char *clipboard = SDL_GetClipboardText();
                        if (clipboard) { numberology_text(numberology_handle, clipboard, now_ms); SDL_free(clipboard); }
                    }
                } else if (jigsaw_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_jigsaw_info(jigsaw_handle, 0);
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_jigsaw_action(jigsaw_handle, phase == 1 ? 2 : 0, 0, now_ms);
                    else if (event.key.key >= SDLK_0 && event.key.key <= SDLK_9 && phase == 1)
                        nw_jigsaw_action(jigsaw_handle, 1,
                                         event.key.key - SDLK_0, now_ms);
                } else if (sudoku_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_sudoku_info(sudoku_handle, 0);
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN)
                        nw_sudoku_action(sudoku_handle, 0, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_UP)
                        nw_sudoku_action(sudoku_handle, 1, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_DOWN)
                        nw_sudoku_action(sudoku_handle, 2, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_LEFT)
                        nw_sudoku_action(sudoku_handle, 3, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_RIGHT)
                        nw_sudoku_action(sudoku_handle, 4, 0, now_ms);
                    else if (phase == 1 &&
                             (event.key.key == SDLK_BACKSPACE ||
                              event.key.key == SDLK_DELETE ||
                              event.key.key == SDLK_0))
                        nw_sudoku_action(sudoku_handle, 6, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_N)
                        nw_sudoku_action(sudoku_handle, 7, 0, now_ms);
                    else if (phase == 1 && event.key.key >= SDLK_1 && event.key.key <= SDLK_9)
                        nw_sudoku_action(sudoku_handle, 5,
                                         event.key.key - SDLK_0, now_ms);
                    else if (phase == 1 && event.key.key >= SDLK_A && event.key.key <= SDLK_G &&
                             (event.key.key != SDLK_C ||
                              nw_sudoku_info(sudoku_handle, 5) >= 12))
                        nw_sudoku_action(sudoku_handle, 5,
                                         10 + event.key.key - SDLK_A, now_ms);
                } else if (go_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_go_info(go_handle, 0);
                    if (event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) {
                        if (phase == 0 || phase == 3) nw_go_action(go_handle, 0, 0, now_ms);
                        else if (phase == 1) {
                            int64_t size = nw_go_info(go_handle, 4);
                            int64_t x = nw_go_info(go_handle, 5);
                            int64_t y = nw_go_info(go_handle, 6);
                            nw_go_action(go_handle, 1, y * size + x, now_ms);
                        } else if (phase == 2) nw_go_action(go_handle, 2, 0, now_ms);
                    } else if (phase == 1 && event.key.key == SDLK_UP) nw_go_action(go_handle, 3, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_DOWN) nw_go_action(go_handle, 4, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_LEFT) nw_go_action(go_handle, 5, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_RIGHT) nw_go_action(go_handle, 6, 0, now_ms);
                    else if ((phase == 0 || phase == 3) &&
                             event.key.key >= SDLK_1 && event.key.key <= SDLK_9)
                        nw_go_action(go_handle, 7,
                                     event.key.key - SDLK_0, now_ms);
                    else if ((phase == 0 || phase == 3) && event.key.key == SDLK_0)
                        nw_go_action(go_handle, 7, 10, now_ms);
                } else if (scramble_mode) {
                    int64_t phase = nw_scramble_info(scramble_handle, 0);
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    if (scramble_options_open) {
                        if (event.key.key == SDLK_UP && scramble_options_selected > 0) scramble_options_selected--;
                        else if (event.key.key == SDLK_DOWN && scramble_options_selected < 3) scramble_options_selected++;
                        else if (event.key.key == SDLK_LEFT || event.key.key == SDLK_RIGHT || event.key.key == SDLK_SPACE)
                            scramble_modify_option(&scramble_draft, scramble_options_selected, event.key.key == SDLK_LEFT ? -1 : 1);
                        else if (event.key.key == SDLK_RETURN) {
                            if (nw_scramble_action(scramble_handle, 4, scrabble_pack_options(&scramble_draft), now_ms) == 1) {
                                scramble_config = scramble_draft;
                                if (!scramble_write_settings(&scramble_config)) SDL_Log("Could not save Scramble settings");
                            }
                            scramble_options_open = false;
                            if (scramble_options_from_hub) {
                                nw_scramble_destroy(scramble_handle);
                                scramble_handle = 0; scramble_mode = false; scramble_options_from_hub = false;
                            }
                        }
                    } else if (phase == 1 && event.key.key == SDLK_V &&
#ifdef __APPLE__
                               (event.key.mod & SDL_KMOD_GUI)) {
#else
                               (event.key.mod & SDL_KMOD_CTRL)) {
#endif
                        char *clipboard = SDL_GetClipboardText();
                        if (clipboard) { scramble_text(scramble_handle, clipboard, now_ms); SDL_free(clipboard); }
                    } else if (event.key.key == SDLK_O && phase != 1) {
                        scramble_draft = scramble_config;
                        scramble_options_selected = 0;
                        scramble_options_open = true;
                        scramble_options_from_hub = false;
                        SDL_StopTextInput(window);
                    } else if (event.key.key == SDLK_SPACE && phase != 1) {
                        nw_scramble_action(scramble_handle, 0, 0, now_ms);
                        if (nw_scramble_info(scramble_handle, 0) == 1) {
                            nw_scramble_action(scramble_handle, 5, 0, (int64_t)SDL_GetTicks());
                            scramble_suppress_space = true;
                            SDL_StartTextInput(window);
                        }
                    } else if (event.key.key == SDLK_RETURN || event.key.key == SDLK_KP_ENTER) {
                        nw_scramble_action(scramble_handle, 3, 0, now_ms);
                        if (nw_scramble_info(scramble_handle, 0) != 1) SDL_StopTextInput(window);
                    } else if (event.key.key == SDLK_BACKSPACE || event.key.key == SDLK_DELETE) {
                        nw_scramble_action(scramble_handle, 2, 0, now_ms);
                    }
                } else if (scrabble_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_scrabble_info(scrabble_handle, 0);
                    SDL_Keycode key = event.key.key;
                    if (scrabble_options_open) {
                        if (key == SDLK_UP && scrabble_options_selected > 0) scrabble_options_selected--;
                        else if (key == SDLK_DOWN && scrabble_options_selected < 3) scrabble_options_selected++;
                        else if (key == SDLK_LEFT || key == SDLK_RIGHT || key == SDLK_SPACE)
                            scrabble_modify_option(&scrabble_draft, scrabble_options_selected, key == SDLK_LEFT ? -1 : 1);
                        else if (key == SDLK_RETURN) {
                            if (nw_scrabble_action(scrabble_handle, 9, scrabble_pack_options(&scrabble_draft), now_ms) == 1) {
                                scrabble_config = scrabble_draft;
                                if (!scrabble_write_settings(&scrabble_config)) SDL_Log("Could not save Scrabble settings");
                            }
                            scrabble_options_open = false;
                            if (scrabble_options_from_hub) {
                                nw_scrabble_destroy(scrabble_handle);
                                scrabble_handle = 0; scrabble_mode = false; scrabble_options_from_hub = false;
                            }
                        }
                    } else if (key == SDLK_O || key == SDLK_C) {
                        scrabble_draft = scrabble_config;
                        scrabble_options_selected = 0;
                        scrabble_options_open = true;
                        scrabble_options_from_hub = false;
                    } else if (key == SDLK_SPACE && phase != 1) {
                        nw_scrabble_action(scrabble_handle, 0, 0, now_ms);
                        if (nw_scrabble_info(scrabble_handle, 0) == 1)
                            nw_scrabble_action(scrabble_handle, 10, 0, (int64_t)SDL_GetTicks());
                    }
                    else if (phase == 1) {
                        int action = key == SDLK_RETURN || key == SDLK_KP_ENTER ? 1 :
                                     key == SDLK_LEFT ? 2 : key == SDLK_RIGHT ? 3 : key == SDLK_TAB ? 4 :
                                     key == SDLK_UP ? 5 : key == SDLK_DOWN ? 6 :
                                     (key == SDLK_BACKSPACE || key == SDLK_DELETE) ? 8 : -1;
                        if (action >= 0) nw_scrabble_action(scrabble_handle, action, 0, now_ms);
                        else if (key >= SDLK_1 && key <= SDLK_7) nw_scrabble_action(scrabble_handle, 7, key - SDLK_1, now_ms);
                        else if (key >= SDLK_KP_1 && key <= SDLK_KP_7) nw_scrabble_action(scrabble_handle, 7, key - SDLK_KP_1, now_ms);
                    }
                } else if (crossword_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_crossword_info(crossword_handle, 0);
                    SDL_Keycode key = event.key.key;
                    if (crossword_options_open) {
                        if (key == SDLK_UP && crossword_options_selected > 0) crossword_options_selected--;
                        else if (key == SDLK_DOWN && crossword_options_selected < 3) crossword_options_selected++;
                        else if (key == SDLK_LEFT || key == SDLK_RIGHT || key == SDLK_SPACE)
                            crossword_modify_option(&crossword_draft, crossword_options_selected, key == SDLK_LEFT ? -1 : 1);
                        else if (key == SDLK_RETURN) {
                            if (nw_crossword_action(crossword_handle, 10, crossword_pack_options(&crossword_draft), now_ms) == 1) {
                                crossword_config = crossword_draft;
                                if (!crossword_write_settings(&crossword_config))
                                    SDL_Log("Could not save Crossword settings");
                            }
                            crossword_options_open = false;
                        }
                    } else if (key == SDLK_O && phase != 1) {
                        crossword_draft = crossword_config;
                        crossword_options_selected = 0;
                        crossword_options_open = true;
                    } else if (key == SDLK_SPACE && (phase == 0 || phase == 2 || phase == 3))
                        nw_crossword_action(crossword_handle, 0, 0, now_ms);
                    else if (phase == 1) {
                        int action = key == SDLK_LEFT ? 2 : key == SDLK_RIGHT ? 3 :
                                     key == SDLK_UP ? 4 : key == SDLK_DOWN ? 5 :
                                     key == SDLK_TAB ? 6 :
                                     (key == SDLK_BACKSPACE || key == SDLK_DELETE) ? 8 : -1;
                        if (action >= 0) nw_crossword_action(crossword_handle, action, 0, now_ms);
                        else if (key >= SDLK_A && key <= SDLK_Z)
                            nw_crossword_action(crossword_handle, 7, key - SDLK_A, now_ms);
                    }
                } else if (crossed_wires_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_crossed_wires_info(crossed_wires_handle, 0);
                    int64_t keys = nw_crossed_wires_info(crossed_wires_handle, 4);
                    if (event.key.key == SDLK_SPACE) {
                        nw_crossed_wires_action(crossed_wires_handle, 0, 0, now_ms);
                    } else if (event.key.key == SDLK_O) {
                        /* O is reserved for the source options shortcut. The
                         * native shell exposes the same values as CLI flags. */
                    } else if (phase == 1 && keys == 4 &&
                               (event.key.key == SDLK_UP || event.key.key == SDLK_W ||
                                event.key.key == SDLK_KP_8)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 0, now_ms);
                    } else if (phase == 1 && keys == 4 &&
                               (event.key.key == SDLK_RIGHT || event.key.key == SDLK_D ||
                                event.key.key == SDLK_KP_6)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 1, now_ms);
                    } else if (phase == 1 && keys == 4 &&
                               (event.key.key == SDLK_DOWN || event.key.key == SDLK_S ||
                                event.key.key == SDLK_KP_2)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 2, now_ms);
                    } else if (phase == 1 && keys == 4 &&
                               (event.key.key == SDLK_LEFT || event.key.key == SDLK_A ||
                                event.key.key == SDLK_KP_4)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 3, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_W || event.key.key == SDLK_KP_8 ||
                                event.key.key == SDLK_UP)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 0, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_E || event.key.key == SDLK_KP_9)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 1, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_D || event.key.key == SDLK_KP_6 ||
                                event.key.key == SDLK_RIGHT)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 2, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_C || event.key.key == SDLK_KP_3)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 3, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_X || event.key.key == SDLK_KP_2 ||
                                event.key.key == SDLK_DOWN)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 4, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_Z || event.key.key == SDLK_KP_1)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 5, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_A || event.key.key == SDLK_KP_4 ||
                                event.key.key == SDLK_LEFT)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 6, now_ms);
                    } else if (phase == 1 && keys == 8 &&
                               (event.key.key == SDLK_Q || event.key.key == SDLK_KP_7)) {
                        nw_crossed_wires_action(crossed_wires_handle, 1, 7, now_ms);
                    } else if (event.key.key == SDLK_C && keys == 4) {
                        /* The source options are available through CLI flags. */
                    }
                } else if (ncup_monte_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_ncup_monte_info(ncup_monte_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 4))
                        nw_ncup_monte_action(ncup_monte_handle, 0, 0, now_ms);
                } else if (tracking_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_tracking_info(tracking_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 5))
                        nw_tracking_action(tracking_handle, 0, 0, now_ms);
                } else if (lookout_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_lookout_info(lookout_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 3))
                        nw_lookout_action(lookout_handle, 0, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_J)
                        nw_lookout_action(lookout_handle, 1, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_F)
                        nw_lookout_action(lookout_handle, 2, 0, now_ms);
                } else if (pursuit_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_pursuit_info(pursuit_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 3))
                        nw_pursuit_action(pursuit_handle, 0, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_UP)
                        nw_pursuit_action(pursuit_handle, 1, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_DOWN)
                        nw_pursuit_action(pursuit_handle, 2, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_LEFT)
                        nw_pursuit_action(pursuit_handle, 3, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_RIGHT)
                        nw_pursuit_action(pursuit_handle, 4, 0, now_ms);
                } else if (out_of_sight_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_out_of_sight_info(out_of_sight_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 4))
                        nw_out_of_sight_action(out_of_sight_handle, 0, 0, now_ms);
                    else if (phase == 2 && event.key.key == SDLK_J)
                        nw_out_of_sight_action(out_of_sight_handle, 1, 0, now_ms);
                    else if (phase == 2 && event.key.key == SDLK_F)
                        nw_out_of_sight_action(out_of_sight_handle, 2, 0, now_ms);
                } else if (buzz_wire_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_buzz_wire_info(buzz_wire_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 2 || phase == 3))
                        nw_buzz_wire_action(buzz_wire_handle, 0, 0, now_ms);
                    else if (phase == 1) {
                        int64_t port = -1;
                        if (event.key.key == SDLK_UP) port = 0;
                        if (event.key.key == SDLK_DOWN) port = 1;
                        if (event.key.key == SDLK_LEFT) port = 2;
                        if (event.key.key == SDLK_RIGHT) port = 3;
                        if (event.key.key == SDLK_W) port = 4;
                        if (event.key.key == SDLK_S) port = 5;
                        if (event.key.key == SDLK_I) port = 6;
                        if (event.key.key == SDLK_K) port = 7;
                        if (event.key.key == SDLK_J) port = 8;
                        if (event.key.key == SDLK_L) port = 9;
                        if (event.key.key == SDLK_LSHIFT || event.key.key == SDLK_RSHIFT) port = 10;
                        if (port >= 0) nw_buzz_wire_action(buzz_wire_handle, 1, port, now_ms);
                    }
                } else if (donkey_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_donkey_info(donkey_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 3 || phase == 4))
                        nw_donkey_action(donkey_handle, 0, 0, now_ms);
                    else if (phase == 2 && (event.key.key == SDLK_LEFT ||
                                            event.key.key == SDLK_RIGHT ||
                                            event.key.key == SDLK_SPACE))
                        nw_donkey_action(donkey_handle, 1, 0, now_ms);
                } else if (two_hands_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_two_hands_info(two_hands_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 3 || phase == 4))
                        nw_two_hands_action(two_hands_handle, 0, 0, now_ms);
                    else if (phase == 2) {
                        int64_t port = -1;
                        if (event.key.key == SDLK_LEFT || event.key.key == SDLK_A) port = 1;
                        if (event.key.key == SDLK_RIGHT || event.key.key == SDLK_D) port = 2;
                        if (event.key.key == SDLK_UP || event.key.key == SDLK_W) port = 4;
                        if (event.key.key == SDLK_DOWN || event.key.key == SDLK_S) port = 5;
                        if (event.key.key == SDLK_I) port = 6;
                        if (event.key.key == SDLK_L) port = 7;
                        if (event.key.key == SDLK_O) port = 8;
                        if (event.key.key == SDLK_K) port = 9;
                        if (event.key.key == SDLK_SPACE) port = 10;
                        if (port >= 0) nw_two_hands_action(two_hands_handle, 1, port, now_ms);
                    }
                } else if (overrun_mode) {
                    int64_t now_ms = (int64_t)SDL_GetTicks();
                    int64_t phase = nw_overrun_info(overrun_handle, 0);
                    if ((event.key.key == SDLK_SPACE || event.key.key == SDLK_RETURN) &&
                        (phase == 0 || phase == 3))
                        nw_overrun_action(overrun_handle, 0, 0, now_ms);
                    else if (phase == 1 && event.key.key == SDLK_BACKSPACE)
                        nw_overrun_action(overrun_handle, 2, 0, now_ms);
                    else if (phase == 1 && event.key.key >= SDLK_A && event.key.key <= SDLK_Z)
                        nw_overrun_action(overrun_handle, 1,
                                          event.key.key - SDLK_A, now_ms);
                } else {
                    if (event.key.key == SDLK_SPACE) playing = !playing;
                    if (event.key.key == SDLK_RIGHT) step = true;
                }
            }
            if (event.type == SDL_EVENT_KEY_UP && marble_mode) {
                if (event.key.key == SDLK_UP)
                    nw_marble_release(marble_handle, 4);
                if (event.key.key == SDLK_RIGHT)
                    nw_marble_release(marble_handle, 5);
                if (event.key.key == SDLK_DOWN)
                    nw_marble_release(marble_handle, 6);
                if (event.key.key == SDLK_LEFT)
                    nw_marble_release(marble_handle, 3);
            }
            if (event.type == SDL_EVENT_KEY_UP && buzz_wire_mode) {
                int64_t port = -1;
                if (event.key.key == SDLK_UP) port = 0;
                if (event.key.key == SDLK_DOWN) port = 1;
                if (event.key.key == SDLK_LEFT) port = 2;
                if (event.key.key == SDLK_RIGHT) port = 3;
                if (event.key.key == SDLK_W) port = 4;
                if (event.key.key == SDLK_S) port = 5;
                if (event.key.key == SDLK_I) port = 6;
                if (event.key.key == SDLK_K) port = 7;
                if (event.key.key == SDLK_J) port = 8;
                if (event.key.key == SDLK_L) port = 9;
                if (event.key.key == SDLK_LSHIFT || event.key.key == SDLK_RSHIFT) port = 10;
                if (port >= 0)
                    nw_buzz_wire_action(buzz_wire_handle, 2, port, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && reflex_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0) {
                    int64_t x = (int64_t)(event.button.x * 1000000.0f / (float)px);
                    int64_t y = (int64_t)((py - event.button.y) * 1000000.0f / (float)py);
                    nw_reflex_pointer(reflex_handle, x, y, (int64_t)SDL_GetTicks());
                }
            }
            if (event.type == SDL_EVENT_MOUSE_MOTION && pursuit_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0)
                    nw_pursuit_pointer(pursuit_handle,
                                       (int64_t)(event.motion.x * 1000000.0f / px),
                                       (int64_t)((py - event.motion.y) * 1000000.0f / py));
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && jigsaw_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0)
                    nw_jigsaw_pointer(jigsaw_handle,
                        (int64_t)(event.button.x * 1000000.0f / (float)px),
                        (int64_t)((py - event.button.y) * 1000000.0f / (float)py),
                        px, py, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && numberology_mode && event.button.button == SDL_BUTTON_LEFT) {
                if (numberology_options_open) {
                    int px = 0, py = 0; SDL_GetWindowSize(window, &px, &py);
                    if (px > 0 && py > 0) {
                        float x = event.button.x * 912.0f / px, y = (py - event.button.y) * 684.0f / py;
                        for (int row = 0; row < 3; row++) {
                            float center = 474.0f - row * 48.0f;
                            if (x >= 102 && x <= 810 && y >= center - 18 && y <= center + 18) {
                                if (row == numberology_options_selected) numberology_modify_option(&numberology_draft, row, 1);
                                else numberology_options_selected = row;
                                numberology_level_editing = false; break;
                            }
                        }
                    }
                } else if (nw_numberology_info(numberology_handle, 0) != 1)
                    numberology_advance(numberology_handle, &numberology_config);
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && algebra_mode && event.button.button == SDL_BUTTON_LEFT) {
                if (algebra_options_open) {
                    int px = 0, py = 0; SDL_GetWindowSize(window, &px, &py);
                    if (px > 0 && py > 0) {
                        float x = event.button.x * 912.0f / px, y = (py - event.button.y) * 684.0f / py;
                        for (int row = 0; row < 4; row++) {
                            float center = 474.0f - row * 48.0f;
                            if (x >= 102 && x <= 810 && y >= center - 18 && y <= center + 18) {
                                if (row == algebra_options_selected) algebra_modify_option(&algebra_draft, row, 1);
                                else algebra_options_selected = row;
                                break;
                            }
                        }
                    }
                } else if (nw_algebra_info(algebra_handle, 0) != 1) algebra_start(algebra_handle);
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && scramble_mode && scramble_options_open && event.button.button == SDL_BUTTON_LEFT) {
                int px = 0, py = 0; SDL_GetWindowSize(window, &px, &py);
                if (px > 0 && py > 0) {
                    float x = event.button.x * 912.0f / px, y = (py - event.button.y) * 684.0f / py;
                    for (int row = 0; row < 4; row++) {
                        float center = 474.0f - row * 48.0f;
                        if (x >= 102 && x <= 810 && y >= center - 18 && y <= center + 18) {
                            if (row == scramble_options_selected) scramble_modify_option(&scramble_draft, row, 1);
                            else scramble_options_selected = row;
                            break;
                        }
                    }
                }
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && scramble_mode && !scramble_options_open && event.button.button == SDL_BUTTON_LEFT &&
                nw_scramble_info(scramble_handle, 0) != 1) {
                nw_scramble_action(scramble_handle, 0, 0, (int64_t)SDL_GetTicks());
                if (nw_scramble_info(scramble_handle, 0) == 1) {
                    nw_scramble_action(scramble_handle, 5, 0, (int64_t)SDL_GetTicks());
                    scramble_suppress_space = false;
                    SDL_StartTextInput(window);
                }
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && scrabble_mode &&
                (event.button.button == SDL_BUTTON_LEFT || event.button.button == SDL_BUTTON_RIGHT)) {
                int px = 0, py = 0; SDL_GetWindowSize(window, &px, &py);
                if (px > 0 && py > 0 && scrabble_options_open && event.button.button == SDL_BUTTON_LEFT) {
                    float x = event.button.x * 912.0f / px;
                    float y = (py - event.button.y) * 684.0f / py;
                    for (int row = 0; row < 4; row++) {
                        float center = 474.0f - row * 48.0f;
                        if (x >= 102 && x <= 810 && y >= center - 18 && y <= center + 18) {
                            if (row == scrabble_options_selected) scrabble_modify_option(&scrabble_draft, row, 1);
                            else scrabble_options_selected = row;
                            break;
                        }
                    }
                } else if (px > 0 && py > 0 && !scrabble_options_open) {
                    int64_t phase = nw_scrabble_info(scrabble_handle, 0);
                    nw_scrabble_pointer(scrabble_handle,
                        (int64_t)(event.button.x * 1000000.0f / px),
                        (int64_t)((py - event.button.y) * 1000000.0f / py), px, py,
                        event.button.button == SDL_BUTTON_RIGHT ? 2 : 0, 0, (int64_t)SDL_GetTicks());
                    if (phase != 1 && nw_scrabble_info(scrabble_handle, 0) == 1)
                        nw_scrabble_action(scrabble_handle, 10, 0, (int64_t)SDL_GetTicks());
                }
            }
            if (event.type == SDL_EVENT_MOUSE_MOTION && scrabble_mode && !scrabble_options_open) {
                int px = 0, py = 0; SDL_GetWindowSize(window, &px, &py);
                if (px > 0 && py > 0) nw_scrabble_pointer(scrabble_handle,
                    (int64_t)(event.motion.x * 1000000.0f / px),
                    (int64_t)((py - event.motion.y) * 1000000.0f / py), px, py, 0, 1, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && crossword_mode &&
                (event.button.button == SDL_BUTTON_LEFT || event.button.button == SDL_BUTTON_RIGHT)) {
                int px = 0, py = 0;
                SDL_GetWindowSize(window, &px, &py);
                if (px > 0 && py > 0 && crossword_options_open && event.button.button == SDL_BUTTON_LEFT) {
                    float x = event.button.x * 912.0f / px;
                    float y = (py - event.button.y) * 684.0f / py;
                    for (int row = 0; row < 4; row++) {
                        float center = 474.0f - row * 48.0f;
                        if (x >= 102 && x <= 810 && y >= center - 18 && y <= center + 18) {
                            if (row == crossword_options_selected) crossword_modify_option(&crossword_draft, row, 1);
                            else crossword_options_selected = row;
                            break;
                        }
                    }
                } else if (px > 0 && py > 0 && !crossword_options_open)
                    nw_crossword_pointer(crossword_handle,
                        (int64_t)(event.button.x * 1000000.0f / px),
                        (int64_t)((py - event.button.y) * 1000000.0f / py),
                        px, py, event.button.button == SDL_BUTTON_RIGHT ? 2 : 0,
                        (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && go_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0)
                    nw_go_pointer(go_handle,
                        (int64_t)(event.button.x * 1000000.0f / (float)px),
                        (int64_t)((py - event.button.y) * 1000000.0f / (float)py),
                        px, py, (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && ncup_monte_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0)
                    nw_ncup_monte_pointer(ncup_monte_handle,
                        (int64_t)(event.button.x * 1000000.0f / (float)px),
                        (int64_t)((py - event.button.y) * 1000000.0f / (float)py),
                        (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && tracking_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0)
                    nw_tracking_pointer(tracking_handle,
                        (int64_t)(event.button.x * 1000000.0f / (float)px),
                        (int64_t)((py - event.button.y) * 1000000.0f / (float)py),
                        (int64_t)SDL_GetTicks());
            }
            if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN && two_hands_mode) {
                int px = 0, py = 0;
                SDL_GetWindowSizeInPixels(window, &px, &py);
                if (px > 0 && py > 0)
                    nw_two_hands_pointer(two_hands_handle,
                        (int64_t)(event.button.x * 1000000.0f / (float)px),
                        (int64_t)((py - event.button.y) * 1000000.0f / (float)py),
                        1, (int64_t)SDL_GetTicks());
            }
        }
        if (!maze_mode && playing && SDL_GetTicks() - last_step > 700) { step = true; last_step = SDL_GetTicks(); }
        if (monkey_ladder_mode)
            nw_monkey_ladder_action(monkey_ladder_handle, 1, 0, (int64_t)SDL_GetTicks());
        if (nback3d_mode)
            nw_nback3d_action(nback3d_handle, 2, 0, (int64_t)SDL_GetTicks());
        if (marble_mode) {
            Uint64 now = SDL_GetTicks();
            nw_marble_advance(marble_handle, (int64_t)(now - last_marble_tick));
            last_marble_tick = now;
        }
        if (count_mode)
            nw_count_advance(count_handle, (int64_t)SDL_GetTicks());
        if (mr_time_mode)
            nw_mr_time_advance(mr_time_handle, (int64_t)SDL_GetTicks());
        if (graph_mapping_mode)
            nw_graph_mapping_advance(graph_mapping_handle, (int64_t)SDL_GetTicks());
        if (matrix_reasoning_mode)
            nw_matrix_reasoning_advance(matrix_reasoning_handle, (int64_t)SDL_GetTicks());
        if (in_the_dark_mode)
            nw_in_the_dark_advance(in_the_dark_handle, (int64_t)SDL_GetTicks());
        if (removals_mode)
            nw_removals_advance(removals_handle, (int64_t)SDL_GetTicks());
        if (custody_mode)
            nw_custody_advance(custody_handle, (int64_t)SDL_GetTicks());
        if (concentration_mode)
            nw_concentration_advance(concentration_handle, (int64_t)SDL_GetTicks());
            if (recognition_mode)
                nw_recognition_advance(recognition_handle, (int64_t)SDL_GetTicks());
            if (reflex_mode)
                nw_reflex_advance(reflex_handle, (int64_t)SDL_GetTicks());
        if (ncup_monte_mode)
            nw_ncup_monte_advance(ncup_monte_handle, (int64_t)SDL_GetTicks());
        if (tracking_mode)
            nw_tracking_advance(tracking_handle, (int64_t)SDL_GetTicks());
        if (lookout_mode)
            nw_lookout_advance(lookout_handle, (int64_t)SDL_GetTicks());
        if (pursuit_mode)
            nw_pursuit_advance(pursuit_handle, (int64_t)SDL_GetTicks());
        if (out_of_sight_mode)
            nw_out_of_sight_advance(out_of_sight_handle, (int64_t)SDL_GetTicks());
        if (buzz_wire_mode)
            nw_buzz_wire_advance(buzz_wire_handle, (int64_t)SDL_GetTicks());
        if (donkey_mode)
            nw_donkey_advance(donkey_handle, (int64_t)SDL_GetTicks());
        if (two_hands_mode)
            nw_two_hands_advance(two_hands_handle, (int64_t)SDL_GetTicks());
        if (overrun_mode)
            nw_overrun_advance(overrun_handle, (int64_t)SDL_GetTicks());
        if (step) {
            trial += 1;
        }

        int width = 0, height = 0;
        SDL_GetWindowSizeInPixels(window, &width, &height);
        nw_view v = view_for(width, height);

        int64_t length = numberology_mode && numberology_options_open
            ? nw_numberology_options_frame_write(buffer, FRAME_CAPACITY, 0, numberology_options_selected,
                  numberology_draft.level, numberology_draft.trials, numberology_draft.adaptive)
            : algebra_mode && algebra_options_open
            ? nw_algebra_options_frame_write(buffer, FRAME_CAPACITY, 0, algebra_options_selected,
                  algebra_draft.level, algebra_draft.trials, algebra_draft.show_mistakes, algebra_draft.adaptive)
            : scramble_mode && scramble_options_open
            ? nw_scramble_options_frame_write(buffer, FRAME_CAPACITY, 0, scramble_options_selected,
                  scramble_draft.level, scramble_draft.trials, scramble_draft.show_mistakes, scramble_draft.adaptive)
            : scramble_mode ? nw_scramble_frame_write(buffer, FRAME_CAPACITY, scramble_handle, 0, width, height)
            : scrabble_mode && scrabble_options_open
            ? nw_scrabble_options_frame_write(buffer, FRAME_CAPACITY, 0, scrabble_options_selected,
                  scrabble_draft.level, scrabble_draft.trials, scrabble_draft.show_mistakes, scrabble_draft.adaptive)
            : scrabble_mode ? nw_scrabble_frame_write(buffer, FRAME_CAPACITY, scrabble_handle, 0, width, height)
            : crossword_mode && crossword_options_open
            ? nw_crossword_options_frame_write(buffer, FRAME_CAPACITY, 0, crossword_options_selected,
                  crossword_draft.level, crossword_draft.trials, crossword_draft.show_mistakes, crossword_draft.adaptive)
            : maze_mode ? nw_you_are_here_frame_write(buffer, FRAME_CAPACITY, maze_handle,
                                          0, width, height)
            : (sokoban_mode
                ? nw_sokoban_frame_write(buffer, FRAME_CAPACITY, sokoban_handle,
                                         0, width, height)
            : (monkey_ladder_mode
                ? nw_monkey_ladder_frame_write(buffer, FRAME_CAPACITY,
                                               monkey_ladder_handle, 0,
                                               width, height)
            : (nback3d_mode
                ? nw_nback3d_frame_write(buffer, FRAME_CAPACITY,
                                         nback3d_handle, 0, width, height)
            : (marble_mode
                ? nw_marble_frame_write(buffer, FRAME_CAPACITY,
                                        marble_handle, 0, width, height)
            : (tetris_mode
                ? nw_tetris_frame_write(buffer, FRAME_CAPACITY, tetris_handle,
                                        0, width, height)
            : (count_mode
                ? nw_count_frame_write(buffer, FRAME_CAPACITY, count_handle,
                                       0, width, height)
            : (mr_time_mode
                ? nw_mr_time_frame_write(buffer, FRAME_CAPACITY, mr_time_handle,
                                         0, width, height)
            : (graph_mapping_mode
                ? nw_graph_mapping_frame_write(buffer, FRAME_CAPACITY,
                                               graph_mapping_handle, 0,
                                               width, height)
            : (matrix_reasoning_mode
                ? nw_matrix_reasoning_frame_write(buffer, FRAME_CAPACITY,
                                                  matrix_reasoning_handle, 0,
                                                  width, height)
            : (in_the_dark_mode
                ? nw_in_the_dark_frame_write(buffer, FRAME_CAPACITY,
                                             in_the_dark_handle, 0, width, height)
            : (fog_mode
                ? nw_fog_frame_write(buffer, FRAME_CAPACITY,
                                     fog_handle, 0, width, height)
            : (removals_mode
                ? nw_removals_frame_write(buffer, FRAME_CAPACITY,
                                          removals_handle, 0, width, height)
            : (custody_mode
                ? nw_custody_frame_write(buffer, FRAME_CAPACITY,
                                         custody_handle, 0, width, height)
            : (concentration_mode
                ? nw_concentration_frame_write(buffer, FRAME_CAPACITY,
                                               concentration_handle, 0, width, height)
            : (recognition_mode
                ? nw_recognition_frame_write(buffer, FRAME_CAPACITY,
                                             recognition_handle, 0, width, height)
            : (trivia_mode
                ? nw_trivia_frame_write(buffer, FRAME_CAPACITY,
                                        trivia_handle, 0, width, height)
            : (reflex_mode
                ? nw_reflex_frame_write(buffer, FRAME_CAPACITY,
                                        reflex_handle, 0, width, height)
            : (algebra_mode
                ? nw_algebra_frame_write(buffer, FRAME_CAPACITY,
                                         algebra_handle, 0, width, height)
            : (numberology_mode
                ? nw_numberology_frame_write(buffer, FRAME_CAPACITY,
                                             numberology_handle, 0, width, height)
            : (jigsaw_mode
                ? nw_jigsaw_frame_write(buffer, FRAME_CAPACITY,
                                        jigsaw_handle, 0, width, height)
            : (sudoku_mode
                ? nw_sudoku_frame_write(buffer, FRAME_CAPACITY,
                                        sudoku_handle, 0, width, height)
            : (go_mode
                ? nw_go_frame_write(buffer, FRAME_CAPACITY, go_handle, 0, width, height)
            : (crossword_mode
                ? nw_crossword_frame_write(buffer, FRAME_CAPACITY, crossword_handle, 0, width, height)
            : (crossed_wires_mode
                ? nw_crossed_wires_frame_write(buffer, FRAME_CAPACITY,
                                               crossed_wires_handle, 0,
                                               width, height)
            : (ncup_monte_mode
                ? nw_ncup_monte_frame_write(buffer, FRAME_CAPACITY,
                                            ncup_monte_handle, 0, width, height)
            : (tracking_mode
                ? nw_tracking_frame_write(buffer, FRAME_CAPACITY,
                                          tracking_handle, 0, width, height)
            : (lookout_mode
                ? nw_lookout_frame_write(buffer, FRAME_CAPACITY,
                                         lookout_handle, 0, width, height)
            : (pursuit_mode
                ? nw_pursuit_frame_write(buffer, FRAME_CAPACITY,
                                         pursuit_handle, 0, width, height)
            : (out_of_sight_mode
                ? nw_out_of_sight_frame_write(buffer, FRAME_CAPACITY,
                                              out_of_sight_handle, 0, width, height)
            : (buzz_wire_mode
                ? nw_buzz_wire_frame_write(buffer, FRAME_CAPACITY,
                                           buzz_wire_handle, 0, width, height)
            : (donkey_mode
                ? nw_donkey_frame_write(buffer, FRAME_CAPACITY,
                                        donkey_handle, 0, width, height)
            : (two_hands_mode
                ? nw_two_hands_frame_write(buffer, FRAME_CAPACITY,
                                           two_hands_handle, 0, width, height)
            : (overrun_mode
                ? nw_overrun_frame_write(buffer, FRAME_CAPACITY,
                                         overrun_handle, 0, width, height)
            : (taskhub_mode
                ? nw_taskhub_write(buffer, FRAME_CAPACITY, category, selected,
                                   0, width, height)
                : nw_title_write(buffer, FRAME_CAPACITY, trial % 4, 0, 1, 1)))))))))))))))))))))))))))))))))));

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
    if (maze_handle) nw_you_are_here_destroy(maze_handle);
    if (sokoban_handle) nw_sokoban_destroy(sokoban_handle);
    if (monkey_ladder_handle) nw_monkey_ladder_destroy(monkey_ladder_handle);
    if (nback3d_handle) nw_nback3d_destroy(nback3d_handle);
    if (marble_handle) nw_marble_destroy(marble_handle);
    if (tetris_handle) nw_tetris_destroy(tetris_handle);
    if (count_handle) nw_count_destroy(count_handle);
    if (mr_time_handle) nw_mr_time_destroy(mr_time_handle);
    if (graph_mapping_handle) nw_graph_mapping_destroy(graph_mapping_handle);
    if (matrix_reasoning_handle) nw_matrix_reasoning_destroy(matrix_reasoning_handle);
    if (in_the_dark_handle) nw_in_the_dark_destroy(in_the_dark_handle);
    if (fog_handle) nw_fog_destroy(fog_handle);
    if (removals_handle) nw_removals_destroy(removals_handle);
    if (custody_handle) nw_custody_destroy(custody_handle);
    if (concentration_handle) nw_concentration_destroy(concentration_handle);
    if (recognition_handle) nw_recognition_destroy(recognition_handle);
        if (trivia_handle) nw_trivia_destroy(trivia_handle);
    if (reflex_handle) nw_reflex_destroy(reflex_handle);
    if (algebra_handle) nw_algebra_destroy(algebra_handle);
    if (numberology_handle) nw_numberology_destroy(numberology_handle);
    if (jigsaw_handle) nw_jigsaw_destroy(jigsaw_handle);
    if (sudoku_handle) nw_sudoku_destroy(sudoku_handle);
    if (go_handle) nw_go_destroy(go_handle);
    if (crossed_wires_handle) nw_crossed_wires_destroy(crossed_wires_handle);
    if (crossword_handle) nw_crossword_destroy(crossword_handle);
    if (scrabble_handle) nw_scrabble_destroy(scrabble_handle);
    if (scramble_handle) nw_scramble_destroy(scramble_handle);
    if (ncup_monte_handle) nw_ncup_monte_destroy(ncup_monte_handle);
    if (tracking_handle) nw_tracking_destroy(tracking_handle);
    if (lookout_handle) nw_lookout_destroy(lookout_handle);
    if (pursuit_handle) nw_pursuit_destroy(pursuit_handle);
    if (out_of_sight_handle) nw_out_of_sight_destroy(out_of_sight_handle);
    if (buzz_wire_handle) nw_buzz_wire_destroy(buzz_wire_handle);
    if (donkey_handle) nw_donkey_destroy(donkey_handle);
    if (two_hands_handle) nw_two_hands_destroy(two_hands_handle);
    if (overrun_handle) nw_overrun_destroy(overrun_handle);
    SDL_Quit();
    return 0;
}
