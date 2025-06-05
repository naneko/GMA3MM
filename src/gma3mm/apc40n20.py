import logging
from midi_mapper.app import App
from midi_mapper.button import ButtonType

import enum

from midi_mapper.fader import FaderType


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
    scene_launch_1 = 0x52  # 0=off, 1=on, 2=blink
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
    master_level = 0x0E
    crossfader = 0x0F
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
    master_level = 0x0E
    crossfader = 0x0F
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
    cue_level = 0x2F


# logging.basicConfig(level=logging.INFO)
#TODO: Allow shift button to be assigned that will flash relevant knobs without executing the function

app = App("10.1.1.100", 8000, "10.1.1.100", 8001)

apc40 = app.MIDI.add_device("Akai APC40", "Akai APC40")
apc20 = app.MIDI.add_device('Akai APC20', 'Akai APC20')

apc40.set_connect_bytes(b'\xF0\x47\x00\x73\x60\x00\x04\x42\x01\x01\x01\xF7') # Initialize APC40 to mode 2
apc20.set_connect_bytes(b'\xF0\x47\x7F\x7B\x60\x00\x04\x41\x08\x02\x01\xF7')

# Faders
for i in range(4):
    app.register_fader(apc40, 201 + i, InboundControlSignals.track_level.value, i, True)

for i in range(4):
    app.register_fader(apc40, 206 + i, InboundControlSignals.track_level.value, i+4, True)

for i in range(4):
    app.register_fader(apc20, 201 + i, InboundControlSignals.track_level.value, i, True)

for i in range(4):
    app.register_fader(apc20, 206 + i, InboundControlSignals.track_level.value, i+4, True)

app.register_fader(apc40, 210, InboundControlSignals.master_level.value, 0, True)
app.register_fader(apc20, 210, InboundControlSignals.master_level.value, 0, True)

grid_button = ButtonType(app)
grid_button.set_default_off(ClipLaunchLEDState.off)
grid_button.set_default_on(ClipLaunchLEDState.green)
grid_button.set_on("Toggle", ClipLaunchLEDState.yellow)
grid_button.set_blink_on("Toggle", ClipLaunchLEDState.yellow)
grid_button.set_blink_off("Toggle", ClipLaunchLEDState.off)
grid_button.set_on("Off", ClipLaunchLEDState.red)
grid_button.set_blink_on("Off", ClipLaunchLEDState.red)
grid_button.set_blink_off("Off", ClipLaunchLEDState.off)

button = ButtonType(app)
button.set_default_off(0)
button.set_default_on(1)

knob_button = ButtonType(app)
knob_button.set_default_off(0)
knob_button.set_default_on(1)
knob_button.set_blink_on("Toggle", 1)
knob_button.set_blink_off("Toggle", 0)
knob_button.set_on("Off", ClipLaunchLEDState.red)
knob_button.set_blink_on("Off", 1)
knob_button.set_blink_off("Off", 0)

# Select page buttons
for i in range(8):
    app.register_page_button(apc40, i, InboundNotes.track_selection.value, i).set_type(
        button
    )

app.register_page_button(apc40, 8, InboundNotes.master.value, 0).set_type(button)

for i in range(8):
    app.register_page_button(apc20, i, InboundNotes.track_selection.value, i).set_type(
        button
    )

app.register_page_button(apc20, 8, InboundNotes.master.value, 0).set_type(button)

# Red buttons
for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc40, 201 + j, InboundNotes.record_arm.value, i).set_type(
        button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc20, 201 + j, InboundNotes.record_arm.value, i).set_type(
        button
    )

# Blue buttons
for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc40, 101 + j, InboundNotes.solo.value, i).set_type(button)

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc20, 101 + j, InboundNotes.solo.value, i).set_type(button)

