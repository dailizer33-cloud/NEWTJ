import re, pathlib, shutil, sys

p = pathlib.Path("main.lua")
if not p.exists(): sys.exit("ไม่พบ main.lua — รันที่ราก repo")
src = p.read_text(encoding="utf-8")
if "TJ.Main.FarmLoot" in src: sys.exit("แพตช์ถูกใช้แล้ว — ยกเลิก")

CACHE = r"""-- =========================================================
-- FARM LOOT CACHE (perf): เลิกสแกน workspace ทุก 0.05s
-- เก็บเฉพาะ BasePart ที่ชื่อเข้าคีย์เวิร์ด + อัปเดตจาก DescendantAdded/Removing
-- สแกนเต็มอย่างเร็วทุก RESCAN_INTERVAL วินาที แบบแบ่ง batch แล้ว yield
-- เก็บผ่าน TJ.Main เพื่อไม่เพิ่ม local ใน main chunk (local-limit)
-- =========================================================
do
    local FarmLoot = TJ.Main.FarmLoot
    if type(FarmLoot) ~= "table" then FarmLoot = {}; TJ.Main.FarmLoot = FarmLoot end

    local RESCAN_INTERVAL, MAX_CANDIDATES, BATCH = 2.0, 150, 400
    local set, list = {}, {}
    local nextScan, scanning, dirty = 0, false, true

    local function matches(obj)
        if not obj:IsA("BasePart") then return false end
        local parent = obj.Parent
        if not parent then return false end
        return farmIsLootName(obj.Name .. " " .. parent.Name)
    end

    local function add(obj)
        if set[obj] or #list >= MAX_CANDIDATES then return end
        if not matches(obj) then return end
        set[obj] = true
        list[#list + 1] = obj
    end

    local function remove(obj)
        if not set[obj] then return end
        set[obj] = nil
        local idx = table.find(list, obj)
        if idx then table.remove(list, idx) end
    end

    local function reset()
        if #list == 0 and nextScan == 0 then return end
        table.clear(set); table.clear(list)
        nextScan, dirty = 0, true
    end

    local function rescan()
        if scanning then return end
        scanning = true
        nextScan = os.clock() + RESCAN_INTERVAL
        task.spawn(function()
            local newSet, newList, processed = {}, {}, 0
            local ok = pcall(function()
                for _, obj in ipairs(workspace:GetDescendants()) do
                    if _G.TAYJAY_STOPPED or not states.MonsterWarp then break end
                    if matches(obj) and #newList < MAX_CANDIDATES then
                        newSet[obj] = true
                        newList[#newList + 1] = obj
                    end
                    processed += 1
                    if processed % BATCH == 0 then task.wait() end
                end
            end)
            if ok then set, list = newSet, newList end
            scanning = false
        end)
    end

    function FarmLoot.Nearest(root, character, maxDist)
        local now = os.clock()
        if not scanning and (dirty or now >= nextScan) then
            dirty = false
            rescan()
        end
        local best, bestDist = nil, maxDist or 90
        for i = #list, 1, -1 do
            local obj = list[i]
            local parent = obj.Parent
            if not parent or not obj:IsDescendantOf(workspace) then
                remove(obj)
            elseif parent ~= character then
                local d = (obj.Position - root.Position).Magnitude
                if d > 0.5 and d < bestDist then best, bestDist = obj, d end
            end
        end
        return best, bestDist
    end

    FarmLoot.Reset = reset
    FarmLoot.MarkDirty = function() dirty = true end

    trackConnection(workspace.DescendantAdded:Connect(function(obj)
        if not states.MonsterWarp then return end
        add(obj)
    end))
    trackConnection(workspace.DescendantRemoving:Connect(function(obj)
        remove(obj)
    end))
end"""

NEWFN = r"""-- Warp-collect: ใช้แคชแทนการสแกนทั้ง workspace (พฤติกรรม hop/touch เดิม)
local function farmWarpCollectLoot()
    if not states.MonsterWarp then return end
    local now = os.clock()
    if farmOrbTouchAt > 0 and now - farmOrbTouchAt < 0.28 then return end

    local character = LocalPlayer.Character
    local root = character and (character:FindFirstChild("HumanoidRootPart") or character.PrimaryPart)
    if not root then return end

    local FarmLoot = TJ.Main.FarmLoot
    if type(FarmLoot) ~= "table" then return end

    local best = FarmLoot.Nearest(root, character, 90)
    if not best then return end

    -- soft hop toward loot (anti-kick clamp)
    local from = root.Position
    local delta = best.Position - from
    local dist = delta.Magnitude
    local hop = math.min(dist, MONSTER_WARP_MAX_HOP)
    if hop > 1.2 and dist > 1e-4 then
        local dest = from + delta.Unit * hop
        if MONSTER_GROUND_STICK then
            local gy = monsterGroundY(dest, { character })
            if math.abs(gy - dest.Y) < 18 then
                dest = Vector3.new(dest.X, gy, dest.Z)
            end
        end
        pcall(function()
            ResourceManager:RecordWrite("MonsterWarp", "Position")
            root.AssemblyLinearVelocity = Vector3.zero
            local flat = Vector3.new(delta.X, 0, delta.Z)
            local look = flat.Magnitude > 1e-3 and flat.Unit or root.CFrame.LookVector
            root.CFrame = CFrame.new(dest, dest + look)
        end)
        monsterLastMoveAt = now
    end

    -- touch / firetouch when close enough
    if (best.Position - root.Position).Magnitude <= 14 then
        pcall(function()
            if firetouchinterest then
                firetouchinterest(root, best, 0)
                firetouchinterest(root, best, 1)
            end
        end)
        local oid = best:GetAttribute("Id") or best:GetAttribute("OrbId")
            or (best.Parent and (best.Parent:GetAttribute("Id") or best.Parent:GetAttribute("OrbId")))
        if type(oid) == "number" then
            pcall(function()
                local folder = ReplicatedStorage:FindFirstChild("AntRemotes")
                local col = folder and folder:FindFirstChild("Collect")
                if col then col:FireServer({ oid }) end
            end)
        end
    end
    farmOrbTouchAt = now
end"""

pat_fn = re.compile(
    r"(?:[ \t]*--[^\n]*\n)?[ \t]*local function farmWarpCollectLoot\(\).*?"
    r"\n[ \t]*farmOrbTouchAt[ \t]*=[ \t]*now[ \t]*\nend", re.S)
src, n1 = pat_fn.subn(lambda m: NEWFN.strip("\n"), src)
if n1 != 1: sys.exit("ANCHOR_FN=%d — ยกเลิก ไม่แก้ไฟล์" % n1)

mark = NEWFN.strip("\n").split("\n")[0]
i = src.index(mark)
src = src[:i] + CACHE.strip("\n") + "\n\n" + src[i:]

pat_loop = re.compile(r"([ \t]*)farmWarpCollectLoot\(\)\n([ \t]*)end\n([ \t]*task\.wait\(0\.05\))")
def repl(m):
    a, b, w = m.groups()
    return (f"{a}farmWarpCollectLoot()\n{b}else\n"
            f"{a}local FL = TJ.Main.FarmLoot\n"
            f'{a}if type(FL) == "table" then FL.Reset() end\n'
            f"{b}end\n{w}")
src, n3 = pat_loop.subn(repl, src)
if n3 != 1: sys.exit("ANCHOR_LOOP=%d — ยกเลิก ไม่แก้ไฟล์" % n3)

shutil.copyfile(p, "main.lua.bak")
p.write_text(src, encoding="utf-8")
print("OK: แพตช์แล้ว (สำรอง main.lua.bak)")
