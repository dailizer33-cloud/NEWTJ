#!/usr/bin/env python3
"""Replace hybrid movement with full virtual joystick (WalkSpeed 80)
and warp-collect for orb/acorn/buff/event. Removes old walk-control paths.
"""
from pathlib import Path
import re
import sys

path = Path("main.lua")
text = path.read_text(encoding="utf-8")

if "VIRTUAL JOYSTICK MOVEMENT" in text and "farmWarpCollectLoot" in text:
    print("already virtual joystick + warp collect")
    sys.exit(0)

# ---- 1) Replace movement constants (hybrid or any prior SAFE block) ----
const_pat = re.compile(
    r"    -- (?:HYBRID MOVEMENT|SAFE MOVEMENT).*?\n"
    r"(?:    --.*\n)*"
    r"    local MONSTER_WALK_SPEED_MIN = 60\n"
    r"    local MONSTER_WALK_SPEED_MAX = 80\n"
    r"    local MONSTER_WALK_NEAR = 28.*\n"
    r"    local MONSTER_GLIDE_SPEED = math\.random\(90, 110\).*\n"
    r"    local MONSTER_WARP_MAX_HOP = 36.*\n"
    r"    local MONSTER_MOVE_COOLDOWN = 0\.03.*\n"
    r"    local MONSTER_HORIZONTAL_LERP = 0\.18\n"
    r"    local MONSTER_VERTICAL_LERP = 0\.26\n"
    r"    local MONSTER_GROUND_STICK = true\n"
    r"    local MONSTER_GROUND_RAY = 14\n"
    r"    local MONSTER_GROUND_OFFSET = 2\.2\n"
    r"    local monsterLastMoveAt = 0\n"
    r"    local monsterSavedWalkSpeed = nil\n"
    r"    local monsterSpeedCharacter = nil\n"
    r"    local monsterAppliedWalkSpeed = nil\n"
    r"    local monsterMoveMode = \"GLIDE\".*\n",
)

new_consts = """    -- VIRTUAL JOYSTICK MOVEMENT (full):
    --   WalkSpeed fixed 80 + Humanoid:Move (no hybrid walk/glide blend)
    --   Soft hop only when very far or dodging (anti-kick hop clamp)
    --   Loot: warp-collect orb / acorn / buff / event (separate path)
    local MONSTER_WALK_SPEED = 80          -- fixed
    local MONSTER_WARP_MAX_HOP = 36         -- max single hop (keep under ~40)
    local MONSTER_MOVE_COOLDOWN = 0.03
    local MONSTER_FAR_HOP = 55             -- use hop when farther than this
    local MONSTER_GROUND_STICK = true
    local MONSTER_GROUND_RAY = 14
    local MONSTER_GROUND_OFFSET = 2.2
    local monsterLastMoveAt = 0
    local monsterSavedWalkSpeed = nil
    local monsterSpeedCharacter = nil
    local monsterAppliedWalkSpeed = nil
"""

const_pat2 = re.compile(
    r"    -- HYBRID MOVEMENT \(anti-kick\):\n"
    r"    --   near.*\n"
    r"    --   far.*\n"
    r"    --   aerial.*\n"
    r"    local MONSTER_WALK_SPEED_MIN = 60\n"
    r"    local MONSTER_WALK_SPEED_MAX = 80\n"
    r"    local MONSTER_WALK_NEAR = 28.*\n"
    r"    local MONSTER_GLIDE_SPEED = math\.random\(90, 110\).*\n"
    r"    local MONSTER_WARP_MAX_HOP = 36.*\n"
    r"    local MONSTER_MOVE_COOLDOWN = 0\.03.*\n"
    r"    local MONSTER_HORIZONTAL_LERP = 0\.18\n"
    r"    local MONSTER_VERTICAL_LERP = 0\.26\n"
    r"    local MONSTER_GROUND_STICK = true\n"
    r"    local MONSTER_GROUND_RAY = 14\n"
    r"    local MONSTER_GROUND_OFFSET = 2\.2\n"
    r"    local monsterLastMoveAt = 0\n"
    r"    local monsterSavedWalkSpeed = nil\n"
    r"    local monsterSpeedCharacter = nil\n"
    r"    local monsterAppliedWalkSpeed = nil\n"
    r"    local monsterMoveMode = \"GLIDE\".*\n",
)
if const_pat.search(text):
    text = const_pat.sub(new_consts + "\n", text, count=1)
    print("replaced movement consts")
elif const_pat2.search(text):
    text = const_pat2.sub(new_consts + "\n", text, count=1)
    print("replaced hybrid consts")
else:
    print("ERROR: movement consts not found", file=sys.stderr)
    sys.exit(1)

# ---- 2) Replace monsterEnsureWalkSpeed + monsterSoftApply ----
start = text.find("    local function monsterEnsureWalkSpeed(character)")
if start < 0:
    start = text.find("    local function monsterSoftApply(myRoot, desiredCF, character, targetModel, dt, aerial)")
