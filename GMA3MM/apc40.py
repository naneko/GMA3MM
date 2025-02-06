from pathlib import Path
from time import sleep

import mido

from GMA3MM.app import route_midi, route_osc, start, OSC, remap, MIDI

from GMA3MM.enums import MIDIMessageTypes, InboundNotes, OutboundNotes, OutboundControlSignals, KnobLEDState, \
    InboundControlSignals, GMA3ExecMapToAPC40, APC40MapToGMA3Exec


class State:
    selected_page = 0
    fader_values = {
        201: -1,
        202: -1,
        203: -1,
        204: -1,
        206: -1,
        207: -1,
        208: -1,
        209: -1,
        'apc1': -1,
        'apc2': -1,
        'apc3': -1,
        'apc4': -1,
        'apc5': -1,
        'apc6': -1,
        'apc7': -1,
        'apc8': -1,
        'apcached1': -1,
        'apcached2': -1,
        'apcached3': -1,
        'apcached4': -1,
        'apcached5': -1,
        'apcached6': -1,
        'apcached7': -1,
        'apcached8': -1,
    }


def clear_track_select():
    for i in range(0, 8):
        MIDI.output.send(mido.Message('note_on', channel=i, note=OutboundNotes.track_selection.value, velocity=0))
    MIDI.output.send(mido.Message('note_on', channel=0, note=OutboundNotes.master.value, velocity=0))


def gma3_update_page_data():
    with open(Path('get_page_info.lua'), 'r') as f:
        lua = f.readlines()
        OSC.send_message('/cmd', 'lua \'' + ';'.join(lua).replace('\n', '') + '\'')


def clear_apc40():
    for note in [OutboundNotes.clip_row_1.value, OutboundNotes.clip_row_2.value, OutboundNotes.clip_row_3.value,
                 OutboundNotes.clip_row_4.value, OutboundNotes.clip_row_5.value, OutboundNotes.clip_stop.value,
                 OutboundNotes.record_arm.value, OutboundNotes.solo.value, OutboundNotes.activator.value,
                 OutboundNotes.clip_track.value, OutboundNotes.device_on_off.value, OutboundNotes.arrow_left.value,
                 OutboundNotes.arrow_right.value, OutboundNotes.detail_view.value, OutboundNotes.rec_quant.value,
                 OutboundNotes.midi_overdub.value, OutboundNotes.metronome.value]:
        for ch in range(0, 8):
            MIDI.output.send(mido.Message('note_on', note=note, channel=ch, velocity=0))
    for control in [OutboundControlSignals.track_level, OutboundControlSignals.master_level, OutboundControlSignals.device_knob_1, OutboundControlSignals.device_knob_2, OutboundControlSignals.device_knob_3, OutboundControlSignals.device_knob_4, OutboundControlSignals.device_knob_5, OutboundControlSignals.device_knob_6, OutboundControlSignals.device_knob_7, OutboundControlSignals.device_knob_8]:
        for ch in range(0, 8):
            MIDI.output.send(mido.Message('control_change', control=control, channel=ch, value=0))


@route_midi([MIDIMessageTypes.note_on], 0, 8, [InboundNotes.track_selection])
def track_select(msg):
    print(f'Page {msg.channel} selected', flush=True)
    clear_track_select()
    clear_apc40()
    State.selected_page = msg.channel
    MIDI.output.send(msg.copy(velocity=1))
    gma3_update_page_data()
    OSC.send_message('/cmd', f'Page {msg.channel + 1}')


@route_midi([MIDIMessageTypes.note_on], 0, 1, [InboundNotes.master])
def track_select_master(msg):
    print(f'Page 9 selected', flush=True)
    clear_track_select()
    clear_apc40()
    State.selected_page = 9
    MIDI.output.send(msg.copy(velocity=1))
    gma3_update_page_data()
    OSC.send_message('/cmd', 'Page 9')


