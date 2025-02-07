local cue_num = GetExecutor([[]]).object:Get("cueno")
if cue_num == "" or cue_num == nil then cue_num = "None" end
CmdIndirect("SendOSC 2 \"/UpdateBlink,issfs," .. GetExecutor([[]]).index .. "," .. GetExecutor([[]]).key .. "," .. GetExecutor([[]]).fader .. "," .. GetExecutor([[]]):GetFader({}) .. "," .. cue_num .. "\"")