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

    # TODO: Update get_exec.lua to notify a page doesn't exist page and update state of controller accordingly

    def __init__(self, app: 'App'):
        self._log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._app: 'App' = app
        self._devices: list[Device] = []
        self._midi_routes: dict[str, MIDIMessageTypes, int, int, callable] = {}
        self._lock = threading.Lock()

        self._log.info("Connected output MIDI devices: " + ", ".join(mido.get_output_names()))
        self._log.info("Connected input MIDI devices: " + ", ".join(mido.get_input_names()))

    def add_device(self, input_device_name: str, output_device_name: str):
        """
        Add MIDI input and output devices based on name. Check first log message for currently connected device names.

        :param output_device_name: Output device name
        :param input_device_name: Input device name
        """
        self._log.debug("Adding MIDI device | Input Name: " + input_device_name + " | Output Name: " + output_device_name)
        new_device = Device(self._app, input_device_name, output_device_name)
        with self._lock:
            self._devices.append(new_device)
            self._midi_routes[input_device_name] = {}
            for message_type in MIDIMessageTypes:
                self._midi_routes[input_device_name][message_type.value] = {}
                for i in range(0, 16):
                    self._midi_routes[input_device_name][message_type.value][i] = {}

            return new_device
    
    def get_device(self, input_device_name: str = None, output_device_name: str = None) -> 'Device':
        """
        Get MIDI input and output devices based on name. Only input or output name is needed. If both are provided, will search by input first.

        :param output_device_name: Output device name
        :param input_device_name: Input device name
        """
        if input_device_name:
            for device in self._devices:
                if device._input_name == input_device_name:
                    device._connect()
                    return device
        elif output_device_name:
            for device in self._devices:
                if device._output_name == output_device_name:
                    device._connect()
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
            with self._lock:
                for msg_type in msg_types:
                    for i in range(start_channel, end_channel):
                        for signal in signals:
                            self._log.debug(f"Adding MIDI route to {func.__name__} | Device: {device._input_name} | Message Type: {msg_type} | Channel: {i} | Signal: {signal}")
                            self._midi_routes[device._input_name][msg_type][i][signal] = func

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
        with self._lock:
            self._log.debug(f"Adding MIDI route to {func.__name__} | Device: {device._input_name} | Message Type: {msg_type} | Channel: {channel} | Signal: {signal}")
            self._midi_routes[device._input_name][msg_type.value][channel][signal] = func

    def send_note(self, device: 'Device', msg_type: 'MIDIMessageTypes', channel: int, note: int, value: int):
        self._log.debug(f"Sending MIDI note | Device: {device._input_name} | Message Type: {msg_type} | Channel: {channel} | Note: {note} | Value: {value}")
        device._output.send(mido.Message(msg_type.value, channel=channel, note=note, velocity=value))

    def send_control_change(self, device: 'Device', msg_type: 'MIDIMessageTypes', channel: int, control: int, value: int):
        self._log.debug(f"Sending MIDI control change | Device: {device._input_name} | Message Type: {msg_type} | Channel: {channel} | Control: {control} | Value: {value}")
        device._output.send(mido.Message(msg_type.value, channel=channel, control=control, value=value))

    def send_sysex(self, device: 'Device', sysex: list[bytes]):
        self._log.debug(f"Sending MIDI sysex | Device: {device._input_name} | Sysex: {sysex}")
        device._output.send(mido.Message('sysex', data=sysex))

    def send_bytes(self, device: 'Device', bytes: bytes):
        self._log.debug(f"Sending MIDI bytes | Device: {device._input_name} | Bytes: {bytes}")
        device._output.send(mido.Message.from_bytes(bytes))

    def start(self):
        """
        Start MIDI router
        """
        for device in self._devices:
            self._log.debug(f"Starting MIDI thread for device | Device: {device._input_name}")
            threading.Thread(target=self.__midi_device_thread, args=(self, device)).start()
            
    @staticmethod
    def __midi_device_thread(midi_handler: 'MIDIHandler', device: 'Device'):
        # Yes, this is the best way to do this. Try/except will hide key errors in the callback functions. Ask me how I know.
        midi_handler._log.info(f"Starting MIDI thread for device | Device: {device._input_name}")
        while True:
            if device._input:
                if device._connect_bytes:
                    device._app.MIDI.send_bytes(device, device._connect_bytes)
                for msg in device._input:
                    with midi_handler._lock:
                        if msg.is_cc():
                            midi_handler._log.debug(f"Received MIDI control change | Device: {device._input_name} | Message: {msg}")
                            if msg.type in midi_handler._midi_routes[device._input_name]:
                                if msg.channel in midi_handler._midi_routes[device._input_name][msg.type]:
                                    if msg.control in midi_handler._midi_routes[device._input_name][msg.type][msg.channel]:
                                        midi_handler._log.debug(f"Routing MIDI control change | Device: {device._input_name} | Message: {msg}")
                                        midi_handler._midi_routes[device._input_name][msg.type][msg.channel][msg.control](msg)
                        elif msg.type in midi_handler._midi_routes[device._input_name] and hasattr(msg, 'note'):
                            midi_handler._log.debug(f"Received MIDI message | Device: {device._input_name} | Message: {msg}")
                            if msg.channel in midi_handler._midi_routes[device._input_name][msg.type]:
                                if msg.note in midi_handler._midi_routes[device._input_name][msg.type][msg.channel]:
                                    midi_handler._log.debug(f"Routing MIDI message | Device: {device._input_name} | Message: {msg}")
                                    midi_handler._midi_routes[device._input_name][msg.type][msg.channel][msg.note](msg)

