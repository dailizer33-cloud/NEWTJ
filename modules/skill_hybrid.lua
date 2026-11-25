-- =========================================================
-- TAYJAY / NEWTJ — Hybrid Skill System (Ant Evolution)
-- Source: RobloxSpy logs 2026-11-25 (place 123969755970816)
-- =========================================================
-- Real remotes (server):
--   AntRemotes.Bite :FireServer(targetId|nil)
--   AntRemotes.Move :FireServer(direction:Vector3, targetId|nil)
--   AntRemotes.Evolve :InvokeServer()
--   AntRemotes.Collect :FireServer({orbId, ...})
--
-- UI Event (Bindable) is display-only — do NOT use it to fire skills.
-- =========================================================

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local LocalPlayer = Players.LocalPlayer

local SkillHybrid = {
	Version = 1,
	-- toggles
	AutoBite = false,
	AutoMove = false,
	AutoEvolve = false,
	-- timing (from log cooldowns + safety margin)
	BiteCooldown = 0.62,          -- game ~0.58
	MoveCooldown = 10.5,          -- varies by stage skill (10–13s)
	EvolveCooldown = 1.5,
	CollectBatchMax = 8,
	-- range helpers
	BiteRange = 18,
	MoveRange = 40,
	-- internal
	_lastBite = 0,
	_lastMove = 0,
	_lastEvolve = 0,
	_remotes = nil,
	_conn = nil,
	_owner = nil,
}

-- ---------- remote resolve ----------
local function getRemotes()
	if SkillHybrid._remotes then return SkillHybrid._remotes end
	local ok, folder = pcall(function()
		return ReplicatedStorage:WaitForChild("AntRemotes", 8)
	end)
	if not ok or not folder then return nil end
	local pack = {
		Bite = folder:FindFirstChild("Bite"),
		Move = folder:FindFirstChild("Move"),
		Evolve = folder:FindFirstChild("Evolve"),
		Collect = folder:FindFirstChild("Collect"),
	}
	SkillHybrid._remotes = pack
	return pack
end

-- ---------- helpers ----------
local function now()
	return os.clock()
end

local function getRoot(character)
	if not character then return nil end
	return character:FindFirstChild("HumanoidRootPart")
		or character:FindFirstChild("RootPart")
		or character.PrimaryPart
end

local function getMyRoot()
	return getRoot(LocalPlayer.Character)
end

local function getLookDirection()
	local root = getMyRoot()
	if not root then return Vector3.new(0, 0, -1) end
	local look = root.CFrame.LookVector
	local flat = Vector3.new(look.X, 0, look.Z)
	if flat.Magnitude < 0.05 then return Vector3.new(0, 0, -1) end
	return flat.Unit
end

local function directionTo(targetPos)
	local root = getMyRoot()
	if not root then return getLookDirection() end
	local delta = targetPos - root.Position
	local flat = Vector3.new(delta.X, 0, delta.Z)
	if flat.Magnitude < 0.05 then return getLookDirection() end
	return flat.Unit
end

-- Network id heuristic from logs: negative integers (e.g. -100154)
local function asNetworkId(value)
	if type(value) == "number" and value < 0 then return value end
	return nil
end

-- ---------- core fire (pcall-safe) ----------
function SkillHybrid.FireBite(targetId)
	local rem = getRemotes()
	if not rem or not rem.Bite then return false end
	local t = now()
	if t - SkillHybrid._lastBite < SkillHybrid.BiteCooldown then return false end
	local ok = pcall(function()
		rem.Bite:FireServer(asNetworkId(targetId))
	end)
	if ok then SkillHybrid._lastBite = t end
	return ok
end

function SkillHybrid.FireMove(direction, targetId)
	local rem = getRemotes()
	if not rem or not rem.Move then return false end
	local t = now()
	if t - SkillHybrid._lastMove < SkillHybrid.MoveCooldown then return false end

	direction = direction or getLookDirection()
	if typeof(direction) == "Vector3" and direction.Magnitude > 0.001 then
		direction = direction.Unit
	else
		direction = getLookDirection()
	end

	local ok = pcall(function()
		rem.Move:FireServer(direction, asNetworkId(targetId))
	end)
	if ok then SkillHybrid._lastMove = t end
	return ok
