import enum
import logging
from multiprocessing.pool import ThreadPool
import pprint
import threading
from time import sleep
from typing import TYPE_CHECKING
import mido
if TYPE_CHECKING:
    from midi_mapper.app import App


class MIDIHandler:
    """
    Handles MIDI input and output
    """

    def __init__(self, app: 'App'):
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.app: 'App' = app
        self.devices: list[Device] = []
        self.midi_routes: dict[str, MIDIMessageTypes, int, int, callable] = {}
        self.lock = threading.Lock()

        self.log.info("Connected output MIDI devices: " + ", ".join(mido.get_output_names()))
        self.log.info("Connected input MIDI devices: " + ", ".join(mido.get_input_names()))

    def add_device(self, input_device_name: str, output_device_name: str):
        """
        Add MIDI input and output devices based on name. Check first log message for currently connected device names.

        :param output_device_name: Output device name
        :param input_device_name: Input device name
        """
        self.log.debug("Adding MIDI device | Input Name: " + input_device_name + " | Output Name: " + output_device_name)
        new_device = Device(self.app, input_device_name, output_device_name)
        with self.lock:
            self.devices.append(new_device)
            self.midi_routes[input_device_name] = {}
            for message_type in MIDIMessageTypes:
                self.midi_routes[input_device_name][message_type.value] = {}
                for i in range(0, 16):
                    self.midi_routes[input_device_name][message_type.value][i] = {}

            return new_device
    
    def get_device(self, input_device_name: str = None, output_device_name: str = None) -> 'Device':
        """
        Get MIDI input and output devices based on name. Only input or output name is needed. If both are provided, will search by input first.

        :param output_device_name: Output device name
        :param input_device_name: Input device name
        """
        if input_device_name:
            for device in self.devices:
                if device.input_name == input_device_name:
                    device.connect()
                    return device
        elif output_device_name:
            for device in self.devices:
                if device.output_name == output_device_name:
                    device.connect()
                    return device
        return None

    def route(
        self, device: 'Device', msg_types: 'MIDIMessageTypes', start_channel: int, end_channel: int, signals: list[int]
    ) -> callable:
        """
        Decorator to execute a function via MIDI
        :param device:
        :param msg_types: MIDI message type (see MIDIMessageTypes enum)
        :param start_channel: Start MIDI channel
        :param end_channel: End MIDI channel (non-inclusive)
        :param signals: MIDI signal to watch (such as a note or control change)
        :return: Wrapper function
        """

        def wrapper(func):
            with self.lock:
                for msg_type in msg_types:
                    for i in range(start_channel, end_channel):
                        for signal in signals:
                            self.log.debug(f"Adding MIDI route to {func.__name__} | Device: {device.input_name} | Message Type: {msg_type} | Channel: {i} | Signal: {signal}")
                            self.midi_routes[device.input_name][msg_type][i][signal] = func

        return wrapper
    
    def add_route(self, device: 'Device', msg_type: 'MIDIMessageTypes', channel: int, signal: int, func: callable, overwrite: bool = False):
        """
        Map a route directly without a decorator
        :param device:
        :param msg_type: MIDI message type (see MIDIMessageTypes enum)
        :param channel: MIDI channel
        :param signal: MIDI signal to watch (such as a note or control change)
        :param func: Function to execute
        """
        # TODO: Check for overwrite
        with self.lock:
            self.log.debug(f"Adding MIDI route to {func.__name__} | Device: {device.input_name} | Message Type: {msg_type} | Channel: {channel} | Signal: {signal}")
            self.midi_routes[device.input_name][msg_type.value][channel][signal] = func

    def send_note(self, device: 'Device', msg_type: 'MIDIMessageTypes', channel: int, note: int, value: int):
        self.log.debug(f"Sending MIDI note | Device: {device.input_name} | Message Type: {msg_type} | Channel: {channel} | Note: {note} | Value: {value}")
        device.output.send(mido.Message(msg_type.value, channel=channel, note=note, velocity=value))

    def send_control_change(self, device: 'Device', msg_type: 'MIDIMessageTypes', channel: int, control: int, value: int):
        self.log.debug(f"Sending MIDI control change | Device: {device.input_name} | Message Type: {msg_type} | Channel: {channel} | Control: {control} | Value: {value}")
        device.output.send(mido.Message(msg_type.value, channel=channel, control=control, value=value))

    def send_sysex(self, device: 'Device', sysex: list[bytes]):
        self.log.debug(f"Sending MIDI sysex | Device: {device.input_name} | Sysex: {sysex}")
        device.output.send(mido.Message('sysex', data=sysex))

    def send_bytes(self, device: 'Device', bytes: bytes):
        self.log.debug(f"Sending MIDI bytes | Device: {device.input_name} | Bytes: {bytes}")
        device.output.send(mido.Message.from_bytes(bytes))
    
    def start(self):
        """
        Start MIDI router
        """
        for device in self.devices:
            self.log.debug(f"Starting MIDI thread for device | Device: {device.input_name}")
            threading.Thread(target=self.midi_device_thread, args=(self, device)).start()
            
    @staticmethod
    def midi_device_thread(midi_handler: 'MIDIHandler', device: 'Device'):
        # Yes, this is the best way to do this. Try/except will hide key errors in the callback functions. Ask me how I know.
        midi_handler.log.info(f"Starting MIDI thread for device | Device: {device.input_name}")
        while True:
            if device.input:
                for msg in device.input:
                    with midi_handler.lock:
                        if msg.is_cc():
                            midi_handler.log.debug(f"Received MIDI control change | Device: {device.input_name} | Message: {msg}")
                            if msg.type in midi_handler.midi_routes[device.input_name]:
                                if msg.channel in midi_handler.midi_routes[device.input_name][msg.type]:
                                    if msg.control in midi_handler.midi_routes[device.input_name][msg.type][msg.channel]:
                                        midi_handler.log.debug(f"Routing MIDI control change | Device: {device.input_name} | Message: {msg}")
                                        midi_handler.midi_routes[device.input_name][msg.type][msg.channel][msg.control](msg)
                        elif msg.type in midi_handler.midi_routes[device.input_name] and hasattr(msg, 'note'):
                            midi_handler.log.debug(f"Received MIDI message | Device: {device.input_name} | Message: {msg}")
                            if msg.channel in midi_handler.midi_routes[device.input_name][msg.type]:
                                if msg.note in midi_handler.midi_routes[device.input_name][msg.type][msg.channel]:
                                    midi_handler.log.debug(f"Routing MIDI message | Device: {device.input_name} | Message: {msg}")
                                    midi_handler.midi_routes[device.input_name][msg.type][msg.channel][msg.note](msg)

