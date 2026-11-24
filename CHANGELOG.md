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
