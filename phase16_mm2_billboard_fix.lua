-- TAYJAY SOFTMOVE - Phase 16 MM2 Billboard Isolation Patch
-- Replace the existing updateMM2RoleESP() and clearMM2RoleESP() functions
-- inside TAYJAY_SOFTMOVE_Flat_UI_Clean.txt with these implementations.

local MM2_ROLE_ESP_NAME = "TayJay_MM2RoleESP"

local function updateMM2RoleESP()
    for _, player in ipairs(Players:GetPlayers()) do
        if player ~= LocalPlayer and player.Character then
            local roleName, roleColor = getMM2PlayerRole(player)
            local character = player.Character

            -- Preserve existing MM2 highlight behavior.
            local highlight = character:FindFirstChild("TayJay_PlayerHighlight")
            if not highlight then
                highlight = Instance.new("Highlight")
                highlight.Name = "TayJay_PlayerHighlight"
                highlight.Adornee = character
                highlight.DepthMode = Enum.HighlightDepthMode.AlwaysOnTop
                highlight.Parent = character
            end
            highlight.Enabled = true
            highlight.FillColor = roleColor
            highlight.OutlineColor = roleColor
            highlight.FillTransparency = 0.6
            highlight.OutlineTransparency = 0.1

            -- Phase 16: MM2 owns its own billboard and never reuses TayJay_PlayerESP.
            local adornment = character:FindFirstChild("Head") or character.PrimaryPart
            if adornment then
                local billboard = adornment:FindFirstChild(MM2_ROLE_ESP_NAME)
                if not billboard then
                    billboard = Instance.new("BillboardGui")
                    billboard.Name = MM2_ROLE_ESP_NAME
                    billboard.Adornee = adornment
                    billboard.AlwaysOnTop = true
                    billboard.LightInfluence = 0
                    billboard.MaxDistance = 500
                    billboard.Size = UDim2.new(0, 190, 0, 22)
                    billboard.StudsOffset = Vector3.new(0, 4.0, 0)
                    billboard.Parent = adornment

                    local roleLabel = Instance.new("TextLabel")
                    roleLabel.Name = "MM2RoleText"
                    roleLabel.Size = UDim2.fromScale(1, 1)
                    roleLabel.BackgroundTransparency = 1
                    roleLabel.Font = Enum.Font.GothamBold
                    roleLabel.TextSize = 13
                    roleLabel.TextStrokeTransparency = 0.48
                    roleLabel.TextStrokeColor3 = TEXT_OUTLINE
                    roleLabel.TextXAlignment = Enum.TextXAlignment.Center
                    roleLabel.Parent = billboard
                    applyTayJayTextContrast(roleLabel)
                end

                local roleLabel = billboard:FindFirstChild("MM2RoleText")
                if roleLabel then
                    roleLabel.Text = roleName
                    roleLabel.TextColor3 = roleColor
                end
            end
        end
    end
end

local function clearMM2RoleESP()
    states.MM2RoleESP = false

    for _, player in ipairs(Players:GetPlayers()) do
        local character = player.Character
        if character then
            -- Preserve Player ESP highlight when normal ESP remains enabled.
            local highlight = character:FindFirstChild("TayJay_PlayerHighlight")
            if highlight then
                if states.ESP and TJ.Main.PlayerESP then
                    highlight.Enabled = true
                    highlight.FillColor = TJ.Main.PlayerESP.FillColor
                    highlight.OutlineColor = TJ.Main.PlayerESP.OutlineColor
                    highlight.FillTransparency = 0.78
                    highlight.OutlineTransparency = 0.08
                else
                    highlight:Destroy()
                end
            end

            -- Phase 16: destroy only the MM2-owned billboard.
            local adornment = character:FindFirstChild("Head") or character.PrimaryPart
            local billboard = adornment and adornment:FindFirstChild(MM2_ROLE_ESP_NAME)
            if billboard then
                billboard:Destroy()
            end
        end
    end
end
