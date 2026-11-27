# Gain + farm fixes (Ant Evolution)

## Done in this session

### Code (local workspace `main.lua` — full file ready)
1. **Gain.OnClientEvent** — server confirms reward after Collect; clears `farmRejectUntil` within 2.5s
2. **CollectReject** — blacklist pending orb ids 60s
3. **Boss priority** — mantis/orchid/anteater/boss-hud within 600 studs
4. **Shout** — opens event loot window ~95s (mantis/treasure/stampede/queen/rain/golden)
5. **Unstuck** — hop + brief no-collide when stuck on rocks
6. Skip loot that is buried / unreachable after 4.5s chase

### GitHub commits (supporting files)
- `.github/workflows/apply-main-patch.yml`
- `tools/GAIN_NOTES.md` (this file)
- `tools/farm_gain_block.lua` (summary notes)

### Note on `main.lua` size
Full `main.lua` is ~350KB. Connector payload limit blocked a direct full-file replace in this session. Use the local patched `main.lua` from the Grok workspace, or apply the unified diff when `tools/main.lua.patch` is complete.

## Gain remote (from RobloxSpy)
- Path: `ReplicatedStorage.AntRemotes.Gain`
- Direction: **incoming only** (never FireServer)
- Typical sequence: `Collect` → `Gain` → `OrbTaken`
- Opposite: `CollectReject`
