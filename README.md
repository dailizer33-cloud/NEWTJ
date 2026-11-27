# NEWTJ

สคริปต์ Lua แบบ client (สไตล์ executor) ไฟล์เดียว: เมนู UI, Player ESP, MM2 Role ESP,
Death Note / Monster Warp, Rapid Bite, FPS Booster, Server Hop ฯลฯ

> สถานะ: **Phase 18.3** — GitHub `main.lua` เป็น Source of Truth

## โครงสร้าง

| Path | คืออะไร |
|---|---|
| `main.lua` | ตัวสคริปต์หลัก (Phase 18.3) |
| `original.txt` | snapshot ต้นฉบับก่อน Phase 16 |
| `patches/` | patch ของแต่ละ phase (`.diff` ใช้ `git apply` ได้) |
| `docs/` | บันทึกแต่ละ phase + checklist |
| `static-check.sh` | ตรวจโครงสร้างโค้ดด้วย grep (ไม่ใช่การรันจริง) |

## วิธีรัน

สคริปต์ใช้ API ของ executor (`gethui`, `getgenv`, `request`, `firetouchinterest`,
`setclipboard`, `writefile`/`readfile`) จึงออกแบบให้รันผ่าน executor ในเกม ไม่ใช่โมดูลที่วางใน
Roblox Studio ได้ทันที — ใน Studio ฟังก์ชันเหล่านี้ส่วนใหญ่เป็น `nil` ทดสอบได้แค่ UI/ESP บางส่วน

**แบบวางไฟล์โดยตรง:** เปิด `main.lua` แล้ววางทั้งไฟล์ใน executor แล้วกด Execute

**แบบโหลดจาก repo ของคุณ** (แก้ `<USER>` / `<REPO>` / branch ให้ตรง):

```lua
loadstring(game:HttpGet("https://raw.githubusercontent.com/dailizer33-cloud/NEWTJ/main/main.lua"))()
```

หมายเหตุ: ใช้ลักษณะนี้หมายความว่าใครมีสิทธิ์เขียน repo ก็คุมโค้ดที่คุณรัน — เปิด 2FA และจำกัดสิทธิ์ push

## ตรวจโค้ดก่อน commit

```bash
bash static-check.sh main.lua
```

ตรวจว่า MM2 ใช้ billboard ของตัวเอง (`TayJay_MM2RoleESP`), billboard ปกติ
(`TayJay_PlayerESP`) ถูกควบคุมด้วย `states.ESP` อย่างเดียว และ cleanup ครบ

ถ้าติดตั้ง Luau แล้ว สคริปต์จะรัน `luau-analyze` ต่อให้อัตโนมัติ (global ของ executor จะขึ้นเป็น
unknown-global — เป็นเรื่องปกติ) GitHub Actions (`.github/workflows/static-check.yml`) รันเฉพาะ
structural check

## ทดสอบจริง

ดูรายละเอียด Phase 18.3 ใน `docs/PHASE18_3.md` (ESP ปิด/เปิดคู่กับ MM2, เปลี่ยน role, respawn, STOP ALL,
รันซ้ำ 2 รอบ)

## License

ยังไม่ได้เลือก license — ดู `LICENSE.txt` ก่อนทำ repo เป็น public


## Source of Truth

ตั้งแต่ Phase 18.3 เป็นต้นไป ให้ใช้ `main.lua` บน GitHub branch `main` เป็นไฟล์หลักในการอ่าน ตรวจสอบ และพัฒนาต่อ ไฟล์ใน Library ใช้เป็นแหล่งอ้างอิงย้อนหลังเท่านั้น เว้นแต่ผู้ใช้จะสั่งเปลี่ยนแหล่งต้นฉบับ