class Device:
    """
    Represents a MIDI device
    """

    def __init__(self, app, input_name: str, output_name: str):
        self.app: 'App' = app
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.input_name: str = input_name
        self.output_name: str = output_name
        self.input = None
        self.output = None
        self.connected: bool = False
        self.connecting = threading.Lock()
        self.lock = threading.Lock()
        self.page: int = 0

        self.log.debug(f"Initializing MIDI device | Input Name: {self.input_name} | Output Name: {self.output_name}")

        self.connect()

    def connect(self):

        self.app.log.debug(f"Starting MIDI connection process | Input Name: {self.input_name} | Output Name: {self.output_name}")

        def connect_helper():
            with self.connecting:
                while True:
                    try:
                        self.app.log.debug(f"Connecting to MIDI device | Input Name: {self.input_name} | Output Name: {self.output_name}")
                        self.input = mido.open_input(self.input_name)
                        self.output = mido.open_output(self.output_name)
                        self.connected = True
                        self.log.info(f"Connected to MIDI device | Input Name: {self.input_name} | Output Name: {self.output_name}")
                        self.set_page(self.page) # Initialize the page
                        break
                    except OSError:
                        if self.input:
                            self.input.close()
                        if self.output:
                            self.output.close()
                        self.input = None
                        self.output = None
                        self.connected = False
                        self.log.error(f"Could not connect to MIDI device. Trying again in 5 seconds... | Input Name: {self.input_name} | Output Name: {self.output_name}")
                    sleep(5)

            
        if not self.connecting.locked():
            threading.Thread(target=connect_helper).start()

    def set_page(self, page: int):
        with self.lock:
            self.log.debug(f"Setting page | Device: {self.input_name} | Page: {page}")
            self.page = page
            for button in self.app.buttons:
                if button.device == self and button.select_page == page:
                    button.update_feedback(self.app, button, button.current_button_type, 'on')
                elif button.device == self and button.select_page != page:
                    button.update_feedback(self.app, button, button.current_button_type, 'off')
                else:
                    button.update_feedback(self.app, button, button.current_button_type, 'off')
                    button.request_update()

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