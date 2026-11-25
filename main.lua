-- TEMPORARY PLACEHOLDER
-- The real main.lua was accidentally overwritten.
-- See conversation for the fix to "attempt to index nil with 'Main'".
-- Re-apply this block just before "PHASE 20B: THEME SYSTEM":
--[[
local _tjEarlyEnv = _G
pcall(function()
    if type(getgenv) == "function" then
        local shared = getgenv()
        if type(shared) == "table" then _tjEarlyEnv = shared end
    end
end)
if type(_tjEarlyEnv.TJ) ~= "table" then
    _tjEarlyEnv.TJ = {}
end
TJ = _tjEarlyEnv.TJ
if type(TJ.Main) ~= "table" then
    TJ.Main = {}
end
Main = TJ.Main
--]]

error("main.lua is a temporary placeholder. Restore the full file and insert the TJ.Main init before PHASE 20B.")
