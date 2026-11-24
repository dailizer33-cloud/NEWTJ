# Phase 16 - MM2 Billboard Isolation

## Integrated behavior

- MM2 uses `TayJay_MM2RoleESP` on Head or PrimaryPart.
- MM2 role text and role color remain independent from the normal Player ESP billboard.
- `clearMM2RoleESP()` removes the MM2 billboard directly.
- When normal ESP remains enabled, its highlight styling is restored after MM2 ESP is turned off.
- When normal ESP is disabled, MM2 cleanup removes the highlight it was using.

## Static verification

- Independent billboard name: PASS
- No `TayJay_PlayerESP` lookup in patched MM2 functions: PASS
- Billboard creation: PASS
- MM2 billboard destruction: PASS

## Runtime checks still recommended

- ESP OFF + MM2 ESP ON
- Role change
- Respawn
- STOP ALL
- Startup failure path
- Re-run twice in the runtime environment
