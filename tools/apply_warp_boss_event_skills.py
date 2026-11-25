#!/usr/bin/env python3
"""Warp only for event/boss, remove monster-table noclip, fire skills whenever ready."""
from pathlib import Path
import re
import sys

path = Path("main.lua")
text = path.read_text(encoding="utf-8")

if "WARP_BOSS_EVENT_ONLY" in text and "monsterNoclipStep disabled" in text:
    print("already applied boss/event warp + noclip remove + skill ready")
    sys.exit(0)

old_kw = """    local FARM_LOOT_KEYWORDS = {
        "orb", "acorn", "buff", "event", "power", "xp", "energy", "glow",
        "capsule", "pickup", "token", "shard", "fruit", "apple", "nut",
        "boost", "gift", "chest", "drop", "reward", "crystal", "gem",
    }"""

new_kw = """    -- WARP_BOSS_EVENT_ONLY: warp-collect only event/boss-related pickups
    local FARM_LOOT_KEYWORDS = {
        "event", "boss", "queen", "raid", "worldboss", "world boss",
        "limited", "special event", "boss drop", "boss orb",
    }"""

if old_kw not in text:
    print("ERROR: loot keywords not found", file=sys.stderr)
    sys.exit(1)
text = text.replace(old_kw, new_kw, 1)
print("loot keywords -> event/boss only")

text = text.replace(
    "    -- Warp-collect: hop to nearby orb/acorn/buff/event then touch",
    "    -- Warp-collect: hop ONLY to event/boss-related loot then touch",
    1,
)

if "if horizDist > MONSTER_FAR_HOP then" not in text:
    print("ERROR: FAR hop block not found", file=sys.stderr)
    sys.exit(1)

old_sig = "    local function monsterSoftApply(myRoot, desiredCF, character, targetModel, dt, aerial)"
new_sig = "    local function monsterSoftApply(myRoot, desiredCF, character, targetModel, dt, aerial, allowWarp)"
if old_sig not in text:
    print("ERROR: soft apply signature not found", file=sys.stderr)
    sys.exit(1)
text = text.replace(old_sig, new_sig, 1)

text = text.replace(
    "      if horizDist > MONSTER_FAR_HOP then",
    "      -- FAR hop only for boss/event (WARP_BOSS_EVENT_ONLY); normal mobs use joystick only\n"
    "      if allowWarp and horizDist > MONSTER_FAR_HOP then",
    1,
)
print("far hop gated by allowWarp")

old_call = "      monsterSoftApply(myRoot, destination, character, target.model, dt, aerial)"
new_call = """      local allowWarp = isBoss
        or (type(target.reason) == "string" and string.find(string.lower(target.reason), "event", 1, true) ~= nil)
        or (type(target.name) == "string" and (
              string.find(string.lower(target.name), "boss", 1, true) ~= nil
              or string.find(string.lower(target.name), "event", 1, true) ~= nil
              or string.find(string.lower(target.name), "queen", 1, true) ~= nil
           ))
      monsterSoftApply(myRoot, destination, character, target.model, dt, aerial, allowWarp)"""
if old_call not in text:
    print("ERROR: soft apply call not found", file=sys.stderr)
    sys.exit(1)
text = text.replace(old_call, new_call, 1)
print("glue step passes allowWarp for boss/event")

p = re.compile(
    r"    local function monsterDisableCollision\(character\)\n"
    r"        local list = \{\}.*?"
    r"    local function monsterNoclipStep\(\)\n"
    r"        if not states\.MonsterWarp or not monsterCurrent then return end\n"
    r"        for _, part in ipairs\(monsterNoclipList\) do\n"
    r"            if part\.Parent and part\.CanCollide then part\.CanCollide = false end\n"
    r"        end\n"
    r"    end\n",
    re.DOTALL,
)
new_disable = """    -- monsterNoclipStep disabled: removed from monster table (no collision strip)
    local function monsterDisableCollision(character)
        -- no-op: do not disable collision while farming monsters
        monsterNoclipList = {}
    end
    local function monsterNoclipStep()
        -- no-op
    end
"""
if not p.search(text):
    print("ERROR: monster noclip functions not found", file=sys.stderr)
    sys.exit(1)
text = p.sub(new_disable, text, count=1)
print("monster table noclip removed")

text = text.replace(
    "    trackConnection(RunService.Stepped:Connect(monsterNoclipStep))",
    "    -- trackConnection(RunService.Stepped:Connect(monsterNoclipStep)) -- removed: no monster noclip",
    1,
)

p2 = re.compile(
    r"    task\.spawn\(function\(\)\n"
    r"        local nextBite, nextMove = 0, 0\n"
    r"        while screenGui\.Parent and not _G\.TAYJAY_STOPPED do\n"
    r"            if states\.MonsterWarp and monsterFilterMode == \"Monster\" then\n"
    r"                local now = os\.clock\(\)\n"
    r"                if now >= nextBite then\n"
    r"                    if skillFireBite\(nil\) then nextBite = now \+ 0\.62 else nextBite = now \+ 0\.2 end\n"
    r"                end\n"
    r"                if now >= nextMove then\n"
    r"                    if skillFireMoveAtTarget\(\) then nextMove = now \+ 10\.5 else nextMove = now \+ 1 end\n"
    r"                end\n"
    r"                farmWarpCollectLoot\(\)\n"
    r"            end\n"
    r"            task\.wait\(0\.05\)\n"
    r"        end\n"
    r"    end\)",
)
new_skill = """    task.spawn(function()
        -- Fire skills whenever ready (cooldowns enforced inside skillFire*)
        local nextBite, nextMove = 0, 0
        while screenGui.Parent and not _G.TAYJAY_STOPPED do
            if states.MonsterWarp and monsterFilterMode == "Monster" then
                local now = os.clock()
                if now >= nextBite then
                    if skillFireBite(nil) then
                        nextBite = now + 0.62
                    else
                        nextBite = now + 0.05  -- retry soon until ready
                    end
                end
                if now >= nextMove then
                    if skillFireMoveAtTarget() then
                        nextMove = now + 10.5
                    else
                        nextMove = now + 0.15  -- poll until Move skill ready
                    end
                end
                farmWarpCollectLoot()
            end
            task.wait(0.05)
        end
    end)"""
if not p2.search(text):
    print("ERROR: skill worker not found", file=sys.stderr)
    sys.exit(1)
text = p2.sub(new_skill, text, count=1)
print("skills fire whenever ready")

path.write_text(text, encoding="utf-8")
print("OK", len(text))
assert "WARP_BOSS_EVENT_ONLY" in text
assert "monsterNoclipStep disabled" in text or "no-op" in text
assert "allowWarp" in text
assert "nextBite = now + 0.05" in text
