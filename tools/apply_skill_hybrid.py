#!/usr/bin/env python3
"""Apply SkillHybrid integration to main.lua (remove GUI tap combat)."""
from pathlib import Path
import re
import sys

path = Path("main.lua")
text = path.read_text(encoding="utf-8")
if "skillFireBite" in text and "Farm combat: SkillHybrid remotes" in text:
    print("already integrated")
    sys.exit(0)

marker = "    -- Farm-derived combat input: locate BITE and Q/E buttons in the same ScreenGui."
if marker not in text:
    print("ERROR: farm combat marker missing", file=sys.stderr)
    sys.exit(1)

INSERT = """
    -- =========================================================
    -- SKILL HYBRID (from spy logs 2026-11-25) - remote fire, not GUI tap
    -- =========================================================
    local SkillHybrid = { BiteCooldown = 0.62, MoveCooldown = 10.5, _lastBite = 0, _lastMove = 0, _remotes = nil }
    local function skillGetRemotes()
        if SkillHybrid._remotes then return SkillHybrid._remotes end
        local folder = ReplicatedStorage:FindFirstChild("AntRemotes")
        if not folder then
            local ok, f = pcall(function() return ReplicatedStorage:WaitForChild("AntRemotes", 3) end)
            if ok then folder = f end
        end
        if not folder then return nil end
        SkillHybrid._remotes = {
            Bite = folder:FindFirstChild("Bite"),
            Move = folder:FindFirstChild("Move"),
            Evolve = folder:FindFirstChild("Evolve"),
            Collect = folder:FindFirstChild("Collect"),
        }
        return SkillHybrid._remotes
    end
    local function skillAsNetworkId(value)
        if type(value) == "number" and value < 0 then return value end
        return nil
    end
    local function skillLookDirection()
        local char = LocalPlayer.Character
        local root = char and (char:FindFirstChild("HumanoidRootPart") or char.PrimaryPart)
        if not root then return Vector3.new(0, 0, -1) end
        local look = root.CFrame.LookVector
        local flat = Vector3.new(look.X, 0, look.Z)
        if flat.Magnitude < 0.05 then return Vector3.new(0, 0, -1) end
        return flat.Unit
    end
    local function skillDirectionTo(targetPos)
        local char = LocalPlayer.Character
        local root = char and (char:FindFirstChild("HumanoidRootPart") or char.PrimaryPart)
        if not root then return skillLookDirection() end
        local delta = targetPos - root.Position
        local flat = Vector3.new(delta.X, 0, delta.Z)
        if flat.Magnitude < 0.05 then return skillLookDirection() end
        return flat.Unit
    end
    local function skillFireBite(targetId)
        local rem = skillGetRemotes()
        if not rem or not rem.Bite then return false end
        local t = os.clock()
        if t - SkillHybrid._lastBite < SkillHybrid.BiteCooldown then return false end
        local ok = pcall(function()
            rem.Bite:FireServer(skillAsNetworkId(targetId))
        end)
        if ok then SkillHybrid._lastBite = t end
        return ok
    end
    local function skillFireMove(direction, targetId)
        local rem = skillGetRemotes()
        if not rem or not rem.Move then return false end
        local t = os.clock()
        if t - SkillHybrid._lastMove < SkillHybrid.MoveCooldown then return false end
        if typeof(direction) ~= "Vector3" or direction.Magnitude < 0.001 then
            direction = skillLookDirection()
        else
            direction = direction.Unit
        end
        local ok = pcall(function()
            rem.Move:FireServer(direction, skillAsNetworkId(targetId))
        end)
        if ok then SkillHybrid._lastMove = t end
        return ok
    end
    local function skillFireMoveAtTarget()
        local targetRoot = nil
        if monsterCurrent and monsterCurrent.root and monsterCurrent.root.Parent then
            targetRoot = monsterCurrent.root
        end
        if targetRoot then
            return skillFireMove(skillDirectionTo(targetRoot.Position), nil)
        end
        return skillFireMove(skillLookDirection(), nil)
    end
    pcall(function()
        local env = _G
        if type(getgenv) == "function" then
            local g = getgenv()
            if type(g) == "table" then env = g end
        end
        env.TAYJAY_SKILL_HYBRID = SkillHybrid
        if type(env.TJ) ~= "table" then env.TJ = {} end
        env.TJ.SkillHybrid = SkillHybrid
        SkillHybrid.FireBite = skillFireBite
        SkillHybrid.FireMove = skillFireMove
        SkillHybrid.FireMoveAtTarget = skillFireMoveAtTarget
    end)

"""

