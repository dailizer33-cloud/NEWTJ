# Hybrid Skill System (Ant Evolution)

ไฟล์: `modules/skill_hybrid.lua`  
ที่มา: RobloxSpy log 2026-11-25 place `123969755970816`

## Remote จริงที่ใช้ (ฝั่งเซิร์ฟเวอร์)

| Remote | วิธี | อาร์กิวเมนต์ |
|--------|------|-------------|
| `AntRemotes.Bite` | FireServer | `targetId:number\|nil` |
| `AntRemotes.Move` | FireServer | `direction:Vector3`, `targetId:number\|nil` |
| `AntRemotes.Evolve` | InvokeServer | (ไม่มี) |
| `AntRemotes.Collect` | FireServer | `{orbId, ...}` |

Bindable `Event` (Sprint/Bite/Move UI) เป็นแค่สถานะปุ่ม — **ไม่ใช้ยิงสกิล**

## วิธีใช้ใน main.lua

```lua
local SkillHybrid = require(path.to.skill_hybrid)
-- หรือหลังโหลดไฟล์:
-- local SkillHybrid = _G.TAYJAY_SKILL_HYBRID or TJ.SkillHybrid

-- ยิงเอง
SkillHybrid.FireBite(nil)                    -- กัดรอบตัว
SkillHybrid.FireBite(-100154)                -- กัดเป้า (network id)
SkillHybrid.FireMove(lookVector, targetId)   -- สกิลประจำร่าง
SkillHybrid.FireMoveAt(monsterRoot, id)
SkillHybrid.FireEvolve()
SkillHybrid.FireCollect({ 3152, 3151 })

-- โหมดอัตโนมัติ (ไฮบริด)
SkillHybrid.SetAuto({ Bite = true, Move = true, Evolve = false })
SkillHybrid.StartAuto(ownerBag)  -- optional cleanup bag

-- ในลูปฟาร์ม
SkillHybrid.Tick({
    targetRoot = monsterRoot,
    targetId = networkId,
    wantBite = true,
    wantMove = true,
    orbIds = nearbyOrbIds,
})
```

## จุดเด่นแบบไฮบริด

- มี cooldown ภายใน (กันยิงถี่เกิน log)
- ใช้ทิศจาก `HumanoidRootPart` หรือเป้าจริง
- เปิด/ปิด Auto แยก Bite / Move / Evolve
- เผยแพร่ผ่าน `_G.TAYJAY_SKILL_HYBRID` และ `TJ.SkillHybrid`
- pcall ทุกครั้ง — ไม่ทำให้สคริปต์หลักพังถ้า remote หาย

## แนะนำการผูกกับระบบเดิม

1. **Rapid Bite** → เรียก `FireBite` แทนคลิกปุ่ม
2. **MonsterWarp ใกล้เป้า** → `FireMoveAt` + `FireBite`
3. **Power bar เต็ม** → `FireEvolve`
4. **เก็บ orb ระยะใกล้** → `FireCollect` (ถ้าต้องการยิงตรง)

## หมายเหตุ anti-cheat

- ส่งเฉพาะทิศทางที่เป็น unit vector และ targetId ที่สมเหตุสมผล
- ไม่แทนที่ระบบเคลื่อนที่ (ยังใช้ soft-glide เดิมได้)
- อย่าสแปมเร็วกว่า cooldown ของเกม
