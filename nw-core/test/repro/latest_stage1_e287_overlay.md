# Latest Stage1 integration snapshot — 2026-10-01

This is a recovery/reproduction record, not a replacement for the shared
compiler checkout or evidence of complete Marble Maze fidelity.

## Exact source boundary

- Upstream Elisa compiler HEAD: `e2871b2cbfc601b9e13dc50d31184a22303e655d`.
- Overlay: `latest_stage1_e287_overlay.patch`, relative to that exact HEAD.
- Overlay SHA-256: `55f71d0d5a357a8bd71f8e1cb82b8423b5c19b1b9c669d2d545017ef30a0127e`.
- Combined source fingerprint: `d2b607b8dc3a7e936d67e8683ba48833d76a011b731ef9bf003f593f7f8a6dd0`.
- Seed Stage0 HEAD: `a2f9429ced194b0bdc3732372c84d17fd9bfb593`, clean tree.
- Seed Stage0 SHA-256: `075475481c3e084581f79ff148a8815d6621ba556709d03134116f6e73c12e11`.
- Built Stage1 SHA-256: `c6d28027b7ad6012bf711144912c2f5cf05ae857e302cde8a05cc99ca687cf50`.
- Private checkout used: `/private/tmp/nw-elisa-latest-oct1.d971pj/compiler`.

The fingerprint hashes dirty Git content, not the entire committed tree; use
it together with the exact HEAD. Temporary paths are evidence locations, not
durable dependencies. Rebuild from the durable patch if they disappear.

## What this preserves and corrects

The overlay reconciles the existing local compiler parity repairs with 25
new upstream commits. It is deliberately a complete integration snapshot,
not just the new four-line bootstrap correction. Do not apply it blindly to
a different revision or an already modified shared checkout.

The new `codegen_aggregate_copies.elisa` used four `is _` presence checks
that the authoritative Stage0 rejects. They are replaced with `!= null`, the
established nullable presence check. The new aggregate-copy optimization is
retained; neither Stage0 checking nor the Stage1 semantic gate is weakened.

Retained local Python-module error ownership/reporting changes are paired.
Upstream f-string error-view rehoming is retained alongside the local
character-literal scanning fix. Upstream region-owned handler capture and
hoisted exclusivity diagnostic names supersede the two older local fixes;
those obsolete hunks were not transplanted. All other applicable local
changes were retained. The original shared compiler tree was not edited.

## Reproduction discipline

1. Fetch and inspect current upstream before choosing the compiler. This
   snapshot reproduces a boundary; it does not assert that e287 remains newest.
2. For this exact reproduction, use an isolated checkout at the HEAD above.
   Resolve the patch targets with `git apply --check` first; use the agent's
   file-editing mechanism to transplant the patch. Never reset, stash, or
   overwrite another agent's shared changes to make it apply.
3. Rebuild Stage0 from the current authoritative Go source. Record its HEAD,
   dirty-content fingerprint, and product hash. The historical binary hash
   above identifies this run, not all future builds.
4. Use `DEVELOPER_DIR=/Library/Developer/CommandLineTools` for native linking
   on this host. Include `/usr/sbin:/sbin` in PATH: importing the original
   application's pyglet code needs `sysctl`.
5. Seed Stage1 using `ELISA_STAGE1_SEED_OPT_LEVEL=-O1`, `ELISACORE_STRICT_FP=1`,
   `ELISA_STAGE1_SEMANTIC_GATE=1`, and the explicit Stage0 binary. Respect
   the compiler's host-global seed guard; do not override another seed.
6. Confirm the vendored runtime matches canonical Stage0 runtime bytes;
   verify Stage1 source freshness and record the product hash.
7. Run `large_aggregate_copy_memcpy_smoke.sh`, `stage1_product_smoke.sh`,
   and the complete `driver_acceptance_smoke.sh`, including WITH-STD.
8. Build the port with `build_latest_stage1_wasm.sh`, explicit compiler root
   and binary, and a private `NW_STAGE1_WASM_ARTIFACT` destination outside
   the compiler checkout. Keep its provenance guard enabled.
9. Run all artifact tests before promotion. Use `NWCORE_WASM_PATH` to
   select the private artifact for Node tests. Compare the 7,601-event
   Marble hard trace, including contact identities, against the retained
   core before making any production/compiler-provenance update.
10. Repeat the original-wheel strict replay without synchronization. Exact
    neutrality to an already imperfect port does not prove original parity.

At initial capture, bootstrap, aggregate-copy smoke, product smoke, complete
port artifact testing, and 7,601-event exact retained-core neutrality passed.
The full driver acceptance test was still running. Consult the newest plan
and physics manifest checkpoint for final gate/promotion status; this file
intentionally records the initial boundary without inventing later results.
