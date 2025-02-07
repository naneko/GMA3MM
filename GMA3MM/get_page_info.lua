local executors = CurrentExecPage():Children()

for i = 1, #executors do
    local cue_num = executors[i].object:Get("cueno")
    if cue_num == "" or cue_num == nil then cue_num = "None" end
    CmdIndirect("SendOSC 2 \"/ExecData,issfs," .. executors[i].index .. "," .. executors[i].key .. "," .. executors[i].fader .. "," .. executors[i]:GetFader({}) .. "," .. cue_num .. "\"")
end