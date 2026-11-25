-- Phase 19C authoritative state service.
-- Integration target: place after Main.states/default initialization in main.lua.
-- This module mutates state only. It does not move characters or destroy instances.

local function installPhase19CStateService(Main, states)
    assert(type(Main) == "table", "StateService requires Main")
    assert(type(states) == "table", "StateService requires states")

    local StateService = Main.StateService
    if type(StateService) ~= "table" then
        StateService = {}
        Main.StateService = StateService
    end

    StateService.Version = 1
    StateService._states = states
    StateService._listeners = {}
    StateService._transitioning = false
    StateService._revision = tonumber(StateService._revision) or 0
    StateService.Groups = {
        player_movement = { KillAura = true, DNWarp = true, AutoWarp = true },
        monster_movement = { MonsterWarp = true },
        visual_player = { ESP = true },
        visual_mm2 = { MM2RoleESP = true },
    }

    local function copyState(source)
        local result = {}
        for key, value in pairs(source) do result[key] = value end
        return result
    end

    local function groupFor(name)
        for groupName, members in pairs(StateService.Groups) do
            if members[name] then return groupName end
        end
        return nil
    end

    local function validate(candidate)
        local monster = candidate.MonsterWarp == true
        local player = candidate.KillAura == true
            or candidate.DNWarp == true
            or candidate.AutoWarp == true
        if monster and player then
            return false, "movement_group_conflict"
        end
        return true
    end

    local function notify(change)
        local listeners = copyState(StateService._listeners)
        for _, callback in pairs(listeners) do
            local ok, err = pcall(callback, change)
            if not ok then warn("[TAYJAY StateService] listener: " .. tostring(err)) end
        end
    end

    function StateService:Get(name)
        return self._states[name]
    end

    function StateService:IsEnabled(name)
        return self._states[name] == true
    end

    function StateService:Snapshot()
        return copyState(self._states)
    end

    function StateService:Subscribe(callback)
        if type(callback) ~= "function" then return function() end end
        local token = {}
        self._listeners[token] = callback
        local connected = true
        return function()
            if not connected then return false end
            connected = false
            self._listeners[token] = nil
            return true
        end
    end

    function StateService:DisableGroup(groupName, reason, exceptName)
        local members = self.Groups[groupName]
        if type(members) ~= "table" then return false, "unknown_group" end
        local changes = {}
        for name in pairs(members) do
            if name ~= exceptName and self._states[name] == true then
                changes[name] = false
            end
        end
        return self:Apply(changes, reason or ("disable_group:" .. groupName))
    end

    function StateService:Apply(changes, reason)
        if type(changes) ~= "table" then return false, "invalid_changes" end
        if self._transitioning then return false, "transition_in_progress" end

        self._transitioning = true
        local before = self:Snapshot()
        local candidate = copyState(before)
        local normalized = {}

        for name, value in pairs(changes) do
            if before[name] == nil then
                self._transitioning = false
                return false, "unknown_state:" .. tostring(name)
            end
            normalized[name] = value == true
            candidate[name] = value == true
        end

        local valid, validationError = validate(candidate)
        if not valid then
            self._transitioning = false
            return false, validationError
        end

        local changed = {}
        for name, value in pairs(normalized) do
            if before[name] ~= value then
                self._states[name] = value
                changed[name] = value
            end
        end

        self._revision = self._revision + 1
        self._transitioning = false

        if next(changed) then
            notify({
                revision = self._revision,
                reason = tostring(reason or "transition"),
                before = before,
                after = self:Snapshot(),
                changed = changed,
            })
        end
        return true, self:Snapshot()
    end

    function StateService:Transition(name, enabled, reason)
        if self._states[name] == nil then return false, "unknown_state" end
        enabled = enabled == true

        local changes = { [name] = enabled }
        if enabled then
            local groupName = groupFor(name)
            if groupName == "player_movement" then
                changes.MonsterWarp = false
                for otherName in pairs(self.Groups.player_movement) do
                    if otherName ~= name then changes[otherName] = false end
                end
            elseif groupName == "monster_movement" then
                for otherName in pairs(self.Groups.player_movement) do
                    changes[otherName] = false
                end
            end
        end
        return self:Apply(changes, reason or (name .. ":" .. tostring(enabled)))
    end

    function StateService:Reset(reason)
        local changes = {}
        for name in pairs(self._states) do changes[name] = false end
        return self:Apply(changes, reason or "reset")
    end

    local valid, validationError = validate(states)
    if not valid then
        states.KillAura = false
        states.DNWarp = false
        states.AutoWarp = false
        warn("[TAYJAY StateService] repaired startup state: " .. validationError)
    end

    return StateService
end

return installPhase19CStateService
