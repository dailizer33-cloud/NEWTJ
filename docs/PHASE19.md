# NEWTJ Phase 19.0 - Target lifecycle and movement safety

## Source
- Development branch: `fix/targetservice-warp-queue-phase19`
- Canonical script: `main.lua`
- The default `main` branch is not changed by this phase branch.

## Implemented

### TargetService lifecycle
- `Unlock(reason, expectedSource)` checks ownership for the WARP handoff reasons.
- `warp_mode` may release a `deathnote` target only.
- `warp_off` and `movement_owner_switch` may release a `warp` target only.
- Death Note and WALK unlock reasons are constrained to the `deathnote` source.
- `Reset(reason)` clears Player, Source, Locked, legacy mirrors and DNWarp, then stops the TargetCombat Owner.
- Startup and STOP ALL call Reset. STOP ALL resets TargetService before global Owner shutdown.

### Movement queue
- MovementController now has Enqueue, DrainQueue and CancelQueued.
- Requests are FIFO, deduplicated by owner/key, and only start after Transition, Owner and Platform ownership are clear.
- A queue generation invalidates pending work during ForceClear / STOP ALL.
- WARP and Monster Warp enqueue only retryable handoff failures (transition in progress or a previous platform still active).
- A successful stop handshake still performs immediate owner handoff; the queue is a fallback for the settling window, not a replacement for the existing synchronous handoff.
- WARP shows WAIT while queued. The WARP button cancels its queued request; pressing the active Monster/NPC mode again cancels the Monster request.

### Safe-ground checks
- Player WARP uses a downward raycast to require a collidable surface with an upward-facing normal before a hop or target approach.
- One-shot Death Note WARP rejects a destination when no safe floor is found.
- WARP's safety platform is placed relative to the detected floor, not blindly beneath the current Y coordinate.
- Monster ground lookup now returns nil when no walkable floor is detected. Monster far hops, loot hops and platform placement fail closed in that case.
- These checks reduce the risk of writing a destination below the map, but only live map testing can confirm behavior on every game's geometry.

### Preserved values
- WALK range: 25 studs.
- `atk_cd`: 0.25 seconds.
- Rapid Bite interval: 0.25 seconds.
- Skill Hybrid Bite cooldown in `main.lua`: 0.25 seconds.
- No requested attack timing was changed.

## Verification status
- Source-level preflight assertions passed before the branch update.
- `static-check.sh` was extended with Phase 19 assertions.
- GitHub Actions validation is pending; this workflow currently runs for pull requests targeting `main`.
- No Delta runtime test has been performed in this environment.

## Delta regression checklist
1. Execute the script twice; confirm stale TargetService target and combat owner do not survive re-execution.
2. Select a Death Note target, then enable WARP; confirm the handoff is accepted.
3. Stop WARP with a WARP-owned transient target; confirm unrelated Death Note targets cannot be cleared by a WARP shutdown.
4. Start Monster Warp while WARP is active; confirm WARP physics disconnects, collision restores, the old platform is removed, and Monster Warp starts only after ownership is granted.
5. Trigger the transition/platform settling window and verify the queued request starts once, in FIFO order; cancel a queued request from its matching control.
6. Test WARP and Monster Warp at ground level, on slopes, near ledges, in caves, and in areas without a floor below. Confirm unsafe destinations are rejected and the character does not drop beneath the map.
7. Run STOP ALL with active and queued movement requests; confirm queue invalidation, target reset, physics cleanup, collision restoration, and UI removal.
8. Re-execute after STOP ALL and verify the menu opens normally.

Static checks are structural only. Passing them does not prove the script runs correctly in Delta or on live Roblox maps.
