-- NEWTJ Delta Skill GUI: BITE ONLY
-- Execute main.lua first, then execute this file in Delta.
-- COPY ONLY: reuses the existing SkillHybrid.FireBite function.
-- Does not remove, move, rename, or edit any main-menu command.
-- The interval controls client-side call attempts; the existing skill cooldown remains intact.

local ENV = (getgenv and getgenv()) or _G
local function resolveAPI()
    local api = ENV.TAYJAY_SKILL_HYBRID
    if type(api) ~= "table" and type(ENV.TJ) == "table" then
        api = ENV.TJ.SkillHybrid
    end
    if type(api) == "table" and type(api.FireBite) == "function" then
        return api
    end
    return nil
end

-- Replace this GUI instance only; leave all main-script UI and commands untouched.
if type(ENV.NEWTJ_BITE_GUI_STOP) == "function" then
    pcall(ENV.NEWTJ_BITE_GUI_STOP)
end

local Players = game:GetService("Players")
local CoreGui = game:GetService("CoreGui")
local player = Players.LocalPlayer
local parent
pcall(function()
    if type(gethui) == "function" then parent = gethui() end
end)
parent = parent or player:WaitForChild("PlayerGui")

local old = parent:FindFirstChild("NEWTJ_BiteSkillGUI")
if old then pcall(function() old:Destroy() end) end

local running, enabled, locked = true, false, false
local interval = 0.5
local connections = {}
local gui = Instance.new("ScreenGui")
gui.Name = "NEWTJ_BiteSkillGUI"
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.DisplayOrder = 9998
gui.Parent = parent

local function connect(signal, callback)
    local c = signal:Connect(callback)
    table.insert(connections, c)
    return c
end

local function stop()
    running, enabled = false, false
    for _, c in ipairs(connections) do
        pcall(function() c:Disconnect() end)
    end
    table.clear(connections)
    if ENV.NEWTJ_BITE_GUI_STOP then ENV.NEWTJ_BITE_GUI_STOP = nil end
end
ENV.NEWTJ_BITE_GUI_STOP = stop

local panel = Instance.new("Frame")
panel.Name = "Panel"
panel.Size = UDim2.fromOffset(310, 190)
panel.Position = UDim2.new(0.5, -155, 0.55, -95)
panel.BackgroundColor3 = Color3.fromRGB(24, 48, 25)
panel.BorderSizePixel = 0
panel.Active = true
panel.Parent = gui
local pc = Instance.new("UICorner")
pc.CornerRadius = UDim.new(0, 12)
pc.Parent = panel
local ps = Instance.new("UIStroke")
ps.Color = Color3.fromRGB(90, 255, 35)
ps.Thickness = 2
ps.Parent = panel

local function makeLabel(text, pos, size, fontSize)
    local o = Instance.new("TextLabel")
    o.BackgroundTransparency = 1
    o.Position = pos
    o.Size = size
    o.Font = Enum.Font.GothamBold
    o.Text = text
    o.TextSize = fontSize or 14
    o.TextColor3 = Color3.new(1, 1, 1)
    o.TextStrokeTransparency = 0.45
    o.Parent = panel
    return o
end

local function makeButton(text, pos, size, color, callback)
    local b = Instance.new("TextButton")
    b.Position = pos
    b.Size = size
    b.BackgroundColor3 = color
    b.BorderSizePixel = 0
    b.Font = Enum.Font.GothamBold
    b.Text = text
    b.TextSize = 15
    b.TextColor3 = Color3.new(1, 1, 1)
    b.TextStrokeTransparency = 0.5
    b.Parent = panel
    local c = Instance.new("UICorner")
    c.CornerRadius = UDim.new(0, 8)
    c.Parent = b
    connect(b.Activated, callback)
    return b
end

makeLabel("TAYJAY  |  BITE SKILL", UDim2.fromOffset(12, 7), UDim2.fromOffset(230, 28), 17)
local close = makeButton("X", UDim2.fromOffset(268, 7), UDim2.fromOffset(30, 28),
    Color3.fromRGB(210, 45, 25), function()
        stop()
        gui:Destroy()
    end)
local lock
lock = makeButton("UNLOCK", UDim2.fromOffset(205, 42), UDim2.fromOffset(93, 27),
    Color3.fromRGB(90, 90, 90), function()
        locked = not locked
        lock.Text = locked and "LOCKED" or "UNLOCK"
    end)

local toggle
toggle = makeButton("BITE  OFF", UDim2.fromOffset(12, 42), UDim2.fromOffset(180, 45),
    Color3.fromRGB(190, 55, 20), function()
        enabled = not enabled
        toggle.Text = enabled and "BITE  ON" or "BITE  OFF"
        toggle.BackgroundColor3 = enabled and Color3.fromRGB(25, 170, 45)
            or Color3.fromRGB(190, 55, 20)
    end)

makeLabel("ATTACK INTERVAL", UDim2.fromOffset(12, 100), UDim2.fromOffset(150, 25), 13)
local value = makeLabel("0.5 sec", UDim2.fromOffset(165, 98), UDim2.fromOffset(130, 28), 20)
local minus = makeButton("-", UDim2.fromOffset(12, 130), UDim2.fromOffset(75, 38),
    Color3.fromRGB(35, 145, 55), function()
        interval = math.min(5, math.floor((interval + 0.50001) * 100) / 100)
        interval = math.max(0.5, interval - 0.5)
        value.Text = string.format("%.1f sec", interval)
    end)
local plus = makeButton("+", UDim2.fromOffset(100, 130), UDim2.fromOffset(75, 38),
    Color3.fromRGB(225, 145, 15), function()
        interval = math.min(5, interval + 0.5)
        value.Text = string.format("%.1f sec", interval)
    end)
local status = makeLabel("READY  |  API cooldown remains active", UDim2.fromOffset(12, 169),
    UDim2.fromOffset(286, 17), 10)

-- Drag only from the title area. Lock disables dragging.
local dragging, dragInput, dragStart, startPos
connect(panel.InputBegan, function(input)
    if locked then return end
    if input.UserInputType == Enum.UserInputType.MouseButton1
        or input.UserInputType == Enum.UserInputType.Touch then
        dragging = true
        dragStart = input.Position
        startPos = panel.Position
        dragInput = input
    end
end)
connect(panel.InputChanged, function(input)
    if input.UserInputType == Enum.UserInputType.MouseMovement
        or input.UserInputType == Enum.UserInputType.Touch then
        dragInput = input
    end
end)
local UserInputService = game:GetService("UserInputService")
connect(UserInputService.InputChanged, function(input)
    if dragging and not locked and (input == dragInput) then
        local delta = input.Position - dragStart
        panel.Position = UDim2.new(startPos.X.Scale, startPos.X.Offset + delta.X,
            startPos.Y.Scale, startPos.Y.Offset + delta.Y)
    end
end)
connect(UserInputService.InputEnded, function(input)
    if input == dragInput then dragging = false end
end)

connect(gui.Destroying, stop)

task.spawn(function()
    while running and gui.Parent do
        local API = resolveAPI()
        if not API then
            status.Text = "WAITING  |  execute main.lua first"
        elseif enabled then
            local ok, result = pcall(API.FireBite)
            status.Text = ok and (result == false and "WAITING  |  API cooldown" or "BITE CALL SENT")
                or "ERROR  |  check Delta console"
        else
            status.Text = "READY  |  API connected"
        end
        task.wait(interval)
    end
end)

print("[NEWTJ BITE GUI] Ready | interval 0.5s | COPY ONLY")
