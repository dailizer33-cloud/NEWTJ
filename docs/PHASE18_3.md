# NEWTJ Phase 18.3 - TargetService lifecycle hardening

## Source of truth
GitHub repository `dailizer33-cloud/NEWTJ`, branch `main`, file `main.lua` is the canonical source for future inspection and development from this phase onward.

## Changes
- Restored the title UIGradient and ColorSequence constructor and attached the gradient to the title label.
- Added `TargetService:Reset(reason)` to clear Player, Source, Locked, legacy mirror state, and DNWarp, then stop the dedicated TargetCombat Owner.
- Added startup reset to prevent a stale target from a prior executor session from surviving re-execution.
- Added a TargetService reset to STOP ALL before global ResourceManager Owner shutdown.
- Added source-aware Unlock rejection for mismatched expected sources and legacy Death Note/Warp release reasons.

## Preserved behavior
- Dynamic WALK nearest-living-target selection remains heartbeat-driven.
- WALK range remains 25 studs.
- Attack cooldown remains 0.25 seconds.
- Existing attack functions and original snapshot were not intentionally changed.

## Verification
- `static-check.sh` includes Phase 16/17 checks plus Phase 18.3 source guard, reset, startup, and STOP ALL ordering checks.
- Static structural checks do not replace Luau parser analysis or live Delta regression testing.
- Required live checks: execute twice, StopAll, nearest-target retargeting, Death Note target removal, and feature-owner cleanup.

## Deployment
The repository may be Private. Delta's unauthenticated `loadstring(game:HttpGet(...))()` cannot fetch a private raw file unless the runtime has a supported authenticated route. Make the repository Public only after reviewing the entire repository for secrets and private data.