end

function SkillHybrid.FireMoveAt(targetRoot, targetId)
	if targetRoot and targetRoot.Parent then
		return SkillHybrid.FireMove(directionTo(targetRoot.Position), targetId)
	end
	return SkillHybrid.FireMove(getLookDirection(), targetId)
end

function SkillHybrid.FireEvolve()
	local rem = getRemotes()
	if not rem or not rem.Evolve then return false end
	local t = now()
	if t - SkillHybrid._lastEvolve < SkillHybrid.EvolveCooldown then return false end
	local ok = pcall(function()
		rem.Evolve:InvokeServer()
	end)
	if ok then SkillHybrid._lastEvolve = t end
	return ok
end

function SkillHybrid.FireCollect(orbIds)
	local rem = getRemotes()
	if not rem or not rem.Collect then return false end
	if type(orbIds) ~= "table" or #orbIds == 0 then return false end
	-- batch limit from practical log sizes
	local batch = {}
	for i = 1, math.min(#orbIds, SkillHybrid.CollectBatchMax) do
		batch[i] = orbIds[i]
	end
	return pcall(function()
		rem.Collect:FireServer(batch)
	end)
end

-- ---------- hybrid auto loop ----------
-- Call from Heartbeat / farm loop with optional context:
--   ctx = { targetRoot, targetId, wantBite, wantMove, wantEvolve, orbIds }
function SkillHybrid.Tick(ctx)
	ctx = ctx or {}
	if SkillHybrid.AutoBite and ctx.wantBite ~= false then
		if ctx.targetRoot then
			local my = getMyRoot()
			if my and (ctx.targetRoot.Position - my.Position).Magnitude <= SkillHybrid.BiteRange then
				SkillHybrid.FireBite(ctx.targetId)
			else
				SkillHybrid.FireBite(nil)
			end
		else
			SkillHybrid.FireBite(nil)
		end
	end
	if SkillHybrid.AutoMove and ctx.wantMove ~= false then
		if ctx.targetRoot then
			local my = getMyRoot()
			if my and (ctx.targetRoot.Position - my.Position).Magnitude <= SkillHybrid.MoveRange then
				SkillHybrid.FireMoveAt(ctx.targetRoot, ctx.targetId)
			end
		end
	end
	if SkillHybrid.AutoEvolve and ctx.wantEvolve then
		SkillHybrid.FireEvolve()
	end
	if ctx.orbIds and #ctx.orbIds > 0 then
		SkillHybrid.FireCollect(ctx.orbIds)
	end
end

function SkillHybrid.StartAuto(ownerBag)
	SkillHybrid.StopAuto()
	SkillHybrid._owner = ownerBag
	SkillHybrid._conn = RunService.Heartbeat:Connect(function()
		-- lightweight: only runs when at least one auto flag is on
		if not (SkillHybrid.AutoBite or SkillHybrid.AutoMove or SkillHybrid.AutoEvolve) then
			return
		end
		SkillHybrid.Tick()
	end)
	if ownerBag and type(ownerBag.Add) == "function" then
		pcall(function() ownerBag:Add(SkillHybrid._conn) end)
	end
	return SkillHybrid._conn
end

function SkillHybrid.StopAuto()
	if SkillHybrid._conn then
		pcall(function() SkillHybrid._conn:Disconnect() end)
		SkillHybrid._conn = nil
	end
end

function SkillHybrid.SetAuto(opts)
	opts = opts or {}
	if opts.Bite ~= nil then SkillHybrid.AutoBite = opts.Bite and true or false end
	if opts.Move ~= nil then SkillHybrid.AutoMove = opts.Move and true or false end
	if opts.Evolve ~= nil then SkillHybrid.AutoEvolve = opts.Evolve and true or false end
end

-- Publish for main.lua / other modules
local env = _G
pcall(function()
	if type(getgenv) == "function" then
		local g = getgenv()
		if type(g) == "table" then env = g end
	end
end)
env.TAYJAY_SKILL_HYBRID = SkillHybrid
if type(env.TJ) ~= "table" then env.TJ = {} end
env.TJ.SkillHybrid = SkillHybrid

return SkillHybrid
