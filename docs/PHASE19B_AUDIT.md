# Phase 19B Audit

Audit target: `main.lua` on `phase19-rebuild`
Baseline commit: `82823cb11afa2e537cf55f4159f4e10f5e260085`
Audited blob: `31eff10aec9a881bf4554692ad105bfeaa967d12`

This phase is documentation-only. It does not change runtime behavior.

## 1. Confirmed architecture

### Session and re-execution

- Startup checks `_G.TAYJAY_STOP_ALL` and calls the previous session's function before replacing the session.
- This is the existing re-execution boundary and must remain functional throughout Phase 19.
- Phase 19E must route this boundary through the same cleanup paths used by normal feature shutdown.

### State

- Runtime feature flags are stored under `states`.
- Confirmed movement-related flags include `MonsterWarp`, `KillAura`, `DNWarp`, and `AutoWarp`.
- Existing conflict detection treats `MonsterWarp` as conflicting with any of `KillAura`, `DNWarp`, or `AutoWarp`.
- Existing code also directly writes multiple flags to `false`, confirming that mutation is distributed rather than exclusively mediated by one transition API.

### Target ownership

- `TargetService` is stored in both `TJ.TargetService` and `Main.TargetService`.
- It exposes lock state and player validation through methods including `IsLocked()` and `GetPlayer()`.
- Confirmed unlock reasons include `invalid_player`.
- Confirmed source-aware behavior includes the `deathnote` source.
- Source-aware unlock rules added before Phase 19 must be preserved; source ownership must be checked before release.

### Resource declarations and movement

`ResourceManager` already declares intended writers and priorities:

| Owner | Declared writes | Priority |
|---|---|---:|
| Speed | WalkSpeed | 10 |
| Fly | Position, HumanoidFlags, AnimateState | 30 |
| ShadowHunter | Position, Velocity, Collision | 50 |
| MonsterWarp | Position, Velocity, Collision | 60 |

The file describes these declarations as monitor-only. Therefore they are audit metadata, not yet proof that runtime movement writes are serialized.

### Workers, events, and visuals

- Startup contains a retry worker created with `task.spawn` and `task.wait` for boot GUI attachment.
- At least one persistent event connection is created from `LogService.MessageOut` and stored as `_tjLogConnection`.
- Player ESP and MM2 role ESP use distinct visual identities established in earlier phases: `TayJay_PlayerESP` and `TayJay_MM2RoleESP`.
- Highlight configuration is shared through ESP constants, while billboard lifecycle rules remain feature-specific.

## 2. Ownership map for Phase 19

| Mutable area | Current evidence | Required single owner |
|---|---|---|
| Feature flags | Direct `states.*` reads and writes | StateService |
| Target player/source | `TargetService` lock, source, player, unlock | TargetService |
| Position/CFrame | Resource declarations for Fly, ShadowHunter, MonsterWarp | MovementService |
| Velocity | ShadowHunter and MonsterWarp declarations | MovementService |
| Collision/noclip | ShadowHunter and MonsterWarp declarations | MovementService |
| WalkSpeed | Speed declaration; Monster behavior has recent tuning history | MovementService with property snapshot |
| Event connections | `_tjLogConnection` plus feature callbacks | CleanupService registry |
| Spawned workers | Boot retry plus feature loops | CleanupService cancellation tokens |
| ESP highlights | Shared visual configuration | ESPService |
| Player billboards | `TayJay_PlayerESP` | ESPService / Player ESP scope |
| MM2 billboards | `TayJay_MM2RoleESP` | ESPService / MM2 scope |
| UI toggle appearance | Coupled to feature callbacks | UIController derived from StateService |
| Session shutdown | `_G.TAYJAY_STOP_ALL` | CleanupService coordinator |

## 3. Confirmed risks

### R1 — Distributed state mutation

Direct writes to related movement flags can produce partial transitions if a callback errors between writes. Phase 19C must replace multi-flag edits with one transactional transition function.

### R2 — Detection without enforcement

A conflict detector and ResourceManager declarations exist, but declarations are explicitly monitor-only. Phase 19D must enforce ownership at every movement write boundary rather than only report conflicts.

### R3 — Target release by the wrong feature

Target state is source-aware. Any unconditional unlock can release a target owned by another feature. Every unlock in 19C/19D must include expected owner/source semantics.

### R4 — Split cleanup paths

Re-execution, feature toggles, player invalidation, respawn, and STOP ALL can reach shutdown from different entry points. If each path performs its own subset, workers or visuals can survive. Phase 19E must converge them on idempotent subsystem cleanup.

### R5 — Untracked asynchronous lifetime

`task.spawn`, waits, and event connections can outlive the state that created them unless they use session/feature tokens and registry-managed disconnectors. Phase 19E must give every worker and connection an explicit owner.

### R6 — Visual ownership overlap

Player ESP and MM2 have separate billboards but may share highlight behavior. Cleanup must remove only the visual scope being disabled unless global shutdown is requested.

### R7 — Property restoration race

Movement features write overlapping properties. A lower-priority or stale feature must not restore WalkSpeed, collision, velocity, or animation state after a new owner has acquired movement.

## 4. Invariants to implement and test

1. `MonsterWarp` and player-target movement modes cannot be active simultaneously.
2. A state transition either completes fully or leaves the previous valid state unchanged.
3. UI appearance is rendered from authoritative state after transition completion.
4. Only the current movement owner may write or restore movement-related properties.
5. Target unlock succeeds only for the expected source/owner, except global reset.
6. Every loop observes both a session token and its feature token.
7. Every event connection, tween, temporary instance, and worker belongs to one cleanup scope.
8. Normal toggle-off, target invalidation, respawn, STOP ALL, and re-execution call the same subsystem cleanup operations.
9. Cleanup is idempotent and safe when called in any order.
10. Player ESP cleanup does not delete MM2 role visuals, and MM2 cleanup does not recreate or preserve Player ESP billboards incorrectly.
11. STOP ALL leaves no movement owner, target lock, active state flag, worker, connection, tween, highlight, or billboard owned by the session.
12. Two consecutive executions produce one live session only.

## 5. Required 19C transition surface

The next phase should add a minimal authoritative API before changing movement code:

- `StateService:Get(name)`
- `StateService:IsEnabled(name)`
- `StateService:Transition(name, enabled, reason)`
- `StateService:DisableGroup(group, reason)`
- `StateService:Snapshot()`
- `StateService:Reset(reason)`
- `StateService:Subscribe(callback)`

Initial transition groups:

- `player_movement`: `KillAura`, `DNWarp`, `AutoWarp`
- `monster_movement`: `MonsterWarp`
- `visual_player`: Player ESP
- `visual_mm2`: MM2 role ESP

`Transition` must validate conflicts first, apply the complete state change second, then notify UI/subsystems. It must not move characters or destroy instances directly.

## 6. 19B exit decision

PASS for moving to 19C with these constraints:

- 19C changes state ownership only; it must not retune Monster movement.
- Existing `TargetService` source-aware behavior remains intact.
- Existing ResourceManager declarations remain available as audit metadata until 19D replaces monitor-only behavior with enforcement.
- Cleanup refactoring is deferred to 19E, but all new 19C subscriptions must already expose disconnect handles.
- No merge to `main` occurs before the 19G gate.
