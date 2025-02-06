import enum

# TODO: Move APC40-specific enums to own file
class ClipLaunchLEDState(enum.IntEnum):
    off = 0
    green = 1
    green_blink = 2
    red = 3
    red_blink = 4
    yellow = 5
    yellow_blink = 6

class KnobLEDState(enum.IntEnum):
    off = 0
    single = 1
    volume = 2
    pan = 3

class OutboundNotes(enum.IntEnum):
    record_arm = 0x30
    solo = 0x31
    activator = 0x32
    track_selection = 0x33
    clip_stop = 0x34
    clip_row_1 = 0x35
    clip_row_2 = 0x36
    clip_row_3 = 0x37
    clip_row_4 = 0x38
    clip_row_5 = 0x39
    clip_track = 0x3A
    device_on_off = 0x3B
    arrow_left = 0x3C
    arrow_right = 0x3D
    detail_view = 0x3E
    rec_quant = 0x3F
    midi_overdub = 0x40
    metronome = 0x41
    master = 0x50
    scene_launch_1 = 0x52 # 0=off, 1=on, 2=blink
    scene_launch_2 = 0x53
    scene_launch_3 = 0x54
    scene_launch_4 = 0x55
    scene_launch_5 = 0x56
    pan = 0x57
    send_a = 0x58
    send_b = 0x59
    send_c = 0x5A

class OutboundControlSignals(enum.IntEnum):
    track_level = 0x07
    master_level = 0x0e
    crossfader = 0x0f
    device_knob_1 = 0x10
    device_knob_2 = 0x11
    device_knob_3 = 0x12
    device_knob_4 = 0x13
    device_knob_5 = 0x14
    device_knob_6 = 0x15
    device_knob_7 = 0x16
    device_knob_8 = 0x17
    device_knob_1_led = 0x18
    device_knob_2_led = 0x19
    device_knob_3_led = 0x1A
    device_knob_4_led = 0x1B
    device_knob_5_led = 0x1C
    device_knob_6_led = 0x1D
    device_knob_7_led = 0x1E
    device_knob_8_led = 0x1F
    track_knob_1 = 0x30
    track_knob_2 = 0x31
    track_knob_3 = 0x32
    track_knob_4 = 0x33
    track_knob_5 = 0x34
    track_knob_6 = 0x35
    track_knob_7 = 0x36
    track_knob_8 = 0x37
    track_knob_1_led = 0x38
    track_knob_2_led = 0x39
    track_knob_3_led = 0x3A
    track_knob_4_led = 0x3B
    track_knob_5_led = 0x3C
    track_knob_6_led = 0x3D
    track_knob_7_led = 0x3E
    track_knob_8_led = 0x3F

class InboundNotes(enum.IntEnum):
    record_arm = 0x30
    solo = 0x31
    activator = 0x32
    track_selection = 0x33
    clip_stop = 0x34
    clip_row_1 = 0x35
    clip_row_2 = 0x36
    clip_row_3 = 0x37
    clip_row_4 = 0x38
    clip_row_5 = 0x39
    clip_track = 0x3A
    device_on_off = 0x3B
    arrow_left = 0x3C
    arrow_right = 0x3D
    detail_view = 0x3E
    rec_quant = 0x3F
    midi_overdub = 0x40
    metronome = 0x41
    master = 0x50
    stop_all_clips = 0x51
    scene_launch_1 = 0x52
    scene_launch_2 = 0x53
    scene_launch_3 = 0x54
    scene_launch_4 = 0x55
    scene_launch_5 = 0x56
    pan = 0x57
    send_a = 0x58
    send_b = 0x59
    send_c = 0x5A
    play = 0x5B
    stop = 0x5C
    record = 0x5D
    up = 0x5E
    down = 0x5F
    right = 0x60
    left = 0x61
    shift = 0x62
    tap_tempo = 0x63
    nudge_plus = 0x64
    nudge_minus = 0x65

