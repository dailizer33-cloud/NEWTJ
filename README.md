# TAYJAY SOFTMOVE

สคริปต์ Lua แบบ client (สไตล์ executor) ไฟล์เดียว: เมนู UI, Player ESP, MM2 Role ESP,
Death Note / Monster Warp, Rapid Bite, FPS Booster, Server Hop ฯลฯ

> สถานะ: **Phase 17** — ดู `CHANGELOG.md`

## โครงสร้าง

| Path | คืออะไร |
|---|---|
| `src/main.lua` | ตัวสคริปต์หลัก (Phase 17) |
| `src/original.txt` | snapshot ต้นฉบับก่อน Phase 16 |
| `patches/` | patch ของแต่ละ phase (`.diff` ใช้ `git apply` ได้) |
| `docs/` | บันทึกแต่ละ phase + checklist |
| `scripts/static-check.sh` | ตรวจโครงสร้างโค้ดด้วย grep (ไม่ใช่การรันจริง) |

## วิธีรัน

สคริปต์ใช้ API ของ executor (`gethui`, `getgenv`, `request`, `firetouchinterest`,
`setclipboard`, `writefile`/`readfile`) จึงออกแบบให้รันผ่าน executor ในเกม ไม่ใช่โมดูลที่วางใน
Roblox Studio ได้ทันที — ใน Studio ฟังก์ชันเหล่านี้ส่วนใหญ่เป็น `nil` ทดสอบได้แค่ UI/ESP บางส่วน

**แบบวางไฟล์โดยตรง:** เปิด `src/main.lua` แล้ววางทั้งไฟล์ใน executor แล้วกด Execute

**แบบโหลดจาก repo ของคุณ** (แก้ `<USER>` / `<REPO>` / branch ให้ตรง):

```lua
loadstring(game:HttpGet("https://raw.githubusercontent.com/<USER>/<REPO>/main/src/main.lua"))()
```

หมายเหตุ: ใช้ลักษณะนี้หมายความว่าใครมีสิทธิ์เขียน repo ก็คุมโค้ดที่คุณรัน — เปิด 2FA และจำกัดสิทธิ์ push

การใช้สคริปต์ในเกมที่ไม่ใช่ของคุณอาจขัดกับข้อตกลงของ Roblox และเสี่ยงโดนลงโทษบัญชี

## ตรวจโค้ดก่อน commit

```bash
./scripts/static-check.sh src/main.lua
```

ตรวจว่า MM2 ใช้ billboard ของตัวเอง (`TayJay_MM2RoleESP`), billboard ปกติ
(`TayJay_PlayerESP`) ถูกควบคุมด้วย `states.ESP` อย่างเดียว และ cleanup ครบ

ถ้าติดตั้ง Luau แล้ว สคริปต์จะรัน `luau-analyze` ต่อให้อัตโนมัติ (global ของ executor จะขึ้นเป็น
unknown-global — เป็นเรื่องปกติ) GitHub Actions (`.github/workflows/static-check.yml`) รันเฉพาะ
structural check

## ทดสอบจริง

ดู checklist ใน `docs/PHASE17.md` (ESP ปิด/เปิดคู่กับ MM2, เปลี่ยน role, respawn, STOP ALL,
รันซ้ำ 2 รอบ)

## License

ยังไม่ได้เลือก license — ดู `LICENSE.txt` ก่อนทำ repo เป็น public
