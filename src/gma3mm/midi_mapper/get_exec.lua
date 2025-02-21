local cue_num = GetExecutor([[exec]]).object:Get("cueno")
if cue_num == "" or cue_num == nil then
    cue_num = "None"
end
CmdIndirect("SendOSC 2 \"/[[uid]],issfs," .. GetExecutor([[exec]]).index .. "," .. GetExecutor([[exec]]).key .. "," .. GetExecutor([[exec]]).fader .. "," .. GetExecutor([[exec]]):GetFader({}) .. "," .. cue_num .. "\"")
