from pathlib import Path

main_path = Path("main.lua")
patch_path = Path("patches/phase19c_state_service.lua")
text = main_path.read_text(encoding="utf-8")
patch = patch_path.read_text(encoding="utf-8")

if "-- TAYJAY STATE SERVICE V1 (PHASE 19C)" in text:
    print("Phase 19C already integrated")
    raise SystemExit(0)

start = patch.index("local function installPhase19CStateService")
end = patch.rindex("return installPhase19CStateService")
service = patch[start:end].rstrip() + "\n\nlocal StateService = installPhase19CStateService(Main, states)\n"
anchor = "TJ.Main = Main\n-- TAYJAY MOVEMENT CONTROLLER V1"
assert anchor in text, "state-service insertion anchor missing"
text = text.replace(anchor, "TJ.Main = Main\n-- TAYJAY STATE SERVICE V1 (PHASE 19C)\n" + service + "-- TAYJAY MOVEMENT CONTROLLER V1", 1)

old_sync = '''local function syncButtonState(key, isOn)\n    states[key] = isOn\n    if uiSyncRegistry[key] then pcall(function() uiSyncRegistry[key](isOn) end) end\nend'''
new_sync = '''local function syncButtonState(key, isOn, reason)\n    local ok, result = StateService:Transition(key, isOn == true, reason or ("ui:" .. tostring(key)))\n    if not ok then\n        warn("[TAYJAY StateService] transition rejected: " .. tostring(key) .. " / " .. tostring(result))\n        return false, result\n    end\n    for changedKey, changedValue in pairs(result) do\n        if uiSyncRegistry[changedKey] then\n            pcall(function() uiSyncRegistry[changedKey](changedValue == true) end)\n        end\n    end\n    return true\nend'''
assert old_sync in text, "syncButtonState anchor missing"
text = text.replace(old_sync, new_sync, 1)

replacements = {
'''        states.KillAura = not states.KillAura\n        if states.KillAura then\n            states.NormalKillAura = false''': '''        local changed = StateService:Transition("KillAura", not states.KillAura, "warp_button")\n        if not changed then return end\n        if states.KillAura then\n            StateService:Transition("NormalKillAura", false, "warp_button")''',
'''        states.NormalKillAura = not states.NormalKillAura\n        if states.NormalKillAura then\n            states.KillAura = false''': '''        local changed = StateService:Transition("NormalKillAura", not states.NormalKillAura, "walk_button")\n        if not changed then return end\n        if states.NormalKillAura then\n            StateService:Transition("KillAura", false, "walk_button")''',
'''                states.DNWarp = false\n                return''': '''                StateService:Transition("DNWarp", false, "claim_failed")\n                return''',
'''            states.KillAura = false\n            if flyNowe then stopFlying() end''': '''            StateService:Transition("KillAura", false, "dnwarp_enabled")\n            if flyNowe then stopFlying() end''',
'''                states.AutoWarp = false\n                return''': '''                StateService:Transition("AutoWarp", false, "claim_failed")\n                return''',
'''            states.KillAura = false\n        elseif not states.KillAura and not states.DNWarp''': '''            StateService:Transition("KillAura", false, "autowarp_enabled")\n        elseif not states.KillAura and not states.DNWarp''',
'''        states.KillAura = false\n        states.DNWarp = false\n        states.AutoWarp = false''': '''        StateService:Apply({ KillAura = false, DNWarp = false, AutoWarp = false }, "warp_stop_now")''',
'''        states.MonsterWarp = false\n        local speedCharacter''': '''        StateService:Transition("MonsterWarp", false, "monster_stop")\n        local speedCharacter''',
'''        states.MonsterWarp = true\n        monsterHome = root.CFrame''': '''        local stateReady = StateService:Transition("MonsterWarp", true, "monster_start")\n        if not stateReady then\n            monsterWarpStarting = false\n            if _tjMovementController then _tjMovementController:Release("MONSTER") end\n            return\n        end\n        monsterHome = root.CFrame''',
'''        states.MM2RoleESP = false\n    \n        for _, player''': '''        StateService:Transition("MM2RoleESP", false, "mm2_clear")\n    \n        for _, player''',
'''        states.MM2RoleESP = false\n        mm2ESPButton.BackgroundColor3''': '''        StateService:Transition("MM2RoleESP", false, "mm2_stop")\n        mm2ESPButton.BackgroundColor3''',
'''        states.MM2RoleESP = mm2ESPEnabled\n        if mm2ESPEnabled then''': '''        StateService:Transition("MM2RoleESP", mm2ESPEnabled, "mm2_button")\n        mm2ESPEnabled = states.MM2RoleESP == true\n        if mm2ESPEnabled then''',
'''    states.KillAura = false\n    states.NormalKillAura = false\n    states.AutoWarp = false\n    states.DNWarp = false''': '''    StateService:Apply({\n        KillAura = false, NormalKillAura = false, AutoWarp = false, DNWarp = false\n    }, "STOP_ALL")''',
}
for old, new in replacements.items():
    if old not in text:
        raise AssertionError("replacement anchor missing: " + old.splitlines()[0])
    text = text.replace(old, new, 1)

# TargetService remains the target authority, but state mutation is delegated.
text = text.replace('''        statesRef.DNWarp = true''', '''        StateService:Transition("DNWarp", true, "target_lock")''', 1)
text = text.replace('''    statesRef.DNWarp = false''', '''    StateService:Transition("DNWarp", false, reason or "target_unlock")''', 1)

main_path.write_text(text, encoding="utf-8")
print("Phase 19C integrated into main.lua")
