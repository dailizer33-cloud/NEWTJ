# Phase 19 Rebuild Plan

Baseline: `main` at commit `82823cb11afa2e537cf55f4159f4e10f5e260085`

## Non-negotiable rules

- `main.lua` on GitHub remains the source of truth.
- Work only on `phase19-rebuild` until all gates pass.
- Keep `freeze/phase19-baseline-20261125` untouched as the rollback point.
- One phase per commit. Do not mix feature work with repair work.
- Preserve current user-visible behavior unless a phase explicitly changes it.
- Every state transition must be idempotent and safe on re-execution.
- No merge to `main` before static checks, targeted regression checks, and live executor tests pass.

## 19A — Freeze

- [x] Freeze current `main` into `freeze/phase19-baseline-20261125`.
- [x] Create working branch `phase19-rebuild` from the exact same commit.
- [x] Record baseline SHA and rollback rules.
- [ ] Capture current feature/state inventory from `main.lua`.

Exit gate: baseline and working branch point to the same commit, with no product-code changes.

## 19B — Audit

- [ ] Map every boolean state and every writer.
- [ ] Map `TargetService` lock/unlock/reset call sites and ownership rules.
- [ ] Map movement writers affecting Humanoid, HRP/CFrame, tweens, velocity, and noclip.
- [ ] Map long-running tasks, events, highlights, billboards, and UI callbacks.
- [ ] Identify duplicate loops, stale globals, unsafe fallbacks, and re-execution leaks.
- [ ] Convert findings into explicit invariants and regression checks.

Exit gate: every mutable subsystem has one documented owner and cleanup path.

## 19C — State

- [ ] Introduce one authoritative state transition layer.
- [ ] Replace direct conflicting state writes with named transitions.
- [ ] Encode mutual exclusion between Monster movement and player-target movement modes.
- [ ] Make enable/disable operations idempotent.
- [ ] Keep UI button visuals derived from actual state, not independent flags.

Exit gate: no feature can silently leave another feature half-enabled.

## 19D — Movement

- [ ] Introduce a single movement owner/arbitration contract.
- [ ] Centralize acquire, handoff, cancel, and restore behavior.
- [ ] Ensure WARP, MONSTER, KillAura/Dynamic Walk, and STOP ALL cannot write movement concurrently.
- [ ] Preserve the current Monster glide tuning unless a verified defect requires a change.
- [ ] Restore movement properties only when the current owner is releasing them.

Exit gate: exactly one subsystem may control movement at a time; handoff and disable are deterministic.

## 19E — Cleanup

- [ ] Build a cleanup registry for connections, tasks, instances, tweens, and temporary character state.
- [ ] Make STOP ALL call the same subsystem cleanup paths used by normal toggles.
- [ ] Verify respawn, target leave/death, re-execution, and UI destruction.
- [ ] Remove orphaned ESP/MM2 billboards and highlights.
- [ ] Guarantee cleanup can be called more than once without error.

Exit gate: STOP ALL and re-execution leave no active worker, movement owner, or visual artifact.

## 19F — Modules

- [ ] Split internal responsibilities into local module-style tables while keeping the single-file distribution.
- [ ] Planned boundaries: StateService, TargetService, MovementService, CleanupService, ESPService, UIController.
- [ ] Keep public globals minimal and document the remaining compatibility surface.
- [ ] Prevent circular ownership between UI, state, target, and movement layers.

Exit gate: features depend on service contracts instead of editing each other's internals.

## 19G — Gate and Release

- [ ] Run `static-check.sh main.lua`.
- [ ] Run Luau syntax/analyzer checks when available.
- [ ] Add targeted structural regression checks for all Phase 19 invariants.
- [ ] Live-test: WARP ↔ MONSTER switching, target death/leave, respawn, STOP ALL, and two consecutive executions.
- [ ] Update README and CHANGELOG with the exact implemented behavior.
- [ ] Review the final diff, scan changed content for secrets, then merge through a pull request.

Exit gate: all automated and live checks pass, rollback remains available, and no unrelated feature changed.
