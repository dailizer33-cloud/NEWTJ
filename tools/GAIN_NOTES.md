# AntRemotes.Gain

- Direction: server → client only (never FireServer)
- Path: `ReplicatedStorage.AntRemotes.Gain`
- Meaning: reward / power granted (after Collect success or combat)
- Spy usually pairs: `Collect` → `Gain` → `OrbTaken`
- Opposite signal: `CollectReject` (blacklist orb id)

## main.lua behavior

- Listen `Gain.OnClientEvent`
- On Gain within 2.5s of Collect: clear `farmRejectUntil` / `farmBadLootUntil` for pending orbs
- On CollectReject: blacklist pending orbs 60s
- Also: boss priority, Shout event window, rock unstuck
