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
local cue_num = exec.object:Get("cueno")
if cue_num == "" or cue_num == nil then
    cue_num = "None"
end
Cmd("SendOSC 2 \"/[[uid]],issfs," .. exec.index .. "," .. exec.key .. "," .. exec.fader .. "," .. exec:GetFader({}) .. "," .. cue_num .. "\"")
