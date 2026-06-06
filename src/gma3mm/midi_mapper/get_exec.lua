local page = Root():Children()[13]:Children()[14]:Children()[1]:Children()[12]:Children()[[[page]]]
if page == nil then
    return
end
local exec = nil
for i = 1, #page:Children() do
    if page:Children()[i].index == [[exec]] then
        exec = page:Children()[i]
        break
    end
end
if exec == nil then
    return
end
local cue_num = nil
if exec.object ~= nil then
    if exec.object:HasActivePlayback() then
        cue_num = 1
    else
        cue_num = "None"
    end
else
    cue_num = 1
end
CmdIndirect("SendOSC 2 \"/[[uid]],issfs," .. exec.index .. "," .. exec.key .. "," .. exec.fader .. "," .. exec:GetFader({}) .. "," .. cue_num .. "\" /NoOops")