if start < 0:
    print("ERROR: soft apply not found", file=sys.stderr)
    sys.exit(1)
end = text.find("    function MonsterMove:SetState", start)
if end < 0:
    print("ERROR: MonsterMove:SetState not found", file=sys.stderr)
    sys.exit(1)

new_soft = r'''    local function monsterEnsureWalkSpeed(character)
      if not character then return nil end
      local hum = character:FindFirstChildOfClass("Humanoid")
      if not hum then return nil end
      if monsterSpeedCharacter ~= character or monsterSavedWalkSpeed == nil then
         monsterSavedWalkSpeed = hum.WalkSpeed
         monsterSpeedCharacter = character
      end
      if monsterAppliedWalkSpeed ~= MONSTER_WALK_SPEED or hum.WalkSpeed ~= MONSTER_WALK_SPEED then
         pcall(function()
            ResourceManager:RecordWrite("MonsterWarp", "WalkSpeed")
            hum.WalkSpeed = MONSTER_WALK_SPEED
         end)
         monsterAppliedWalkSpeed = MONSTER_WALK_SPEED
      end
      return hum
    end
    -- Full virtual joystick: WalkSpeed 80 + Move(). Soft hop only if far/dodge.
    local function monsterSoftApply(myRoot, desiredCF, character, targetModel, dt, aerial)
      local now = os.clock()
      dt = tonumber(dt) or 0.016
      if dt <= 0 then dt = 0.016 end
      if dt > 0.1 then dt = 0.1 end
      local current = myRoot.CFrame
      local from = current.Position
      local desiredPos = desiredCF.Position
      local delta = desiredPos - from
      local distance = delta.Magnitude
      local horiz = Vector3.new(delta.X, 0, delta.Z)
      local horizDist = horiz.Magnitude
      local hum = monsterEnsureWalkSpeed(character)

      -- DODGE / aerial: short vertical hop only
      if aerial then
         if now - monsterLastMoveAt < MONSTER_MOVE_COOLDOWN then
            return false, "cooldown"
         end
         local hop = math.min(distance, MONSTER_WARP_MAX_HOP)
         if hop > 0.05 and delta.Magnitude > 1e-4 then
            local dest = from + delta.Unit * hop
            ResourceManager:RecordWrite("MonsterWarp", "Velocity")
            local v = myRoot.AssemblyLinearVelocity
            myRoot.AssemblyLinearVelocity = Vector3.new(0, math.max(v.Y, 0) * 0.35, 0)
            myRoot.AssemblyAngularVelocity = Vector3.zero
            ResourceManager:RecordWrite("MonsterWarp", "Position")
            myRoot.CFrame = CFrame.new(dest) * (current - current.Position)
            monsterLastMoveAt = now
         end
         if hum then pcall(function() hum:Move(Vector3.zero, false) end) end
         return true, distance
      end

      -- FAR: soft hop toward target (not walk-blend / not glide lerp)
      if horizDist > MONSTER_FAR_HOP then
         if now - monsterLastMoveAt < MONSTER_MOVE_COOLDOWN then
            return false, "cooldown"
         end
         local hop = math.min(horizDist, MONSTER_WARP_MAX_HOP)
         local step = horiz.Unit * hop
         local dest = from + step
         if MONSTER_GROUND_STICK then
            local gy = monsterGroundY(dest, { character, targetModel })
            if math.abs(gy - dest.Y) < 18 then
               dest = Vector3.new(dest.X, gy, dest.Z)
            end
         end
         local face = dest + horiz.Unit
         ResourceManager:RecordWrite("MonsterWarp", "Velocity")
         myRoot.AssemblyLinearVelocity = Vector3.zero
         myRoot.AssemblyAngularVelocity = Vector3.zero
         ResourceManager:RecordWrite("MonsterWarp", "Position")
         myRoot.CFrame = CFrame.lookAt(dest, Vector3.new(face.X, dest.Y, face.Z))
         monsterLastMoveAt = now
         if hum then pcall(function() hum:Move(Vector3.zero, false) end) end
         return true, distance
      end

      -- VIRTUAL JOYSTICK (full): fixed WalkSpeed 80 + Move
      if hum then
         local dir = horizDist > 0.08 and horiz.Unit or Vector3.zero
         pcall(function()
            hum:Move(dir, false)
         end)
         -- face target lightly (rotation only, no position write)
         if horizDist > 0.5 then
            local face = from + horiz
            if (face - from).Magnitude > 0.08 then
               local flatLook = Vector3.new(current.LookVector.X, 0, current.LookVector.Z)
               local want = horiz.Unit
               if flatLook.Magnitude > 0.05 then
                  if flatLook.Unit:Dot(want) < 0.90 then
                     if now - monsterLastMoveAt >= MONSTER_MOVE_COOLDOWN then
                        ResourceManager:RecordWrite("MonsterWarp", "Position")
                        myRoot.CFrame = CFrame.lookAt(from, Vector3.new(face.X, from.Y, face.Z))
                        monsterLastMoveAt = now
                     end
                  end
               end
            end
         end
         return true, distance
      end

      return false, "no-humanoid"
    end
'''
text = text[:start] + new_soft + text[end:]
print("replaced soft apply with virtual joystick")

