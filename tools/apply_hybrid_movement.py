#!/usr/bin/env python3
"""Apply hybrid movement: near=WalkSpeed 60-80 + Move, far=soft glide."""
from pathlib import Path
import re
import sys

path = Path("main.lua")
text = path.read_text(encoding="utf-8")
if "MONSTER_WALK_SPEED_MIN" in text and "monsterEnsureWalkSpeed" in text:
    print("already hybrid movement")
    sys.exit(0)

new_consts = """    -- HYBRID MOVEMENT (anti-kick):
    --   near  (<= MONSTER_WALK_NEAR): Humanoid WalkSpeed 60-80 + Move()
    --   far   (>  MONSTER_WALK_NEAR): soft glide + hop clamp + ground stick
    --   aerial/dodge: glide only
    local MONSTER_WALK_SPEED_MIN = 60
    local MONSTER_WALK_SPEED_MAX = 80
    local MONSTER_WALK_NEAR = 28           -- studs horizontal: use walk mode
    local MONSTER_GLIDE_SPEED = math.random(90, 110) -- studs/sec when far
    local MONSTER_WARP_MAX_HOP = 36         -- max single hop (keep under ~40)
    local MONSTER_MOVE_COOLDOWN = 0.03      -- min seconds between position writes (glide)
    local MONSTER_HORIZONTAL_LERP = 0.18
    local MONSTER_VERTICAL_LERP = 0.26
    local MONSTER_GROUND_STICK = true
    local MONSTER_GROUND_RAY = 14
    local MONSTER_GROUND_OFFSET = 2.2
    local monsterLastMoveAt = 0
    local monsterSavedWalkSpeed = nil
    local monsterSpeedCharacter = nil
    local monsterAppliedWalkSpeed = nil
    local monsterMoveMode = "GLIDE"        -- "WALK" | "GLIDE"
"""

const_pat = re.compile(
    r"    -- SAFE MOVEMENT \(anti-kick\): soft glide \+ hop clamp \+ optional ground stick\n"
    r"    local MONSTER_GLIDE_SPEED = math\.random\(100, 120\).*\n"
    r"    local MONSTER_WARP_MAX_HOP = 36.*\n"
    r"    local MONSTER_MOVE_COOLDOWN = 0\.03.*\n"
    r"    local MONSTER_HORIZONTAL_LERP = 0\.18.*\n"
    r"    local MONSTER_VERTICAL_LERP = 0\.26\n"
    r"    local MONSTER_GROUND_STICK = true.*\n"
    r"    local MONSTER_GROUND_RAY = 14\n"
    r"    local MONSTER_GROUND_OFFSET = 2\.2\n"
    r"    local monsterLastMoveAt = 0\n"
    r"    local monsterSavedWalkSpeed = nil\n"
    r"    local monsterSpeedCharacter = nil\n"
    r"    local monsterAppliedWalkSpeed = nil\n",
)
if not const_pat.search(text):
    print("ERROR: movement consts not found", file=sys.stderr)
    sys.exit(1)
text = const_pat.sub(new_consts + "\n", text, count=1)

start = text.find("    local function monsterSoftApply(myRoot, desiredCF, character, targetModel, dt, aerial)")
if start < 0:
    print("ERROR: monsterSoftApply not found", file=sys.stderr)
    sys.exit(1)
end = text.find("    function MonsterMove:SetState", start)
if end < 0:
    print("ERROR: MonsterMove:SetState not found", file=sys.stderr)
    sys.exit(1)

