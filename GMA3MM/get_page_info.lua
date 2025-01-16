local executors = CurrentExecPage():Children()

for i = 1, #executors do
    CmdIndirect("SendOSC 2 \"/ExecData,issf," .. executors[i].index .. "," .. executors[i].key .. "," .. executors[i].fader .. "," .. executors[i].object:GetFader({}) .. "\"")
end