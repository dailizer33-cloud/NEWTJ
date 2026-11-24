# Changelog

## Phase 17
- **Fix:** with Player ESP OFF and MM2 Role ESP ON, the normal `TayJay_PlayerESP`
  billboard (name + HP) was still created every 0.75 s by the ESP loop. The normal
  billboard is now gated by `states.ESP` only; MM2 keeps using the shared highlight.
- **Fix:** turning Player ESP off while MM2 is on now removes the normal billboard
  (before, it was skipped whenever MM2 was on).
- **Fix:** MM2 role billboard no longer gets orphaned if the adornment part switches
  between `Head` and `PrimaryPart`; MM2 cleanup covers both.
- `scripts/static-check.sh` now checks the three points above and was verified to
  FAIL on the Phase 16 source and PASS on Phase 17.
- README rewritten: this is an executor-style client script, not a Studio-ready module.

## Phase 16
- MM2 Role ESP uses its own `TayJay_MM2RoleESP` BillboardGui instead of reusing
  `TayJay_PlayerESP`. See `patches/phase16_mm2_billboard_fix.lua`.


## Phase 18.2 / 18.3
- Restored the title `UIGradient` / `ColorSequence.new` constructor and parent assignment.
- Added source-aware TargetService unlock protection.
- Added TargetService reset during startup and before global Owner shutdown in STOP ALL.
- Kept Dynamic Walk nearest-target selection, 25-stud range, and 0.25-second attack cooldown unchanged.
- Added structural regression guards in `static-check.sh`. Static checks are not a Luau parser or live Delta runtime test.


## Phase 18.4 regression fix
- Corrected the `warp_mode` unlock guard to accept a Death Note-owned target, matching the WARP activation call site.
- Kept `warp_off` and `movement_owner_switch` restricted to WARP-owned targets.
- Added static regression assertions for the WARP activation and unlock ownership contract.
- Live Delta testing is still required for target handoff and StopAll behavior.
