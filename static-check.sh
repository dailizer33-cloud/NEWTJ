#!/usr/bin/env bash
# TAYJAY SOFTMOVE - structural checks (Phase 16 + Phase 17).
# These are grep-level checks on source structure. They do NOT replace a runtime test.
set -euo pipefail

FILE="${1:-src/main.lua}"

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

# ---------------------------------------------------------------- optional
if command -v luau-analyze >/dev/null 2>&1; then
  echo 'INFO: running luau-analyze (executor globals may show as unknown-global warnings)'
  luau-analyze "$FILE" || echo 'WARN: luau-analyze reported issues; review them manually'
else
  echo 'INFO: luau-analyze not installed; structural checks only.'
fi
echo 'Static Check: PASS'