@route_midi([MIDIMessageTypes.control_change], 0, 8, [InboundControlSignals.track_level])
def fader_update(msg):
    # TODO: Smoothing margin (snap after certain amount of value change)
    # TODO: After page change, don't update value until fader reaches current fader level
    value = remap(msg.value, 0, 127, 0, 100)
    State.fader_values[f'apc{msg.channel + 1}'] = value
    if msg.channel < 4:
        ch = msg.channel + 201
    else:
        ch = msg.channel + 201 + 1 # Skip unused executor
    if State.fader_values[ch] != -1: # Value exists
        if State.fader_values[ch] > State.fader_values[f'apcached{msg.channel + 1}']: # If GMA3 value is greater than cached APC fader value, meaning the fader is under the latch
            if State.fader_values[ch] > value: # Then check if the current fader value is still less than the GMA3 value
                print(f'Fader {ch} at {value} | Waiting for latch above {State.fader_values[ch]}', flush=True)
                return
        elif State.fader_values[ch] < State.fader_values[f'apcached{msg.channel + 1}']: # Fader was over latch
            if State.fader_values[ch] < value: # Still over latch?
                print(f'Fader {ch} at {value} | Waiting for latch below {State.fader_values[ch]}', flush=True)
                return
    State.fader_values[ch] = -1
    print(f'/Page{State.selected_page + 1}/Fader{ch} | {value}', flush=True)
    OSC.send_message(f'/Page{State.selected_page + 1}/Fader{ch}', value)

btn_signals = [InboundNotes.clip_row_1, InboundNotes.clip_row_2, InboundNotes.clip_row_3,
                 InboundNotes.clip_row_4, InboundNotes.clip_row_5, InboundNotes.clip_stop,
                 InboundNotes.record_arm, InboundNotes.solo, InboundNotes.activator,
                 InboundNotes.clip_track, InboundNotes.device_on_off, InboundNotes.arrow_left,
                 InboundNotes.arrow_right, InboundNotes.detail_view, InboundNotes.rec_quant,
                 InboundNotes.midi_overdub, InboundNotes.metronome, InboundControlSignals.device_knob_1,
                 InboundControlSignals.device_knob_2, InboundControlSignals.device_knob_3,InboundControlSignals.device_knob_4,
               InboundControlSignals.device_knob_5, InboundControlSignals.device_knob_6, InboundControlSignals.device_knob_7,
                InboundControlSignals.device_knob_8]

@route_midi([MIDIMessageTypes.note_on, MIDIMessageTypes.note_off, MIDIMessageTypes.control_change], 0, 8, btn_signals)
def button_update(msg):
    if msg.note not in APC40MapToGMA3Exec:
        return
    executor = APC40MapToGMA3Exec[msg.note]
    if type(executor) is not int:
        executor = executor[msg.channel]
    if msg.type == MIDIMessageTypes.note_on.value:
        print(f'/Page{State.selected_page + 1}/Key{executor} ON', flush=True)
        OSC.send_message(f'/Page{State.selected_page + 1}/Key{executor}', 1)
    if msg.type == MIDIMessageTypes.note_off.value:
        print(f'/Page{State.selected_page + 1}/Key{executor} OFF', flush=True)
        OSC.send_message(f'/Page{State.selected_page + 1}/Key{executor}', 0)

@route_midi([MIDIMessageTypes.control_change], 0, 1, [InboundControlSignals.device_knob_1, InboundControlSignals.device_knob_2, InboundControlSignals.device_knob_3, InboundControlSignals.device_knob_4, InboundControlSignals.device_knob_5, InboundControlSignals.device_knob_6, InboundControlSignals.device_knob_7, InboundControlSignals.device_knob_8])
def device_knob(msg):
    MIDI.output.send(msg.copy(value=msg.value))
    value = remap(msg.value, 0, 127, 0, 100)
    match msg.control:
        case OutboundControlSignals.device_knob_1.value:
            ch = 401
        case OutboundControlSignals.device_knob_2.value:
            ch = 402
        case OutboundControlSignals.device_knob_3.value:
            ch = 403
        case OutboundControlSignals.device_knob_4.value:
            ch = 404
        case OutboundControlSignals.device_knob_5.value:
            ch = 301
        case OutboundControlSignals.device_knob_6.value:
            ch = 302
        case OutboundControlSignals.device_knob_7.value:
            ch = 303
        case OutboundControlSignals.device_knob_8.value:
            ch = 304
    print(f'/Page{State.selected_page + 1}/Fader{ch} | {value}', flush=True)
    OSC.send_message(f'/Page{State.selected_page + 1}/Fader{ch}', value)