# ---- 3) Replace farmCollectNearbyOrbs with warp collect ----
collect_pat = re.compile(
    r"    local farmOrbTouchAt = 0\n"
    r"    local function farmCollectNearbyOrbs\(\).*?"
    r"        if count > 0 then farmOrbTouchAt = now end\n"
    r"    end\n",
    re.DOTALL,
)

new_collect = r'''    local farmOrbTouchAt = 0
    local FARM_LOOT_KEYWORDS = {
        "orb", "acorn", "buff", "event", "power", "xp", "energy", "glow",
        "capsule", "pickup", "token", "shard", "fruit", "apple", "nut",
        "boost", "gift", "chest", "drop", "reward", "crystal", "gem",
    }
    local function farmIsLootName(name)
        local n = string.lower(tostring(name or ""))
        for _, key in ipairs(FARM_LOOT_KEYWORDS) do
            if string.find(n, key, 1, true) then return true end
        end
        return false
    end
    -- Warp-collect: hop to nearby orb/acorn/buff/event then touch
    local function farmWarpCollectLoot()
        local character = LocalPlayer.Character
        if not character then return end
        local root = character:FindFirstChild("HumanoidRootPart") or character.PrimaryPart
        if not root then return end
        local now = os.clock()
        if farmOrbTouchAt > 0 and now - farmOrbTouchAt < 0.28 then return end
        local best, bestDist = nil, 90
        for _, obj in ipairs(workspace:GetDescendants()) do
            if obj:IsA("BasePart") and obj.Parent and obj.Parent ~= character then
                local label = obj.Name .. " " .. (obj.Parent and obj.Parent.Name or "")
                if farmIsLootName(label) then
                    local d = (obj.Position - root.Position).Magnitude
                    if d < bestDist and d > 0.5 then
                        best, bestDist = obj, d
                    end
                end
            end
        end
        if not best then return end
        -- soft hop toward loot (anti-kick clamp)
        local from = root.Position
        local delta = best.Position - from
        local hop = math.min(delta.Magnitude, MONSTER_WARP_MAX_HOP)
        if hop > 1.2 and delta.Magnitude > 1e-4 then
            local dest = from + delta.Unit * hop
            if MONSTER_GROUND_STICK then
                local gy = monsterGroundY(dest, { character })
                if math.abs(gy - dest.Y) < 18 then
                    dest = Vector3.new(dest.X, gy, dest.Z)
                end
            end
            pcall(function()
                ResourceManager:RecordWrite("MonsterWarp", "Position")
                root.AssemblyLinearVelocity = Vector3.zero
                root.CFrame = CFrame.new(dest, dest + Vector3.new(delta.X, 0, delta.Z))
            end)
            monsterLastMoveAt = now
        end
        -- touch / firetouch when close enough
        if (best.Position - root.Position).Magnitude <= 14 then
            pcall(function()
                if firetouchinterest then
                    firetouchinterest(root, best, 0)
                    firetouchinterest(root, best, 1)
                end
            end)
            local oid = best:GetAttribute("Id") or best:GetAttribute("OrbId")
                or (best.Parent and (best.Parent:GetAttribute("Id") or best.Parent:GetAttribute("OrbId")))
            if type(oid) == "number" then
                pcall(function()
                    local folder = ReplicatedStorage:FindFirstChild("AntRemotes")
                    local col = folder and folder:FindFirstChild("Collect")
                    if col then col:FireServer({ oid }) end
                end)
            end
        end
        farmOrbTouchAt = now
    end
'''

if not collect_pat.search(text):
    print("ERROR: farmCollectNearbyOrbs not found", file=sys.stderr)
    sys.exit(1)
text = collect_pat.sub(new_collect, text, count=1)
print("replaced collect with warp-collect")

if "farmCollectNearbyOrbs()" in text:
    text = text.replace("farmCollectNearbyOrbs()", "farmWarpCollectLoot()")
    print("updated collect call sites")

path.write_text(text, encoding="utf-8")
print("OK virtual joystick + warp collect", len(text))
assert "VIRTUAL JOYSTICK MOVEMENT" in text
assert "MONSTER_WALK_SPEED = 80" in text
assert "farmWarpCollectLoot" in text
assert "monsterEnsureWalkSpeed" in text
assert "MONSTER_WALK_SPEED_MIN" not in text
assert "MONSTER_WALK_NEAR" not in text
assert "farmCollectNearbyOrbs" not in text
