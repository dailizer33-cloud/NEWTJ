from pathlib import Path

paths = [Path("main.lua"), Path("patches/phase19c_state_service.lua")]

for path in paths:
    text = path.read_text(encoding="utf-8")
    old_repair = 'StateService:Apply({ KillAura = false, DNWarp = false, AutoWarp = false }, "warp_stop_now")'
    new_repair = 'StateService:Apply({ KillAura = false, DNWarp = false, AutoWarp = false }, "startup_repair")'
    if old_repair in text:
        text = text.replace(old_repair, new_repair, 1)
    elif new_repair not in text:
        raise AssertionError(f"startup repair anchor missing in {path}")

    if path.name == "main.lua":
        old_sync = '''local function syncButtonState(key, isOn, reason)\n    local ok, result = StateService:Transition(key, isOn == true, reason or ("ui:" .. tostring(key)))\n    if not ok then\n        warn("[TAYJAY StateService] transition rejected: " .. tostring(key) .. " / " .. tostring(result))\n        return false, result\n    end\n    for changedKey, changedValue in pairs(result) do\n        if uiSyncRegistry[changedKey] then\n            pcall(function() uiSyncRegistry[changedKey](changedValue == true) end)\n        end\n    end\n    return true\nend'''
        new_sync = '''local function syncButtonState(key, isOn, reason)\n    local before = StateService:Snapshot()\n    local ok, result = StateService:Transition(key, isOn == true, reason or ("ui:" .. tostring(key)))\n    if not ok then\n        warn("[TAYJAY StateService] transition rejected: " .. tostring(key) .. " / " .. tostring(result))\n        return false, result\n    end\n    local after = StateService:Snapshot()\n    for changedKey, changedValue in pairs(after) do\n        if before[changedKey] ~= changedValue and uiSyncRegistry[changedKey] then\n            pcall(function() uiSyncRegistry[changedKey](changedValue == true) end)\n        end\n    end\n    return true, after\nend'''
        if old_sync in text:
            text = text.replace(old_sync, new_sync, 1)
        elif new_sync not in text:
            raise AssertionError("syncButtonState anchor missing in main.lua")

    path.write_text(text, encoding="utf-8")

print("Phase 19C startup repair and UI sync fixed")