new_soft = """    local function monsterEnsureWalkSpeed(character)
      if not character then return nil end
      local hum = character:FindFirstChildOfClass("Humanoid")
      if not hum then return nil end
      if monsterSpeedCharacter ~= character or monsterSavedWalkSpeed == nil then
         monsterSavedWalkSpeed = hum.WalkSpeed
         monsterSpeedCharacter = character
      end
      local targetSpeed = math.random(MONSTER_WALK_SPEED_MIN, MONSTER_WALK_SPEED_MAX)
      if monsterAppliedWalkSpeed ~= targetSpeed or hum.WalkSpeed ~= targetSpeed then
         pcall(function()
            ResourceManager:RecordWrite("MonsterWarp", "WalkSpeed")
            hum.WalkSpeed = targetSpeed
         end)
         monsterAppliedWalkSpeed = targetSpeed
      end
      return hum
    end
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

      -- NEAR: hybrid walk (WalkSpeed 60-80)
      if (not aerial) and horizDist <= MONSTER_WALK_NEAR and distance > 0.35 then
         local hum = monsterEnsureWalkSpeed(character)
         if hum then
            local dir = horizDist > 0.05 and horiz.Unit or Vector3.zero
            pcall(function()
               hum:Move(dir, false)
            end)
            if horizDist > 0.4 then
               local face = from + Vector3.new(delta.X, 0, delta.Z)
               if (face - from).Magnitude > 0.08 then
                  local faceCF = CFrame.lookAt(from, Vector3.new(face.X, from.Y, face.Z))
                  local flatLook = Vector3.new(current.LookVector.X, 0, current.LookVector.Z)
                  local wantLook = Vector3.new(faceCF.LookVector.X, 0, faceCF.LookVector.Z)
                  if flatLook.Magnitude > 0.05 and wantLook.Magnitude > 0.05 then
                     if flatLook.Unit:Dot(wantLook.Unit) < 0.92 then
                        if now - monsterLastMoveAt >= MONSTER_MOVE_COOLDOWN then
                           ResourceManager:RecordWrite("MonsterWarp", "Position")
                           myRoot.CFrame = CFrame.new(from) * (faceCF - faceCF.Position)
                           monsterLastMoveAt = now
                        end
                     end
                  end
               end
            end
            monsterMoveMode = "WALK"
            return true, distance
         end
      end

      if monsterMoveMode == "WALK" then
         local hum = character and character:FindFirstChildOfClass("Humanoid")
         if hum then pcall(function() hum:Move(Vector3.zero, false) end) end
         monsterMoveMode = "GLIDE"
      end

      if now - monsterLastMoveAt < MONSTER_MOVE_COOLDOWN then
         return false, "cooldown"
      end

      -- FAR / AERIAL: soft glide + hop clamp
      local maxStep = MONSTER_GLIDE_SPEED * dt
      if distance > maxStep and distance > 1e-4 then
         desiredPos = from + delta.Unit * maxStep
         delta = desiredPos - from
         distance = maxStep
      end
      if distance > MONSTER_WARP_MAX_HOP and distance > 1e-4 then
         desiredPos = from + delta.Unit * MONSTER_WARP_MAX_HOP
         distance = MONSTER_WARP_MAX_HOP
      end
      if (not aerial) and MONSTER_GROUND_STICK then
         local gy = monsterGroundY(desiredPos, { character, targetModel })
         if math.abs(gy - desiredPos.Y) < 18 then
            desiredPos = Vector3.new(desiredPos.X, gy, desiredPos.Z)
         end
      end
      local farFactor = math.clamp(distance / 28, 0, 1)
      local alphaH = math.clamp(MONSTER_HORIZONTAL_LERP + farFactor * 0.18, 0.12, 0.58)
      local alphaV = aerial
         and math.clamp(MONSTER_VERTICAL_LERP + 0.18, 0.18, 0.72)
         or math.clamp(MONSTER_VERTICAL_LERP + farFactor * 0.08, 0.10, 0.55)
      local blended = Vector3.new(
         from.X + (desiredPos.X - from.X) * alphaH,
         from.Y + (desiredPos.Y - from.Y) * alphaV,
         from.Z + (desiredPos.Z - from.Z) * alphaH
      )
      local look = desiredCF.LookVector
      local facePoint = blended + Vector3.new(look.X, 0, look.Z)
      if (facePoint - blended).Magnitude < 0.05 then
         facePoint = blended + Vector3.new(delta.X, 0, delta.Z)
      end
      local newCF
      if (Vector3.new(facePoint.X, blended.Y, facePoint.Z) - blended).Magnitude > 0.08 then
         newCF = CFrame.lookAt(blended, Vector3.new(facePoint.X, blended.Y, facePoint.Z))
      else
         newCF = CFrame.new(blended) * (current - current.Position)
      end
      ResourceManager:RecordWrite("MonsterWarp", "Velocity")
      if aerial then
         local v = myRoot.AssemblyLinearVelocity
         myRoot.AssemblyLinearVelocity = Vector3.new(0, math.max(v.Y, 0) * 0.35, 0)
      else
         myRoot.AssemblyLinearVelocity = Vector3.zero
      end
      myRoot.AssemblyAngularVelocity = Vector3.zero
      ResourceManager:RecordWrite("MonsterWarp", "Position")
      myRoot.CFrame = newCF
      monsterLastMoveAt = now
      monsterMoveMode = "GLIDE"
      return true, distance
    end
"""
text = text[:start] + new_soft + text[end:]

old_stop = """        local speedCharacter = monsterSpeedCharacter
        local speedHumanoid = speedCharacter and speedCharacter:FindFirstChildOfClass("Humanoid")
        if speedHumanoid and monsterSavedWalkSpeed ~= nil then
            pcall(function() speedHumanoid.WalkSpeed = monsterSavedWalkSpeed end)
        end
        monsterSavedWalkSpeed = nil
        monsterSpeedCharacter = nil
        monsterAppliedWalkSpeed = nil"""

new_stop = """        local speedCharacter = monsterSpeedCharacter
        local speedHumanoid = speedCharacter and speedCharacter:FindFirstChildOfClass("Humanoid")
        if speedHumanoid then
            pcall(function() speedHumanoid:Move(Vector3.zero, false) end)
            if monsterSavedWalkSpeed ~= nil then
                pcall(function() speedHumanoid.WalkSpeed = monsterSavedWalkSpeed end)
            end
        end
        monsterSavedWalkSpeed = nil
        monsterSpeedCharacter = nil
        monsterAppliedWalkSpeed = nil
        monsterMoveMode = "GLIDE" """

if old_stop not in text:
    print("ERROR: stop WalkSpeed block not found", file=sys.stderr)
    sys.exit(1)
text = text.replace(old_stop, new_stop, 1)

path.write_text(text, encoding="utf-8")
print("OK hybrid movement", len(text))
assert "MONSTER_WALK_SPEED_MIN" in text
assert "monsterEnsureWalkSpeed" in text
assert "hum:Move(dir, false)" in text
