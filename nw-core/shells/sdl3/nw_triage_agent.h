#ifndef NW_TRIAGE_AGENT_H
#define NW_TRIAGE_AGENT_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int64_t frame_seq;
    int64_t timestamp_ns;
    int64_t done;
    int64_t open_receipt;
    int64_t outcome_receipt;
    double outcome_scalar;
    int64_t action_port;
    int64_t receipt_frame_seq;
    int64_t receipt_timestamp_ns;
    int64_t trial;
    char digest[64];
    char stimulus_digest[64];
} NWAgentPublication;

typedef NWAgentPublication NWTriagePublication;

int64_t nw_triage_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
int64_t nw_notebook_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_triage_agent_destroy(int64_t handle);
int64_t nw_triage_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_triage_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWTriagePublication *result);
void nw_notebook_agent_destroy(int64_t handle);
int64_t nw_notebook_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_notebook_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_where_was_it_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_where_was_it_agent_destroy(int64_t handle);
int64_t nw_where_was_it_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_where_was_it_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_same_or_mirror_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_same_or_mirror_agent_destroy(int64_t handle);
int64_t nw_same_or_mirror_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_same_or_mirror_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_point_of_view_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_point_of_view_agent_destroy(int64_t handle);
int64_t nw_point_of_view_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_point_of_view_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_inside_or_out_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_inside_or_out_agent_destroy(int64_t handle);
int64_t nw_inside_or_out_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_inside_or_out_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_touching_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_touching_agent_destroy(int64_t handle);
int64_t nw_touching_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_touching_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_crossings_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_crossings_agent_destroy(int64_t handle);
int64_t nw_crossings_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_crossings_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_delay_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_delay_agent_destroy(int64_t handle);
int64_t nw_delay_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_delay_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_which_is_nearer_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_which_is_nearer_agent_destroy(int64_t handle);
int64_t nw_which_is_nearer_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_which_is_nearer_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_stop_switch_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_stop_switch_agent_destroy(int64_t handle);
int64_t nw_stop_switch_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_stop_switch_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_hold_it_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_hold_it_agent_destroy(int64_t handle);
int64_t nw_hold_it_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_hold_it_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_hold_it_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_time_it_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_beat_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_catch_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_echo_cave_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_drone_hoops_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_field_manual_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_safecracker_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_stagehand_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_loading_dock_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_gunslinger_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_tuner_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
int64_t nw_glider_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_time_it_agent_destroy(int64_t handle);
void nw_beat_agent_destroy(int64_t handle);
void nw_catch_agent_destroy(int64_t handle);
void nw_echo_cave_agent_destroy(int64_t handle);
void nw_drone_hoops_agent_destroy(int64_t handle);
void nw_field_manual_agent_destroy(int64_t handle);
void nw_safecracker_agent_destroy(int64_t handle);
void nw_stagehand_agent_destroy(int64_t handle);
void nw_loading_dock_agent_destroy(int64_t handle);
void nw_gunslinger_agent_destroy(int64_t handle);
void nw_tuner_agent_destroy(int64_t handle);
void nw_glider_agent_destroy(int64_t handle);
int64_t nw_time_it_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_beat_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_catch_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_echo_cave_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_drone_hoops_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_field_manual_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_safecracker_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_stagehand_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_loading_dock_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_gunslinger_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_tuner_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
/* Bits 0 through 7 select the ports held for one publication.
 * If a verdict includes this action, action_port is 256 plus the mask. */
int64_t nw_catch_agent_act_mask(int64_t handle, int64_t mask, int64_t timestamp_ns);
/* Bits 0 through 8 select the ports for one publication. If a verdict
 * includes this action, action_port is 512 plus the mask. */
int64_t nw_echo_cave_agent_act_mask(int64_t handle, int64_t mask, int64_t timestamp_ns);
int64_t nw_drone_hoops_agent_act_mask(int64_t handle, int64_t mask, int64_t timestamp_ns);
int64_t nw_glider_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_time_it_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_beat_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_catch_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_echo_cave_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_drone_hoops_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_field_manual_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_safecracker_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_stagehand_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_loading_dock_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_gunslinger_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_tuner_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_glider_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_balance_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_balance_agent_destroy(int64_t handle);
int64_t nw_balance_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_balance_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_juggler_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_juggler_agent_destroy(int64_t handle);
int64_t nw_juggler_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_juggler_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_lander_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_lander_agent_destroy(int64_t handle);
int64_t nw_lander_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_lander_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);
int64_t nw_time_it_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_beat_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_catch_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_echo_cave_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_drone_hoops_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_field_manual_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_safecracker_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_stagehand_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_loading_dock_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_gunslinger_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_tuner_agent_audio(int64_t handle, uint8_t *pcm, int64_t capacity);
int64_t nw_public_outcome_verify_frame(const uint8_t *rgba, int64_t bytes,
    int64_t width, int64_t height, const uint8_t *expected, double scalar);

int64_t nw_signals_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_signals_agent_destroy(int64_t handle);
int64_t nw_signals_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_signals_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_fold_it_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_fold_it_agent_destroy(int64_t handle);
int64_t nw_fold_it_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_fold_it_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_who_knows_what_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_who_knows_what_agent_destroy(int64_t handle);
int64_t nw_who_knows_what_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_who_knows_what_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_dam_keeper_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_dam_keeper_agent_destroy(int64_t handle);
int64_t nw_dam_keeper_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_dam_keeper_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_dispatch_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral, bool coach);
void nw_dispatch_agent_destroy(int64_t handle);
int64_t nw_dispatch_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_dispatch_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_sonar_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_sonar_agent_destroy(int64_t handle);
int64_t nw_sonar_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_sonar_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_gamble_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, double capacity, double refill, int64_t ports, bool neutral);
void nw_gamble_agent_destroy(int64_t handle);
int64_t nw_gamble_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_gamble_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

int64_t nw_crazy_cog_agent_create(int64_t rung, int64_t trials, int64_t adaptive,
    int64_t seed, int64_t ports, bool neutral);
void nw_crazy_cog_agent_destroy(int64_t handle);
int64_t nw_crazy_cog_agent_act(int64_t handle, int64_t port, int64_t timestamp_ns);
int64_t nw_crazy_cog_agent_publish(int64_t handle, double elapsed_seconds, int64_t timestamp_ns,
    uint8_t *frame, int64_t capacity, int32_t width, int32_t height, int64_t black,
    NWAgentPublication *result);

#ifdef __cplusplus
}
#endif

#endif
