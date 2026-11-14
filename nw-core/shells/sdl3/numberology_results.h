#ifndef NW_NUMBEROLOGY_RESULTS_H
#define NW_NUMBEROLOGY_RESULTS_H

#include <stdbool.h>
#include <stdint.h>

typedef struct nw_numberology_result_record nw_numberology_result_record;
typedef struct {
    nw_numberology_result_record *current;
    nw_numberology_result_record *pending;
} nw_numberology_results;

void nw_numberology_results_start(nw_numberology_results *, int64_t level, int64_t trials, int adaptive);
void nw_numberology_results_judge(nw_numberology_results *, int64_t trial, int64_t level, int correct);
void nw_numberology_results_finish(nw_numberology_results *, int64_t right);
void nw_numberology_results_retry(nw_numberology_results *);
void nw_numberology_results_close(nw_numberology_results *);

#endif