# Grid rows starting from second row down
for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc40, 401 + j, InboundNotes.clip_row_2.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc20, 401 + j, InboundNotes.clip_row_2.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc40, 301 + j, InboundNotes.clip_row_3.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc20, 301 + j, InboundNotes.clip_row_3.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc40, 201 + j, InboundNotes.clip_row_4.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc20, 201 + j, InboundNotes.clip_row_4.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc40, 101 + j, InboundNotes.clip_row_5.value, i).set_type(
        grid_button
    )

for i in range(8):
    if i >= 4:
        j = i + 1
    else:
        j = i
    app.register_button(apc20, 101 + j, InboundNotes.clip_row_5.value, i).set_type(
        grid_button
    )

app.register_button(apc40, 210, InboundNotes.stop_all_clips.value, 0).set_type(button)

# Knobs
knob = FaderType(app)
knob.set_off(KnobLEDState.off, 0)
knob.set_default_inactive_mode(KnobLEDState.volume)
knob.set_default_active_mode(KnobLEDState.volume)
knob.set_default_highlight(KnobLEDState.volume, 127)
knob.set_inactive_mode("Toggle", KnobLEDState.single)

app.register_fader(
    apc40, 401, InboundControlSignals.device_knob_1.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_1_led, 0)
app.register_fader(
    apc40, 402, InboundControlSignals.device_knob_2.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_2_led, 0)
app.register_fader(
    apc40, 403, InboundControlSignals.device_knob_3.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_3_led, 0)
app.register_fader(
    apc40, 404, InboundControlSignals.device_knob_4.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_4_led, 0)
app.register_fader(
    apc40, 301, InboundControlSignals.device_knob_5.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_5_led, 0)
app.register_fader(
    apc40, 302, InboundControlSignals.device_knob_6.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_6_led, 0)
app.register_fader(
    apc40, 303, InboundControlSignals.device_knob_7.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_7_led, 0)
app.register_fader(
    apc40, 304, InboundControlSignals.device_knob_8.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.device_knob_8_led, 0)

app.register_fader(
    apc40, 406, InboundControlSignals.track_knob_1.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_1_led, 0)
app.register_fader(
    apc40, 407, InboundControlSignals.track_knob_2.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_2_led, 0)
app.register_fader(
    apc40, 408, InboundControlSignals.track_knob_3.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_3_led, 0)
app.register_fader(
    apc40, 409, InboundControlSignals.track_knob_4.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_4_led, 0)
app.register_fader(
    apc40, 306, InboundControlSignals.track_knob_5.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_5_led, 0)
app.register_fader(
    apc40, 307, InboundControlSignals.track_knob_6.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_6_led, 0)
app.register_fader(
    apc40, 308, InboundControlSignals.track_knob_7.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_7_led, 0)
app.register_fader(
    apc40, 309, InboundControlSignals.track_knob_8.value, 0, False
).set_type(knob).set_feedback_config(OutboundControlSignals.track_knob_8_led, 0)

# Knob Buttons
app.register_button(apc40, 401, InboundNotes.clip_track.value, 0).set_type(knob_button)
app.register_button(apc40, 402, InboundNotes.device_on_off.value, 0).set_type(knob_button)
app.register_button(apc40, 403, InboundNotes.arrow_left.value, 0).set_type(knob_button)
app.register_button(apc40, 404, InboundNotes.arrow_right.value, 0).set_type(knob_button)
app.register_button(apc40, 301, InboundNotes.detail_view.value, 0).set_type(knob_button)
app.register_button(apc40, 302, InboundNotes.rec_quant.value, 0).set_type(knob_button)
app.register_button(apc40, 303, InboundNotes.midi_overdub.value, 0).set_type(knob_button)
app.register_button(apc40, 304, InboundNotes.metronome.value, 0).set_type(knob_button)
app.register_button(apc40, 306, InboundNotes.pan.value, 0).set_type(knob_button)
app.register_button(apc40, 307, InboundNotes.send_a.value, 0).set_type(knob_button)
app.register_button(apc40, 308, InboundNotes.send_b.value, 0).set_type(knob_button)
app.register_button(apc40, 309, InboundNotes.send_c.value, 0).set_type(knob_button)

app.start(exception_hook=True)
