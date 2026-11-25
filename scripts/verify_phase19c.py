from pathlib import Path
import re
import sys

text = Path("main.lua").read_text(encoding="utf-8")
errors = []

required = [
    '-- TAYJAY STATE SERVICE V1 (PHASE 19C)',
    'local StateService = installPhase19CStateService(Main, states)',
    '"startup_repair"',
    'local before = StateService:Snapshot()',
    'local after = StateService:Snapshot()',
    'if before[changedKey] ~= changedValue and uiSyncRegistry[changedKey] then',
    'StateService:Transition("MonsterWarp", true, "monster_start")',
    'StateService:Apply({\n        KillAura = false, NormalKillAura = false, AutoWarp = false, DNWarp = false\n    }, "STOP_ALL")',
]
for item in required:
    if item not in text:
        errors.append("missing: " + item)

forbidden = [
    'for changedKey, changedValue in pairs(result) do',
    '"warp_stop_now")\n        warn("[TAYJAY StateService] repaired startup state:',
]
for item in forbidden:
    if item in text:
        errors.append("forbidden: " + item)

writer_pattern = re.compile(r"states\.(KillAura|NormalKillAura|DNWarp|AutoWarp|MonsterWarp|MM2RoleESP)\s*=(?!=)")
writers = [(text.count("\n", 0, m.start()) + 1, m.group(0)) for m in writer_pattern.finditer(text)]
if writers:
    errors.append("runtime direct-writer candidates remain: " + ", ".join(f"line {line} {snippet}" for line, snippet in writers))

if errors:
    print("Phase 19C verification: FAIL", file=sys.stderr)
    for error in errors:
        print("- " + error, file=sys.stderr)
    raise SystemExit(1)

print("Phase 19C verification: PASS")