# @route_osc('/*')
# def test_osc(address, *args):
#     print(address, flush=True)
#     print(args, flush=True)

@route_osc('/ExecData')
def exec_data(address, *args):
    # TODO: Add knobs for 400 range executors by using APC40 shift button to toggle between layers
    index, button_type, fader_type, fader_value = args
    # TODO: Use match statements to change LED behaviors, add asynchronous flashing for any LED at any rate
    # fader_types = ['Master', 'X', 'XA', 'XB', 'Temp', 'Rate', 'Speed', 'Time']
    # button_types = ['>>>', '<<<', 'Black', 'DoubleSpeed', 'Flash', 'Go+', 'Go-', 'Goto', 'HalfSpeed', 'Kill', 'LearnSpeed', 'Load', 'On', 'Off', 'Pause', 'Rate1', 'Selecet', 'SelectFixtures', 'Speed1', 'Swap', 'Temp', 'Toggle', 'Top']
    if int(index) in State.fader_values:
        State.fader_values[int(index)] = fader_value
        State.fader_values[f'apcached{index-200}'] = State.fader_values[f'apc{index-200}']
    if index in GMA3ExecMapToAPC40:
        exec_map_data = GMA3ExecMapToAPC40[index]
        # print(f'{index} | {button_type} | {fader_type} | {fader_value}')
        # print(exec_map_data, flush=True)
    else:
        return
    fader_value=int(remap(fader_value, 0, 100, 0, 127))
    if 'fader' in exec_map_data:
        MIDI.output.send(
            mido.Message('note_on', note=exec_map_data['primary_button'], channel=exec_map_data['channel'], velocity=1))
        MIDI.output.send(mido.Message('control_change', control=exec_map_data['fader'], channel=exec_map_data['channel'], value=fader_value))
    if 'grid_button' in exec_map_data:
        MIDI.output.send(
            mido.Message('note_on', note=exec_map_data['grid_button'], channel=exec_map_data['channel'], velocity=1))
    if 'knob' in exec_map_data:
        MIDI.output.send(mido.Message('note_on', note=exec_map_data['primary_button'], channel=0, velocity=1))
        MIDI.output.send(mido.Message('control_change', control=exec_map_data['knob'], channel=0, value=fader_value))
    # Set fader and knob values
    # Get executor type, or none
    # Set LED status


apc40_output_device_names = [d for d in mido.get_output_names() if 'Akai APC40' in d]
apc40_input_device_names = [d for d in mido.get_input_names() if 'Akai APC40' in d]
if len(apc40_output_device_names) < 1:
    print("No APC40 device detected")
    exit(1)
print(f'Connecting to {apc40_output_device_names[0]}', flush=True)
MIDI.set_device(apc40_output_device_names[0], apc40_input_device_names[0])

MIDI.output.send(mido.Message('note_on', channel=0, note=OutboundNotes.track_selection.value, velocity=1))

for i in range(0, 8):
    MIDI.output.send(mido.Message('control_change', control=OutboundControlSignals.device_knob_1_led.value + i,
                                  value=KnobLEDState.volume.value))

for i in range(0, 8):
    MIDI.output.send(mido.Message('control_change', control=OutboundControlSignals.track_knob_1_led.value + i,
                                  value=KnobLEDState.off.value))

MIDI.output.send(mido.Message.from_bytes(b'\xF0\x47\x00\x73\x60\x00\x04\x42\x01\x01\x01\xF7'))  # Set APC40 to mode 3

start()