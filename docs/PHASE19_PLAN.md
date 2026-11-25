# Phase 19 Rebuild Plan

Last reconciled: 2026-11-25
Baseline: `main` at `82823cb11afa2e537cf55f4159f4e10f5e260085`
Working branch: `phase19-rebuild`
Rollback branch: `freeze/phase19-baseline-20261125`
Current verified branch HEAD before this document update: `4bc89096ec43e9910c99fd5b0bbb4601c7b0a63f`

## Operating rules

- `main.lua` on GitHub is the source of truth.
- Work only on `phase19-rebuild` until Phase 19G passes.
- Never modify `freeze/phase19-baseline-20261125`.
- One runtime concern per commit.
- Do not retune Monster movement during State/Cleanup work.
- Do not merge to `main` before static, structural, and live gates pass.
- A workflow-definition commit is not proof that its runtime patch was applied. Require a later commit that changes `main.lua`.

## Current truth

### 19A Freeze — PASS

- [x] Baseline frozen.
- [x] Working branch created from the same commit.
- [x] Rollback rules recorded.

### 19B Audit — PASS

- [x] State, target, movement, worker, connection, visual, and cleanup ownership documented in `docs/PHASE19B_AUDIT.md`.
- [x] Phase 19 invariants documented.

### 19C State — HOLD pending focused fix application

Completed in `main.lua` by commit `be48397890f513b6bb08160329e8c8111593316a`:

- [x] Transactional `StateService` integrated.
- [x] Core writers for WARP, WALK, DN WARP, AutoWarp, MonsterWarp, MM2, TargetService, and STOP ALL migrated.
- [x] Movement group exclusion encoded.

Prepared but not yet verified as applied to `main.lua`:

- [ ] Startup conflict repair uses reason `startup_repair`.
- [ ] `syncButtonState` compares before/after and invokes only callbacks for changed states.
- [ ] Old full-snapshot loop `for changedKey, changedValue in pairs(result) do` is absent.
- [ ] Focused structural gate passes on the resulting `main.lua` commit.

19C exit gate: a commit after `4bc89096ec43e9910c99fd5b0bbb4601c7b0a63f` must modify `main.lua` and `patches/phase19c_state_service.lua`, then the verification workflow must pass.

## Current command path

### Apply the pending focused fix

Use workflow `.github/workflows/phase19c-fix-startup-sync.yml` on branch `phase19-rebuild`.
It runs:

```bash
python3 scripts/fix_phase19c_startup_sync.py
```

Expected commit message:

```text
Phase 19C: repair startup state and sync only changed UI
```

### Verify locally or in Actions

```bash
python3 scripts/verify_phase19c.py
bash static-check.sh main.lua
```

Required Phase 19C assertions:

```bash
grep -qF '"startup_repair"' main.lua
grep -qF 'local before = StateService:Snapshot()' main.lua
grep -qF 'local after = StateService:Snapshot()' main.lua
grep -qF 'if before[changedKey] ~= changedValue and uiSyncRegistry[changedKey] then' main.lua
! grep -qF 'for changedKey, changedValue in pairs(result) do' main.lua
```

### Inspect direct writers

```bash
grep -nE 'states\.(KillAura|NormalKillAura|DNWarp|AutoWarp|MonsterWarp|MM2RoleESP)[[:space:]]*=' main.lua
```

Review every match. Comparisons using `==` are reads, not writers. Initialization/default assignment is allowed; runtime feature mutation must use `StateService`.

## Recovery sequence

1. Trigger the focused-fix workflow on `phase19-rebuild`.
2. Confirm a new bot commit modifies both `main.lua` and `patches/phase19c_state_service.lua`.
3. Run `scripts/verify_phase19c.py` and `static-check.sh`.
4. Review remaining direct-writer matches manually.
5. If any writer remains, make one focused migration commit and rerun both checks.
6. Mark 19C PASS only after the resulting `main.lua` commit and checks are visible.
7. Begin 19D on a new commit without changing Monster tuning.

## 19D Movement — BLOCKED by 19C

- [ ] Enforce one movement owner.
- [ ] Centralize acquire, handoff, cancel, and restore.
- [ ] Prevent concurrent WARP/MONSTER/player movement writes.
- [ ] Restore properties only when released by the current owner.

## 19E Cleanup

- [ ] Register connections, workers, tweens, instances, and temporary character state.
- [ ] Route normal toggle-off, STOP ALL, respawn, and re-execution through shared cleanup.
- [ ] Make cleanup idempotent.

## 19F Modules

- [ ] Keep single-file distribution while separating StateService, TargetService, MovementService, CleanupService, ESPService, and UIController responsibilities.

## 19G Gate and release

- [ ] Run static and Phase 19 structural checks.
- [ ] Run syntax/analyzer checks when available.
- [ ] Live-test WARP ↔ MONSTER, target death/leave, respawn, STOP ALL, and two consecutive executions.
- [ ] Update README and CHANGELOG.
- [ ] Review diff and scan changed content for secrets.
- [ ] Merge through a pull request only after every gate passes.
