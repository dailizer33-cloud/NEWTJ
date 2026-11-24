#!/usr/bin/env bash
# NEWTJ - structural checks (Phase 16 + 17 + 18.2 + 18.3).
# These are grep-level checks on source structure. They do NOT replace a runtime test.
set -euo pipefail

FILE="${1:-main.lua}"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }
has()  { grep -qF -- "$2" <<<"$1"; }          # has "<text>" "<fixed string>"
line_of() { grep -nF -- "$2" <<<"$1" | head -n1 | cut -d: -f1; }

[ -f "$FILE" ] || fail "file not found: $FILE"

# ---------------------------------------------------------------- Phase 16
grep -q 'TayJay_MM2RoleESP' "$FILE"                 || fail 'dedicated MM2 billboard name missing'
pass 'dedicated MM2 billboard name present'

grep -q 'local function updateMM2RoleESP()' "$FILE" || fail 'updateMM2RoleESP missing'
grep -q 'local function clearMM2RoleESP()'  "$FILE" || fail 'clearMM2RoleESP missing'
pass 'MM2 update/cleanup functions present'

mm2="$(sed -n '/local MM2_ROLE_ESP_NAME = "TayJay_MM2RoleESP"/,/_G.TAYJAY_MM2_STOP = function()/p' "$FILE")"
[ -n "$mm2" ] || fail 'MM2 section not found'

has "$mm2" 'Instance.new("BillboardGui")'            || fail 'MM2 BillboardGui creation missing'
pass 'MM2 BillboardGui creation present'

if has "$mm2" 'FindFirstChild("TayJay_PlayerESP")'; then fail 'MM2 still reuses TayJay_PlayerESP'; fi
pass 'MM2 does not reuse TayJay_PlayerESP'

has "$mm2" 'billboard:Destroy()'                     || fail 'MM2 billboard cleanup missing'
pass 'MM2 billboard cleanup present'

# ---------------------------------------------------------------- Phase 17
esp="$(sed -n '/local function applyEspToCharacter(character)/,/registerUiSync("ESP"/p' "$FILE")"
[ -n "$esp" ] || fail 'applyEspToCharacter section not found'

has "$esp" 'if not states.ESP then'                  || fail 'normal ESP billboard guard (if not states.ESP) missing'
has "$esp" 'strayBillboard:Destroy()'                || fail 'normal ESP billboard guard does not destroy the billboard'
guard_line="$(line_of "$esp" 'if not states.ESP then')"
create_line="$(line_of "$esp" 'Instance.new("BillboardGui")')"
[ -n "$guard_line" ] && [ -n "$create_line" ] && [ "$guard_line" -lt "$create_line" ] \
  || fail 'ESP guard must come BEFORE the normal billboard is created'
pass 'normal Player ESP billboard is gated by states.ESP (MM2-only no longer creates it)'

sync="$(sed -n '/registerUiSync("ESP"/,/local function bindEspPlayer/p' "$FILE")"
[ -n "$sync" ] || fail 'ESP UI-sync section not found'
if has "$sync" 'elseif not states.MM2RoleESP'; then
  fail 'ESP-off branch still skips billboard removal while MM2 is on'
fi
has "$sync" 'billboard:Destroy()' || fail 'ESP-off branch does not remove the normal billboard'
pass 'ESP-off removes the normal billboard even while MM2 is on'

has "$mm2" 'rootBillboard:Destroy()' || fail 'MM2 cleanup does not cover PrimaryPart billboards'
has "$mm2" 'strayMM2:Destroy()'      || fail 'MM2 update does not drop stray billboards'
pass 'MM2 billboard cleanup covers Head and PrimaryPart'

# ---------------------------------------------------------------- Phase 18.3: TargetService lifecycle and ownership guards.
target="$(sed -n '/function TargetService:Unlock(reason, expectedSource)/,/function TargetService:SetTransient/p' "$FILE")"
[ -n "$target" ] || fail 'TargetService unlock/reset section missing'
has "$target" 'if expectedSource and currentSource ~= expectedSource then' \
  || fail 'TargetService source ownership guard missing'
has "$target" 'return false, "source_mismatch"' \
  || fail 'TargetService source mismatch rejection missing'
has "$target" 'function TargetService:Reset(reason)' \
  || fail 'TargetService reset method missing'
has "$target" 'self:StopCombatOwner(reason or "reset")' \
  || fail 'TargetService reset does not stop its combat Owner'
pass 'TargetService unlock is source-aware and Reset stops its combat Owner'

grep -qF 'TargetService:Reset("STARTUP_RESET")' "$FILE" \
  || fail 'startup persistent-target reset missing'
stopall="$(sed -n '/_G.TAYJAY_STOP_ALL = function()/,/print("\[TAYJAY\] STOP ALL completed/p' "$FILE")"
reset_line="$(line_of "$stopall" 'TargetService:Reset("STOP_ALL")')"
owners_line="$(line_of "$stopall" 'ResourceManager:StopAllOwners("STOP_ALL")')"
[ -n "$reset_line" ] && [ -n "$owners_line" ] && [ "$reset_line" -lt "$owners_line" ] \
  || fail 'STOP ALL must reset TargetService before global Owner shutdown'
pass 'startup and STOP ALL clear persistent TargetService state before Owner shutdown'

# ---------------------------------------------------------------- optional
if command -v luau-analyze >/dev/null 2>&1; then
  echo 'INFO: running luau-analyze (executor globals may show as unknown-global warnings)'
  luau-analyze "$FILE" || echo 'WARN: luau-analyze reported issues; review them manually'
else
  echo 'INFO: luau-analyze not installed; structural checks only.'
fi
echo 'Static Check: PASS'