class InboundControlSignals(enum.IntEnum):
    track_level = 0x07
    master_level = 0x0e
    crossfader = 0x0f
    device_knob_1 = 0x10
    device_knob_2 = 0x11
    device_knob_3 = 0x12
    device_knob_4 = 0x13
    device_knob_5 = 0x14
    device_knob_6 = 0x15
    device_knob_7 = 0x16
    device_knob_8 = 0x17
    track_knob_1 = 0x30
    track_knob_2 = 0x31
    track_knob_3 = 0x32
    track_knob_4 = 0x33
    track_knob_5 = 0x34
    track_knob_6 = 0x35
    track_knob_7 = 0x36
    track_knob_8 = 0x37
    footswitch_1 = 0x40
    footswitch_2 = 0x41
    cue_level = 0x2f

class MIDIMessageTypes(enum.Enum):
    note_off = 'note_off'
    note_on = 'note_on'
    polytouch = 'polytouch'
    control_change = 'control_change'
    program_change = 'program_change'
    aftertouch = 'aftertouch'
    pitchwheel = 'pitchwheel'
    sysex = 'sysex'
    quarter_frame = 'quarter_frame'
    songpos = 'songpos'
    song_select = 'song_select'
    tune_request = 'tune_request'
    clock = 'clock'
    start = 'start'
    cont = 'continue'
    stop = 'stop'
    active_sensing = 'active_sensing'
    reset = 'reset'

# TODO: Move to JSON
GMA3ExecMapToAPC40 = {
    101: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 0
    },
    102: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 1
    },
    103: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 2
    },
    104: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 3
    },
    106: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 4
    },
    107: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 5
    },
    108: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 6
    },
    109: {
        'primary_button': OutboundNotes.solo.value,
        'grid_button': OutboundNotes.clip_row_5.value,
        'channel': 7
    },
    201: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 0
    },
    202: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 1
    },
    203: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 2
    },
    204: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 3
    },
    206: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 4
    },
    207: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 5
    },
    208: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 6
    },
    209: {
        'fader': OutboundControlSignals.track_level.value,
        'primary_button': OutboundNotes.record_arm.value,
        'grid_button': OutboundNotes.clip_row_4.value,
        'channel': 7
    },
    301: {
        'knob': OutboundControlSignals.device_knob_5.value,
        'primary_button': OutboundNotes.detail_view.value,
        'grid_button': OutboundNotes.clip_row_3.value,
        'channel': 0
    },
    302: {
        'knob': OutboundControlSignals.device_knob_6.value,
        'primary_button': OutboundNotes.rec_quant.value,
        'grid_button': OutboundNotes.clip_row_3.value,
        'channel': 1
    },
    303: {
        'knob': OutboundControlSignals.device_knob_7.value,
        'primary_button': OutboundNotes.midi_overdub.value,
        'grid_button': OutboundNotes.clip_row_3.value,
        'channel': 2
    },
    304: {
        'knob': OutboundControlSignals.device_knob_8.value,
        'primary_button': OutboundNotes.metronome.value,
        'grid_button': OutboundNotes.clip_row_3.value,
        'channel': 3
    },
    306: {
        'primary_button': OutboundNotes.clip_row_3.value,
        'channel': 4
    },
    307: {
        'primary_button': OutboundNotes.clip_row_3.value,
        'channel': 5
    },
    308: {
        'primary_button': OutboundNotes.clip_row_3.value,
        'channel': 6
    },
    309: {
        'primary_button': OutboundNotes.clip_row_3.value,
        'channel': 7
    },
    401: {
        'knob': OutboundControlSignals.device_knob_1.value,
        'grid_button': OutboundNotes.clip_row_2.value,
        'primary_button': OutboundNotes.clip_track.value,
        'channel': 0
    },
    402: {
        'knob': OutboundControlSignals.device_knob_2.value,
        'grid_button': OutboundNotes.clip_row_2.value,
        'primary_button': OutboundNotes.device_on_off.value,
        'channel': 1
    },
    403: {
        'knob': OutboundControlSignals.device_knob_3.value,
        'grid_button': OutboundNotes.clip_row_2.value,
        'primary_button': OutboundNotes.arrow_left.value,
        'channel': 2
    },
    404: {
        'knob': OutboundControlSignals.device_knob_4.value,
        'grid_button': OutboundNotes.clip_row_2.value,
        'primary_button': OutboundNotes.arrow_right.value,
        'channel': 3
    },
    406: {
        'primary_button': OutboundNotes.clip_row_2.value,
        'channel': 4
    },
    407: {
        'primary_button': OutboundNotes.clip_row_2.value,
        'channel': 5
    },
    408: {
        'primary_button': OutboundNotes.clip_row_2.value,
        'channel': 6
    },
    409: {
        'primary_button': OutboundNotes.clip_row_2.value,
        'channel': 7
    },
    210: {
        'fader': OutboundControlSignals.master_level.value,
        'primary_button': OutboundNotes.clip_stop.value,
        'channel': 0
    }
    # 191: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 0
    # },
    # 192: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 1
    # },
    # 193: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 2
    # },
    # 194: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 3
    # },
    # 195: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 4
    # },
    # 196: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 5
    # },
    # 197: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 6
    # },
    # 198: {
    #     'primary_button': OutboundNotes.clip_row_5.value,
    #     'channel': 7
    # },
    # 291: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 0
    # },
    # 292: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 1
    # },
    # 293: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 2
    # },
    # 294: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 3
    # },
    # 295: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 4
    # },
    # 296: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 5
    # },
    # 297: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 6
    # },
    # 298: {
    #     'primary_button': OutboundNotes.clip_stop.value,
    #     'channel': 7
    # },
}

