#!/usr/bin/env python3
"""Optimize virtual joystick input: cache hum, smooth dir, deadzone, less spam."""
from pathlib import Path
import re
import sys

path = Path("main.lua")
text = path.read_text(encoding="utf-8")

if "VJOY_OPT" in text and "monsterVjoyDirSmoothed" in text:
    print("already optimized virtual joystick")
    sys.exit(0)

if "VIRTUAL JOYSTICK MOVEMENT" not in text:
    print("ERROR: virtual joystick block not found", file=sys.stderr)
    sys.exit(1)

old_consts_tail = """    local MONSTER_WALK_SPEED = 80          -- fixed
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

new_consts_tail = """    local MONSTER_WALK_SPEED = 80          -- fixed
    local MONSTER_WARP_MAX_HOP = 36         -- max single hop (keep under ~40)
    local MONSTER_MOVE_COOLDOWN = 0.03
    local MONSTER_FAR_HOP = 55             -- use hop when farther than this
    local MONSTER_GROUND_STICK = true
    local MONSTER_GROUND_RAY = 14
    local MONSTER_GROUND_OFFSET = 2.2
    -- VJOY_OPT: input tuning
    local MONSTER_VJOY_DEADZONE = 0.12      -- ignore tiny direction noise
    local MONSTER_VJOY_SMOOTH = 0.28        -- 0=snappy 1=very smooth (lerp alpha)
    local MONSTER_VJOY_MOVE_EPS = 0.04      -- only re-send Move if dir changed
    local MONSTER_VJOY_FACE_DOT = 0.88      -- re-face when look drifts below this
    local MONSTER_VJOY_FACE_CD = 0.12       -- min seconds between face writes
    local monsterLastMoveAt = 0
    local monsterLastFaceAt = 0
    local monsterSavedWalkSpeed = nil
    local monsterSpeedCharacter = nil
    local monsterAppliedWalkSpeed = nil
    local monsterCachedHum = nil
    local monsterVjoyDirSmoothed = Vector3.zero
    local monsterVjoyLastSent = Vector3.zero
