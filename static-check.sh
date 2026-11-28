#!/usr/bin/env bash
# NEWTJ - structural checks (Phase 16 + 17 + 18.4 + 19.0).
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

warp_guard="$(sed -n '/function TargetService:Unlock(reason, expectedSource)/,/function TargetService:Reset(reason)/p' "$FILE")"
has "$warp_guard" 'reasonText == "warp_mode" and currentSource ~= "deathnote"' \
  || fail 'WARP activation must release a Death Note-owned target'
has "$warp_guard" 'reasonText == "warp_off" or reasonText == "movement_owner_switch"' \
  || fail 'WARP-owned target release guards missing'
warp_toggle="$(sed -n '/local function claimPlayerMovement()/,/-- WALK:/p' "$FILE")"
has "$warp_toggle" 'TargetService.Source == "deathnote"' \
  || fail 'WARP activation no longer checks Death Note target ownership'
has "$warp_toggle" 'TargetService:Unlock("warp_mode")' \
  || fail 'WARP activation target release call missing'
pass 'WARP activation releases only a Death Note-owned target; WARP shutdown guards remain separate'


grep -qF 'TargetService:Reset("STARTUP_RESET")' "$FILE" \
  || fail 'startup persistent-target reset missing'
stopall="$(sed -n '/_G.TAYJAY_STOP_ALL = function()/,/print("\[TAYJAY\] STOP ALL completed/p' "$FILE")"
reset_line="$(line_of "$stopall" 'TargetService:Reset("STOP_ALL")')"
owners_line="$(line_of "$stopall" 'ResourceManager:StopAllOwners("STOP_ALL")')"
[ -n "$reset_line" ] && [ -n "$owners_line" ] && [ "$reset_line" -lt "$owners_line" ] \
  || fail 'STOP ALL must reset TargetService before global Owner shutdown'
pass 'startup and STOP ALL clear persistent TargetService state before Owner shutdown'

# ---------------------------------------------------------------- Phase 19.0: movement queue and safe-ground regression guards.
grep -qF 'function _tjMovementController:Enqueue(owner, key, startFn)' "$FILE" \
  || fail 'movement queue Enqueue missing'
grep -qF 'function _tjMovementController:DrainQueue()' "$FILE" \
  || fail 'movement queue DrainQueue missing'
grep -qF 'function _tjMovementController:CancelQueued(owner, key)' "$FILE" \
  || fail 'movement queue cancellation missing'
grep -qF '_tjMovementController:Enqueue("PLAYER_WARP", "WARP"' "$FILE" \
  || fail 'WARP does not enqueue transient movement requests'
grep -qF '_tjMovementController:Enqueue("MONSTER", "MONSTER"' "$FILE" \
  || fail 'Monster Warp does not enqueue transient movement requests'
grep -qF 'self.QueueGeneration = self.QueueGeneration + 1' "$FILE" \
  || fail 'movement queue generation is not invalidated on ForceClear'
grep -qF '_tjMovementController.QueueGeneration = (tonumber(_tjMovementController.QueueGeneration) or 0) + 1' "$FILE" \
  || fail 'startup does not invalidate retained movement callbacks'
grep -qF 'table.clear(_tjMovementController.Queue)' "$FILE" \
  || fail 'startup does not clear retained movement requests'
grep -qF '_tjMovementController.ActiveQueueItem.cancelled = true' "$FILE" \
  || fail 'startup does not cancel a retained active movement request'
grep -qF '_tjMovementController.PendingPlayerWarp = false' "$FILE" \
  || fail 'WARP pending indicator is not stored/reset on MovementController'
if grep -qF 'local warpQueuePending' "$FILE"; then fail 'WARP pending indicator adds a main-chunk local'; fi
queue_drain="$(sed -n '/function _tjMovementController:DrainQueue()/,/function _tjMovementController:Enqueue/p' "$FILE")"
[ -n "$queue_drain" ] || fail 'movement queue drain section not found'
has "$queue_drain" 'if _G.TAYJAY_STOPPED or self.QueueBusy' || fail 'queue drain does not refuse work after STOP ALL'
has "$queue_drain" 'self.QueueBusy = true' || fail 'queue drain does not reserve a single active starter'
has "$queue_drain" 'local generation = self.QueueGeneration' || fail 'queue drain generation snapshot missing'
has "$queue_drain" 'if generation ~= self.QueueGeneration or _G.TAYJAY_STOPPED then' \
  || fail 'queue drain does not abort after reset / STOP ALL'
has "$queue_drain" 'if #self.Queue > 0 and self.PlatformOwner == "PLAYER_WARP"' \
  || fail 'idle WARP platform cleanup before queue drain missing'
has "$queue_drain" 'if #self.Queue > 0 and self.PlatformOwner == "MONSTER"' \
  || fail 'idle Monster platform cleanup before queue drain missing'
pass 'WARP and Monster Warp use one cancellable FIFO queue with stale-platform and reentrancy guards'

grep -qF 'local function findWarpGround(position, ignoreList)' "$FILE" \
  || fail 'WARP walkable-ground raycast missing'
grep -qF 'hit and hit:IsA("Terrain")' "$FILE" \
  || fail 'safe-ground raycast does not accept Terrain surfaces'
grep -qF 'local function safeWarpCFrame(desired, ignoreList)' "$FILE" \
  || fail 'safe WARP destination guard missing'
grep -qF 'if not ground then' "$FILE" \
  || fail 'safe-ground rejection branch missing'
grep -qF 'if not gy then return false, "no-safe-ground" end' "$FILE" \
  || fail 'Monster far-hop must reject missing ground'
grep -qF 'local monsterGroundY' "$FILE" \
  || fail 'Monster ground finder forward declaration missing'
pass 'WARP and Monster Warp reject destinations without walkable ground'

# ---------------------------------------------------------------- optional
if command -v luau-analyze >/dev/null 2>&1; then
  echo 'INFO: running luau-analyze (executor globals may show as unknown-global warnings)'
  luau-analyze "$FILE" || echo 'WARN: luau-analyze reported issues; review them manually'
else
  echo 'INFO: luau-analyze not installed; structural checks only.'
fi
echo 'Static Check: PASS'
