# Phase 17 - Normal ESP billboard isolation (follow-up to Phase 16)

## Why
Phase 16 gave MM2 its own billboard, but `applyEspToCharacter` still returned early only
when BOTH `states.ESP` and `states.MM2RoleESP` were false. With ESP off and MM2 on, the
background loop kept creating the normal name/HP billboard, so "ESP OFF + MM2 ON" was
not actually isolated.

## Changes (src/main.lua)
1. `applyEspToCharacter`: after the shared-highlight block, `if not states.ESP then`
   destroy any `TayJay_PlayerESP` billboard and `return`.
2. `registerUiSync("ESP")` off-branch: always remove the normal billboard; destroy the
   shared highlight only when MM2 is also off.
3. `updateMM2RoleESP` / `clearMM2RoleESP`: handle a stray MM2 billboard on `PrimaryPart`
   when the adornment switches between `Head` and `PrimaryPart`.

Diff: `patches/phase17_esp_billboard_guard.diff` (applies on top of the Phase 16 source).

## Verified here
- `scripts/static-check.sh` PASS on Phase 17, FAIL on Phase 16 and on the original.

## NOT verified (needs a real run)
- No Luau parser/analyzer or Roblox runtime was available when this was prepared, so
  syntax was checked by review only. Run `luau-analyze src/main.lua` and the checklist below.

## Runtime checklist
- ESP OFF + MM2 ON: only the MM2 role label is visible (no name/HP billboard).
- ESP ON + MM2 ON: both visible; check the two billboards (offsets 2.8 / 4.0) do not overlap badly.
- MM2 OFF while ESP ON: highlight returns to normal ESP colors, MM2 label gone.
- ESP OFF while MM2 ON: name/HP billboard disappears, role highlight stays.
- Role change, respawn, STOP ALL, re-run twice.
