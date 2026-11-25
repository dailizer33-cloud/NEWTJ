# Fix: attempt to index nil with 'Main'

## Problem
When PHASE 20B (Theme) and PHASE 21 (PerformanceOptimizer) were inserted early in `main.lua` (before `app_state` / ResourceManager initialization), the code did:

```lua
TJ.Main.Theme = Theme
Main.Theme = Theme
...
TJ.Main.PerformanceOptimizer = PerformanceOptimizer
Main.PerformanceOptimizer = PerformanceOptimizer
```

At that point `TJ` was still `nil`, causing:

```
attempt to index nil with 'Main'
```

## Fix
Insert this block **immediately before** `-- PHASE 20B: THEME SYSTEM`:

```lua
-- Ensure TJ / Main exist before Theme & PerformanceOptimizer attach to them.
-- These phases sit early in the file (before app_state / ResourceManager init).
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
```

This initializes `TJ` and `TJ.Main` (and the local `Main` alias) using the same `getgenv`/`_G` pattern used later in the file, so the Theme and PerformanceOptimizer assignments succeed.

## Status
- Phase 19 baseline (current `main`) does not contain the Theme/PerformanceOptimizer phases, so the crash does not occur there.
- If you are running a build that includes those phases, apply the block above.