class Device:
    """
    Represents a MIDI device
    """

    def __init__(self, app, input_name: str, output_name: str):
        self._app: 'App' = app
        self._log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._input_name: str = input_name
        self._output_name: str = output_name
        self._input = None
        self._output = None
        self._connected: bool = False
        self._connecting = threading.Lock()
        self._lock = threading.Lock()
        self._page: int = 0
        self._connect_bytes = None

        self._log.debug(f"Initializing MIDI device | Input Name: {self._input_name} | Output Name: {self._output_name}")

        self._connect()

    def _connect(self):

        self._app._log.debug(f"Starting MIDI connection process | Input Name: {self._input_name} | Output Name: {self._output_name}")

        def connect_helper():
            with self._connecting:
                while True:
                    try:
                        self._app._log.debug(f"Connecting to MIDI device | Input Name: {self._input_name} | Output Name: {self._output_name}")
                        self._input = mido.open_input(self._input_name)
                        self._output = mido.open_output(self._output_name)
                        if self._connect_bytes:
                            self._output.send(mido.Message.from_bytes(self._connect_bytes))
                        self._connected = True
                        self._log.info(f"Connected to MIDI device | Input Name: {self._input_name} | Output Name: {self._output_name}")
                        self._set_page(self._page) # Initialize the page
                        break
                    except OSError:
                        if self._input:
                            self._input.close()
                        if self._output:
                            self._output.close()
                        self._input = None
                        self._output = None
                        self._connected = False
                        self._log.error(f"Could not connect to MIDI device. Trying again in 5 seconds... | Input Name: {self._input_name} | Output Name: {self._output_name}")
                    sleep(5)

            
        if not self._connecting.locked():
            threading.Thread(target=connect_helper).start()

    def _set_page(self, page: int):
        with self._lock:
            self._log.debug(f"Setting page | Device: {self._input_name} | Page: {page}")
            self._page = page
            for button in self._app._buttons:
                if button._device == self and button._select_page == page:
                    button._update_feedback(self._app, button, button._current_button_type, 'on')
                elif button._device == self and button._select_page != page and button._select_page != None:
                    button._update_feedback(self._app, button, button._current_button_type, 'off')
                else:
                    button._update_feedback(self._app, button, button._current_button_type, 'off')
                    button._request_update()
            for fader in self._app._faders:
                fader._current_fader_type = ''
                fader._update_mode(self._app, fader, None, 'off')
                fader._request_update()

    def set_connect_bytes(self, bytes: bytes):
        self._connect_bytes = bytes

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