APC40MapToGMA3Exec = {
    InboundControlSignals.track_level.value: { #201
        # Channels -> Executors
        0: 201,
        1: 202,
        2: 203,
        3: 204,
        4: 206,
        5: 207,
        6: 208,
        7: 209,
    },
    InboundNotes.record_arm.value: {
        0: 201,
        1: 202,
        2: 203,
        3: 204,
        4: 206,
        5: 207,
        6: 208,
        7: 209,
    },
    InboundNotes.solo.value: {
        0: 101,
        1: 102,
        2: 103,
        3: 104,
        4: 106,
        5: 107,
        6: 108,
        7: 109,
    },
    InboundNotes.clip_row_2.value: {
        0: 401,
        1: 402,
        2: 403,
        3: 404,
        4: 406,
        5: 407,
        6: 408,
        7: 409,
    },
    InboundNotes.clip_row_3.value: {
        0: 301,
        1: 302,
        2: 303,
        3: 304,
        4: 306,
        5: 307,
        6: 308,
        7: 309,
    },
    InboundNotes.clip_row_4.value: {
        0: 201,
        1: 202,
        2: 203,
        3: 204,
        4: 206,
        5: 207,
        6: 208,
        7: 209,
    },
    InboundNotes.clip_row_5.value: {
        0: 101,
        1: 102,
        2: 103,
        3: 104,
        4: 106,
        5: 107,
        6: 108,
        7: 109,
    },
    # InboundNotes.clip_row_5.value: {
    #     0: 191,
    #     1: 192,
    #     2: 193,
    #     3: 194,
    #     4: 195,
    #     5: 196,
    #     6: 197,
    #     7: 198,
    # },
    # InboundNotes.clip_stop.value: {
    #     0: 291,
    #     1: 292,
    #     2: 293,
    #     3: 294,
    #     4: 295,
    #     5: 296,
    #     6: 297,
    #     7: 298,
    # },
    InboundControlSignals.device_knob_1.value: 401,
    InboundControlSignals.device_knob_2.value: 402,
    InboundControlSignals.device_knob_3.value: 403,
    InboundControlSignals.device_knob_4.value: 404,
    InboundControlSignals.device_knob_5.value: 301,
    InboundControlSignals.device_knob_6.value: 302,
    InboundControlSignals.device_knob_7.value: 303,
    InboundControlSignals.device_knob_8.value: 304,
    InboundNotes.clip_track.value: 401,
    InboundNotes.device_on_off.value: 402,
    InboundNotes.arrow_left.value: 403,
    InboundNotes.arrow_right.value: 404,
    InboundNotes.detail_view.value: 301,
    InboundNotes.rec_quant.value: 302,
    InboundNotes.midi_overdub.value: 303,
    InboundNotes.metronome.value: 304,
    InboundControlSignals.master_level.value: 210,
}