pattern = re.compile(
    r"    -- Farm-derived combat input: locate BITE and Q/E buttons in the same ScreenGui\.\n"
    r"    local function farmTapButton\(button\).*?"
    r"    task\.spawn\(function\(\)\n"
    r"        local nextBite,nextQ,nextE=0,0,0\n"
    r"        while screenGui\.Parent and not _G\.TAYJAY_STOPPED do\n"
    r"            if states\.MonsterWarp and monsterFilterMode==\"Monster\" then\n"
    r"                local now=os\.clock\(\)\n"
    r"                local bite,skills=farmFindCombatButtons\(\)\n"
    r"                if now>=nextBite and bite then farmTapButton\(bite\); nextBite=now\+0\.14 end\n"
    r"                if now>=nextQ and skills\[1\] then farmTapButton\(skills\[1\]\); nextQ=now\+7 end\n"
    r"                if now>=nextE and skills\[2\] then farmTapButton\(skills\[2\]\); nextE=now\+9 end\n"
    r"                farmCollectNearbyOrbs\(\)\n"
    r"            end\n"
    r"            task\.wait\(0\.05\)\n"
    r"        end\n"
    r"    end\)\n",
    re.DOTALL,
)

NEW_FARM = INSERT + r"""
    local farmOrbTouchAt = 0
    local function farmCollectNearbyOrbs()
        local character = LocalPlayer.Character
        if not character then return end
        local root = character:FindFirstChild("HumanoidRootPart") or character.PrimaryPart
        if not root then return end
        local now = os.clock()
        if farmOrbTouchAt > 0 and now - farmOrbTouchAt < 0.35 then return end
        local count = 0
        for _, obj in ipairs(workspace:GetDescendants()) do
            if count >= 8 then break end
            if obj:IsA("BasePart") and obj.Parent and obj.Parent ~= character then
                local n = string.lower(obj.Name .. " " .. (obj.Parent and obj.Parent.Name or ""))
                if (n:find("orb", 1, true) or n:find("power", 1, true) or n:find("xp", 1, true)
                    or n:find("energy", 1, true) or n:find("glow", 1, true))
                    and (obj.Position - root.Position).Magnitude <= 12 then
                    pcall(function()
                        if firetouchinterest then
                            firetouchinterest(root, obj, 0)
                            firetouchinterest(root, obj, 1)
                        end
                    end)
                    count = count + 1
                end
            end
        end
        if count > 0 then farmOrbTouchAt = now end
    end
    task.spawn(function()
        local nextBite, nextMove = 0, 0
        while screenGui.Parent and not _G.TAYJAY_STOPPED do
            if states.MonsterWarp and monsterFilterMode == "Monster" then
                local now = os.clock()
                if now >= nextBite then
                    if skillFireBite(nil) then nextBite = now + 0.62 else nextBite = now + 0.2 end
                end
                if now >= nextMove then
                    if skillFireMoveAtTarget() then nextMove = now + 10.5 else nextMove = now + 1 end
                end
                farmCollectNearbyOrbs()
            end
            task.wait(0.05)
        end
    end)
"""

if not pattern.search(text):
    print("ERROR: farm pattern not matched", file=sys.stderr)
    sys.exit(1)
text = pattern.sub(NEW_FARM, text, count=1)

old_bite = """    local function biteOnce()
        local now = os.clock()
        if (not biteButton or not biteButton.Parent) and now - lastFindAt > 1.5 then
            lastFindAt = now
            biteButton = findBiteButton()
            if biteButton then
                pcall(function() print("[TAYJAY RAPID] attack button found: " .. biteButton:GetFullName()) end)
            end
        end
        if not biteButton or not biteButton.Parent then lastMethod = "NO BUTTON" return false end
        if RAPID_METHOD ~= "signal" and clickScreen(biteButton) then lastMethod = "touch" return true end
        if RAPID_METHOD ~= "touch" and not signalBad then
            lastSignalFireAt = os.clock()
            if fireSignals(biteButton) then lastMethod = "signal" return true end
        end
        lastMethod = "NO INPUT"
        return false
    end"""

new_bite = """    local function biteOnce()
        local SH = rawget(_G, "TAYJAY_SKILL_HYBRID")
        if type(getgenv) == "function" then
            pcall(function()
                local g = getgenv()
                if type(g) == "table" and type(g.TAYJAY_SKILL_HYBRID) == "table" then
                    SH = g.TAYJAY_SKILL_HYBRID
                end
            end)
        end
        if type(SH) == "table" and type(SH.FireBite) == "function" then
            if SH.FireBite(nil) then
                lastMethod = "remote"
                return true
            end
            lastMethod = "CD/FAIL"
            return false
        end
        lastMethod = "NO SKILL"
        return false
    end"""

if old_bite not in text:
    print("ERROR: biteOnce not found", file=sys.stderr)
    sys.exit(1)
text = text.replace(old_bite, new_bite, 1)
path.write_text(text, encoding="utf-8")
print("OK integrated", len(text))
assert "skillFireBite" in text
assert "farmTapButton(bite)" not in text
