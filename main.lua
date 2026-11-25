-- TAYJAY EARLY BOOTSTRAP: visible before game loading / PlayerGui waits.

-- =============================================
-- [TAYJAY ERROR FILTER] - Filter Game Script Errors
-- Purpose: Suppress console spam from game scripts
-- Must be defined BEFORE any code that might trigger errors
-- =============================================
local _tjOriginalWarn = warn
local _tjOriginalPrint = print
local _tjErrorFilterEnabled = true

-- Filter warn() messages
warn = function(...)
    if not _tjErrorFilterEnabled then
        _tjOriginalWarn(...)
        return
    end
    local messages = {...}
    local message = type(messages[1]) == "string" and messages[1] or tostring(messages[1])
    if #messages > 1 then
        for i = 2, #messages do
            message = message .. " " .. tostring(messages[i])
        end
    end
    if type(message) == "string" then
        local lowerMsg = string.lower(message)
        -- Filter: Invalid block id
        if lowerMsg:find("invalid block id") then
            return
        end
        -- Filter: HTTP 404
        if lowerMsg:find("http 404") or lowerMsg:find("404 not found") then
            return
        end
        -- Filter: attempt to call nil
        if lowerMsg:find("attempt to call a nil value") or lowerMsg:find("attempt to call") then
            return
        end
        -- Filter: destroyed script
        if lowerMsg:find("destroyed") and lowerMsg:find("script") then
            return
        end
        -- Filter: Stack Begin/End spam
        if lowerMsg:find("stack begin") or lowerMsg:find("stack end") then
            return
        end
        -- Filter: Other script status messages (TopbarPlus, etc.)
        if lowerMsg:find("running ") or lowerMsg:find(" by @") or
           lowerMsg:find("loaded ") or lowerMsg:find("disabled local") or
           lowerMsg:find("finding suitable spawn") or
           lowerMsg:find("resolving backed up task") or
           lowerMsg:find("waiting for chunk load") or
           lowerMsg:find("resolved") or
           lowerMsg:find("character is successfully loaded") or
           lowerMsg:find("disabling") or
           lowerMsg:find("clear") or
           lowerMsg:find("show data") then
            return
        end
        -- Filter: LocalScript enumeration spam from OPF:R
        if lowerMsg:find("all.localscript") or lowerMsg:find("players.ttay_jjay.playergui.opf:r") or
           lowerMsg:find("updated.mainframe.pages") or
           lowerMsg:match(".*%.localscri") then
            return
        end
    end
    _tjOriginalWarn(...)
end

print = function(...)
    if not _tjErrorFilterEnabled then
        _tjOriginalPrint(...)
        return
    end
    local messages = {...}
    local message = type(messages[1]) == "string" and messages[1] or tostring(messages[1])
    if #messages > 1 then
        for i = 2, #messages do
            message = message .. " " .. tostring(messages[i])
        end
    end
    if type(message) == "string" then
        -- Filter: Coordinate spam (e.g., "253.29, 338.99, 309.29")
        if message:match("^%d+%.%d+,%s*%d+%.%d+,%s*%d+%.%d+$") then
            return
        end
        -- Filter: Accessory (Mesh) spam
        if message:find("Accessory (Mesh)") then
            return
        end
    end
    _tjOriginalPrint(...)
end