"""

if old_consts_tail not in text:
    print("ERROR: const tail not found", file=sys.stderr)
    sys.exit(1)
text = text.replace(old_consts_tail, new_consts_tail, 1)

start = text.find("    local function monsterEnsureWalkSpeed(character)")
if start < 0:
    print("ERROR: monsterEnsureWalkSpeed not found", file=sys.stderr)
    sys.exit(1)
end = text.find("    function MonsterMove:SetState", start)
if end < 0:
    print("ERROR: SetState not found", file=sys.stderr)
    sys.exit(1)

new_body = r'''    local function monsterEnsureWalkSpeed(character)
      if not character then
         monsterCachedHum = nil
         return nil
      end
      if monsterSpeedCharacter == character and monsterCachedHum and monsterCachedHum.Parent then
         local hum = monsterCachedHum
         if monsterAppliedWalkSpeed ~= MONSTER_WALK_SPEED or hum.WalkSpeed ~= MONSTER_WALK_SPEED then
            pcall(function()
               ResourceManager:RecordWrite("MonsterWarp", "WalkSpeed")
               hum.WalkSpeed = MONSTER_WALK_SPEED
            end)
            monsterAppliedWalkSpeed = MONSTER_WALK_SPEED
         end
         return hum
      end
      local hum = character:FindFirstChildOfClass("Humanoid")
      if not hum then
         monsterCachedHum = nil
         return nil
      end
      if monsterSpeedCharacter ~= character or monsterSavedWalkSpeed == nil then
         monsterSavedWalkSpeed = hum.WalkSpeed
         monsterSpeedCharacter = character
      end
      monsterCachedHum = hum
      pcall(function()
         hum.AutoRotate = true
      end)
      if monsterAppliedWalkSpeed ~= MONSTER_WALK_SPEED or hum.WalkSpeed ~= MONSTER_WALK_SPEED then
         pcall(function()
            ResourceManager:RecordWrite("MonsterWarp", "WalkSpeed")
            hum.WalkSpeed = MONSTER_WALK_SPEED
         end)
         monsterAppliedWalkSpeed = MONSTER_WALK_SPEED
      end
      return hum
    end
    local function monsterSoftApply(myRoot, desiredCF, character, targetModel, dt, aerial)
      local now = os.clock()
      dt = tonumber(dt) or 0.016
      if dt <= 0 then dt = 0.016 elseif dt > 0.1 then dt = 0.1 end
      local current = myRoot.CFrame
      local from = current.Position
      local desiredPos = desiredCF.Position
      local delta = desiredPos - from
      local distance = delta.Magnitude
      local horiz = Vector3.new(delta.X, 0, delta.Z)
      local horizDist = horiz.Magnitude
      local hum = monsterEnsureWalkSpeed(character)

      if aerial then
         if now - monsterLastMoveAt < MONSTER_MOVE_COOLDOWN then
            return false, "cooldown"
         end
         monsterVjoyDirSmoothed = Vector3.zero
         monsterVjoyLastSent = Vector3.zero
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

      if horizDist > MONSTER_FAR_HOP then
         if now - monsterLastMoveAt < MONSTER_MOVE_COOLDOWN then
            return false, "cooldown"
         end
         monsterVjoyDirSmoothed = Vector3.zero
         monsterVjoyLastSent = Vector3.zero
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

      if not hum then
         return false, "no-humanoid"
      end

      local raw = Vector3.zero
      if horizDist > MONSTER_VJOY_DEADZONE then
         raw = horiz.Unit
         if horizDist < 4 then
            local t = math.clamp((horizDist - MONSTER_VJOY_DEADZONE) / (4 - MONSTER_VJOY_DEADZONE), 0, 1)
            raw = raw * t
         end
      end

      local a = 1 - math.exp(-math.max(MONSTER_VJOY_SMOOTH, 0.05) * 60 * dt)
      a = math.clamp(a, 0.08, 0.85)
      monsterVjoyDirSmoothed = monsterVjoyDirSmoothed:Lerp(raw, a)
      if monsterVjoyDirSmoothed.Magnitude < MONSTER_VJOY_DEADZONE * 0.5 then
         monsterVjoyDirSmoothed = Vector3.zero
      end

      local sent = monsterVjoyLastSent
      local diff = (monsterVjoyDirSmoothed - sent).Magnitude
      if diff >= MONSTER_VJOY_MOVE_EPS or (monsterVjoyDirSmoothed.Magnitude < 1e-4 and sent.Magnitude > 1e-4) then
         local dir = monsterVjoyDirSmoothed
         if dir.Magnitude > 1 then dir = dir.Unit end
         pcall(function()
            hum:Move(dir, false)
         end)
         monsterVjoyLastSent = monsterVjoyDirSmoothed
      end

      if horizDist > 1.0 and now - monsterLastFaceAt >= MONSTER_VJOY_FACE_CD then
         local want = horiz.Unit
         local flatLook = Vector3.new(current.LookVector.X, 0, current.LookVector.Z)
         if flatLook.Magnitude > 0.05 then
            if flatLook.Unit:Dot(want) < MONSTER_VJOY_FACE_DOT then
               local face = from + want
               ResourceManager:RecordWrite("MonsterWarp", "Position")
               myRoot.CFrame = CFrame.lookAt(from, Vector3.new(face.X, from.Y, face.Z))
               monsterLastFaceAt = now
               monsterLastMoveAt = now
            end
         end
      end

      return true, distance
    end
'''
text = text[:start] + new_body + text[end:]

if "monsterMoveMode = \"GLIDE\"" in text:
    text = text.replace(
        """        monsterSavedWalkSpeed = nil
        monsterSpeedCharacter = nil
        monsterAppliedWalkSpeed = nil
        monsterMoveMode = \"GLIDE\" """,
        """        monsterSavedWalkSpeed = nil
        monsterSpeedCharacter = nil
        monsterAppliedWalkSpeed = nil
        monsterCachedHum = nil
        monsterVjoyDirSmoothed = Vector3.zero
        monsterVjoyLastSent = Vector3.zero """,
        1,
    )
else:
    old2 = """        monsterSavedWalkSpeed = nil
        monsterSpeedCharacter = nil
        monsterAppliedWalkSpeed = nil"""
    new2 = """        monsterSavedWalkSpeed = nil
        monsterSpeedCharacter = nil
        monsterAppliedWalkSpeed = nil
        monsterCachedHum = nil
        monsterVjoyDirSmoothed = Vector3.zero
        monsterVjoyLastSent = Vector3.zero"""
    if old2 in text:
        text = text.replace(old2, new2, 1)

path.write_text(text, encoding="utf-8")
print("OK vjoy optimized", len(text))
assert "VJOY_OPT" in text
assert "monsterVjoyDirSmoothed" in text
assert "MONSTER_VJOY_DEADZONE" in text
assert "monsterCachedHum" in text
