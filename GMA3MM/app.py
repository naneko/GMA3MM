import threading
from numbers import Number
from time import sleep

import mido
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import OSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from GMA3MM.enums import MIDIMessageTypes

midi_device_names = mido.get_input_names()
print('Connected devices: ' +', '.join(midi_device_names))
if len(midi_device_names) < 1:
    print("No MIDI devices detected")
    exit(1)

class MIDI:
    """
    Handles MIDI input and output
    """
    output = None
    input = mido.open_input()

    @staticmethod
    def set_output_device(device_name: str):
        """
        Set output device based on name. Check first log message for currently connected device names.

        :param device_name: Device name
        """
        MIDI.output = mido.open_output(device_name)

# TODO: Allow IP to be set externally
osc_client_ip = "127.0.0.1"
osc_client_port = 8000
OSC = SimpleUDPClient(osc_client_ip, osc_client_port)

dispatcher = Dispatcher()

midi_routes = {}
osc_routes = {}

for message_type in MIDIMessageTypes:
    midi_routes[message_type.value] = {}
    for i in range(0, 16):
        midi_routes[message_type.value][i] = {}

## Decorators
def route_midi(msg_types: [MIDIMessageTypes], start_channel: int, end_channel: int, signals: [int]):
    """
    Decorator to execute a function via MIDI
    :param msg_type: MIDI message type (see MIDIMessageTypes enum)
    :param start_channel: Start MIDI channel
    :param end_channel: End MIDI channel (non-inclusive)
    :param signal: MIDI signal to watch (such as a note or control change)
    :return: Wrapper function
    """
    def wrapper(func):
        for msg_type in msg_types:
            for i in range(start_channel, end_channel):
                for signal in signals:
                    midi_routes[msg_type.value][i][signal.value] = func
    return wrapper

def route_osc(address: str):
    """
    Decorator to execute a function via OSC
    :param address: OSC address
    :return: Wrapper function
    """
    def wrapper(func):
        dispatcher.map(address, func)
        return func
    return wrapper

def midi_handler():
    """
    Blocking MIDI router that routes to route_midi decorated functions
    """
    for msg in MIDI.input:
        print("MIDI Debug: " + msg.__repr__(), flush=True)
        try:
            if msg.is_cc():
                midi_routes[msg.type][msg.channel][msg.control](msg)
            else:
                midi_routes[msg.type][msg.channel][msg.note](msg)
        except KeyError:
            pass

def osc_server():
    """
    Blocking OSC server
    """
    # TODO: Allow IP and port to be set externally
    ip = "127.0.0.1"
    port = 8001
    server = OSCUDPServer((ip, port), dispatcher)
    server.serve_forever()

def remap(old_val, old_min, old_max, new_min, new_max):
    """
    Remap values proportionally from existing range to target range

    :param old_val: Value to be remapped
    :param old_min: Min value for old_val
    :param old_max: Max value for old_val
    :param new_min: New min value
    :param new_max: New max value
    :return: Remapped value
    """
    return (new_max - new_min)*(old_val - old_min) / (old_max - old_min) + new_min

def start():
    """
    Starts GMA3MM
    """
    # Workaround allows GMA3MM to bind to port 8001 by telling GMA3 to disable OSC output for a second and then turning back on so it can't bind to the port itself
    OSC.send_message('/cmd', 'Set OSC Property "EnableOutput" false')
    sleep(1)
    threading.Thread(target=midi_handler).start()
    threading.Thread(target=osc_server).start()
    OSC.send_message('/cmd', 'Set OSC Property "EnableOutput" true')