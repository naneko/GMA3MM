import enum
import logging
import os
import threading
import time
from typing import Literal
import uuid
from multiprocessing.pool import ThreadPool
from pathlib import Path
from time import sleep

import mido
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

# os.add_dll_directory(Path(__file__).parent)

class App:
    """
    Main GMA3MM app class
    """

    def __init__(self, osc_client_ip: str, osc_client_port: int, osc_server_ip: str, osc_server_port: int):
        """GMA3MM app class

        Args:
            osc_client_ip (str): OSC Client IP address (Sends OSC messages to GMA3)
            osc_client_port (int): OSC Client Port
            osc_server_ip (str): OSC Server IP address (Receives OSC messages from GMA3)
            osc_server_port (int): OSC Server Port
        """
        self.OSC = self.OSCHandler(osc_client_ip, osc_client_port, osc_server_ip, osc_server_port)
        self.MIDI = self.MIDIHandler(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.buttons = []
        self.encoders = []
        self.faders = []
        self.log.info("Initialized GMA3MM")

    def start(self):
        """
        Starts GMA3MM app
        """
        # Workaround allows GMA3MM to bind to port 8001 by telling GMA3 to disable OSC output for a second and then turning back on so it can't bind to the port itself
        self.OSC.send("/cmd", 'Set OSC Property "EnableOutput" false')
        sleep(1)
        threading.Thread(target=self.MIDI.start).start()
        threading.Thread(target=self.OSC.start).start()
        threading.Thread(target=self.ButtonType.blink, args=self).start()
        self.OSC.send("/cmd", 'Set OSC Property "EnableOutput" true')

    def register_fader(self, device: 'App.MIDIHandler.Device', executor: int, signal: int, channel: int, latch: bool) -> 'App.Fader':
        fader = self.Fader(self, device, signal, channel, executor, latch=latch)
        self.faders.append(fader)
        return fader

    def register_button(self, device: 'App.MIDIHandler.Device', executor: int, signal: int, channel: int) -> 'App.Button':
        button = self.Button(self, device, signal, channel, executor=executor)
        self.buttons.append(button)
        return button

    def register_page_button(self, device: 'App.MIDIHandler.Device', page: int, signal: int, channel: int) -> 'App.Button':
        button = self.Button(self, device, signal, channel, select_page=page)
        self.buttons.append(button)
        return button
    
    def get_faders(self, executor: int) -> list['App.Fader']:
        return [f for f in self.faders if f.executor == executor]
    
    def get_buttons(self, executor: int) -> list['App.Button']:
        return [b for b in self.buttons if b.executor == executor]

    def start(self):
        """
        Starts GMA3MM app
        """
        # Workaround allows GMA3MM to bind to port 8001 by telling GMA3 to disable OSC output for a second and then turning back on so it can't bind to the port itself
        self.OSC.send("/cmd", 'Set OSC Property "EnableOutput" false')
        sleep(1)
        threading.Thread(target=self.MIDI.start).start()
        threading.Thread(target=self.OSC.start).start()
        threading.Thread(target=self.ButtonType.blink, args=self).start()
        self.OSC.send("/cmd", 'Set OSC Property "EnableOutput" true')

    class MIDIHandler:
        """
        Handles MIDI input and output
        """

        def __init__(self, app: 'App'):
            self.log = logging.getLogger(self.__class__.__name__)
            self.app = app
            self.devices = []
            self.midi_routes = {}
            self.device_search = []
            self.log.info("Connected output MIDI devices: " + ", ".join(mido.get_output_names()))
            self.log.info("Connected input MIDI devices: " + ", ".join(mido.get_input_names()))

        class Device:
            """
            Represents a MIDI device
            """

            def __init__(self, app, input_name: str, output_name: str):
                self.app = app
                self.log = logging.getLogger(self.__class__.__name__)
                self.input_name = input_name
                self.output_name = output_name
                self.input = None
                self.output = None
                self.connected = False
                self.connecting = False
                self.page = 0

                self.connect()

            def connect(self):
                if not self.connecting:
                    with ThreadPool():
                        self.connecting = True
                        while True:
                            try:
                                self.app.log.info(f"Connecting to MIDI device | Input Name: {self.input_name} | Output Name: {self.output_name}")
                                self.input = mido.open_input(self.input_name)
                                self.output = mido.open_output(self.output_name)
                                self.connected = True
                                self.log.info(f"Connected to MIDI device | Input Name: {self.input_name} | Output Name: {self.output_name}")
                                self.set_page(self.page) # Initialize the page
                                self.connecting = False
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

            def set_page(self, page: int):
                self.page = page
                for button in self.app.buttons:
                    if button.device == self and button.select_page == page:
                        button.update_feedback(button, button.current_button_type, 'on')
                    elif button.device == self and button.select_page != page:
                        button.update_feedback(button, button.current_button_type, 'off')
                    else:
                        button.update_feedback(button, button.current_button_type, 'off')
                        button.request_update()

        def add_device(self, input_device_name: str, output_device_name: str):
            """
            Add MIDI input and output devices based on name. Check first log message for currently connected device names.

            :param output_device_name: Output device name
            :param input_device_name: Input device name
            """
            self.log.debug("Adding MIDI device | Input Name: " + input_device_name + " | Output Name: " + output_device_name)
            self.devices.append(self.Device(self.app, input_device_name, output_device_name))
            self.midi_routes[input_device_name] = {}
            for message_type in self.MIDIMessageTypes:
                self.midi_routes[input_device_name][message_type.value] = {}
                for i in range(0, 16):
                    self.midi_routes[input_device_name][message_type.value][i] = {}
        
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

        MIDIMessageTypes = enum.Enum('MIDIMessageTypes', [
            'note_off',
            'note_on',
            'polytouch', 
            'control_change',
            'program_change',
            'aftertouch',
            'pitchwheel',
            'sysex',
            'quarter_frame', 
            'songpos',
            'song_select',
            'tune_request',
            'clock',
            'start',
            'continue', 
            'stop',
            'active_sensing',
            'reset'
        ])

        def route(
            self, device: 'Device', msg_types: MIDIMessageTypes, start_channel: int, end_channel: int, signals: list[int]
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
                for msg_type in msg_types:
                    for i in range(start_channel, end_channel):
                        for signal in signals:
                            self.midi_routes[device.input_name][msg_type.value][i][signal] = func

            return wrapper
        
        def add_route(self, device: 'Device', str, msg_type: MIDIMessageTypes, channel: int, signal: int, func: callable, overwrite: bool = False):
            """
            Map a route directly without a decorator
            :param device:
            :param msg_type: MIDI message type (see MIDIMessageTypes enum)
            :param channel: MIDI channel
            :param signal: MIDI signal to watch (such as a note or control change)
            :param func: Function to execute
            """
            # TODO: Check for overwrite
            self.midi_routes[device.input_name][msg_type.value][channel][signal] = func

        def send_note(self, device: 'Device', msg_type: MIDIMessageTypes, channel: int, note: int, value: int):
            self.log.debug(f"Sending MIDI note | Device: {device.input_name} | Message Type: {msg_type} | Channel: {channel} | Note: {note} | Value: {value}")
            device.output.send(mido.Message(msg_type.value, channel=channel, note=note, velocity=value))

        def send_control_change(self, device: 'Device', msg_type: MIDIMessageTypes, channel: int, control: int, value: int):
            self.log.debug(f"Sending MIDI control change | Device: {device.input_name} | Message Type: {msg_type} | Channel: {channel} | Control: {control} | Value: {value}")
            device.output.send(mido.Message(msg_type.value, channel=channel, control=control, value=value))

        def send_bytes(self, device: 'Device', bytes: bytes):
            self.log.debug(f"Sending MIDI bytes | Device: {device.input_name} | Bytes: {bytes}")
            device.output.send(mido.Message.from_bytes(bytes))
        
        def start(self):
            """
            Blocking MIDI router that routes to route_midi decorated functions
            """
            for device in self.devices:
                self.log.debug(f"Starting MIDI thread for device | Device: {device.input_name}")
                threading.Thread(target=self._device_thread, args=(self, device)).start()
            self.log.info("MIDI Threads Started")

        @staticmethod
        def _device_thread(midi_handler, device: 'Device'):
            # Yes, this is the best way to do this. Try/except will hide key errors in the callback functions. Ask me how I know.
            for msg in device.input:
                midi_handler.log.debug(f"Received MIDI message | Device: {device.input_name} | Message: {msg}")
                if msg.is_cc():
                    if msg.type in midi_handler.midi_routes[device.input_name]:
                        if msg.channel in midi_handler.midi_routes[device.input_name][msg.type]:
                            if msg.control in midi_handler.midi_routes[device.input_name][msg.type][msg.channel]:
                                midi_handler.midi_routes[device.input_name][msg.type][msg.channel][msg.control](msg)
                elif msg.type in midi_handler.midi_routes[device.input_name]:
                    if msg.channel in midi_handler.midi_routes[device.input_name][msg.type]:
                        if msg.note in midi_handler.midi_routes[device.input_name][msg.type][msg.channel]:
                            midi_handler.midi_routes[device.input_name][msg.type][msg.channel][msg.note](msg)

    class OSCHandler:
        """
        Handles OSC input and output
        """

        log = logging.getLogger()

        client_ip = None
        client_port = None
        server_ip = None
        server_port = None
        OSC = None
        dispatcher = Dispatcher()

        def __init__(self, client_ip: str, client_port: int, server_ip: str, server_port: int):
            self.client_ip = client_ip or "10.1.1.100"
            self.client_port = client_port or 8000
            self.server_ip = server_ip or "10.1.1.100"
            self.server_port = server_port or 8001

        def route(self, address: str) -> callable:
            """
            Decorator to execute a function via OSC
            :param address: OSC address
            :return: Wrapper function
            """

            def wrapper(func):
                self.dispatcher.map(address, func)
                return func

            return wrapper

        def add_route(self, address: str, func: callable):
            """
            Map a route directly without a decorator
            :param address: OSC address
            :param func: Function to execute
            """
            self.dispatcher.map(address, func)
        
        def start(self):
            """
            Blocking OSC server
            """
            self.log.info(
                "OSC Thread Started"
            )
            server = ThreadingOSCUDPServer((self.server_ip, self.server_port), self.dispatcher)
            server.serve_forever()

        def send(self, address: str, message: str):
            """
            Send OSC message to GMA3

            :param address: OSC address
            :param message: OSC message
            """
            self.OSC.send_message(address, message)

    class FaderType:
        """
        Define the behavior of a type of MIDI fader or encoder
        """
        
        button_types = enum.Enum('button_types', [
            '>>>',
            '<<<',
            'Black',
            'DoubleSpeed', 
            'Flash',
            'Go+',
            'Go-',
            'Goto',
            'HalfSpeed',
            'Kill',
            'LearnSpeed',
            'Load',
            'On',
            'Off', 
            'Pause',
            'Rate1',
            'Select',
            'SelectFixtures',
            'Speed1',
            'Swap',
            'Temp',
            'Toggle',
            'Top'
        ])

        def __init__(self, app: 'App'):
            self.app = app
            self.off_mode = 0
            self.off_value = 0
            self.default_inactive_mode = 0
            self.default_active_mode = 1
            self.default_highlight_mode = None
            self.default_highlight_value = None
            self.inactive_mode = {} # Inactive mode for specific gma encoder types (based on gma button type)
            self.active_mode = {} # Active mode for specific gma encoder types (based on gma button type)
            self.highlight_mode = {} # Highlight mode for specific gma encoder types (based on gma button type)
            self.highlight_value = {} # Highlight value for specific gma encoder types (based on gma button type)
            self.state = 'off'

        def set_off(self, mode_value: int, value: int) -> 'App.FaderType':
            self.off_mode = mode_value
            self.off_value = value
            return self
        
        def get_off(self) -> tuple[int, int]:
            return self.off_mode, self.off_value
        
        def set_default_inactive_mode(self, value: int) -> 'App.FaderType':
            self.default_inactive_mode = value
            return self
        
        def set_default_active_mode(self, value: int) -> 'App.FaderType':
            self.default_active_mode = value
            return self
        
        def set_inactive_mode(self, gma_type: button_types, value: int) -> 'App.FaderType':
            self.inactive_mode[gma_type] = value
            return self
        
        def get_inactive_mode(self, gma_type: button_types) -> int:
            if gma_type in self.inactive_mode:
                return self.inactive_mode[gma_type]
            else:
                return self.default_inactive_mode
            
        def set_active_mode(self, gma_type: button_types, value: int) -> 'App.FaderType':
            self.active_mode[gma_type] = value
            return self
        
        def get_active_mode(self, gma_type: button_types) -> int:
            if gma_type in self.active_mode:
                return self.active_mode[gma_type]
            else:
                return self.default_active_mode
        
        def set_default_highlight(self, mode_value: int, value: int) -> 'App.FaderType':
            self.default_highlight_mode = mode_value
            self.default_highlight_value = value
            return self
        
        def set_highlight(self, gma_type: button_types, mode_value: int, value: int) -> 'App.FaderType':
            self.highlight_mode[gma_type] = mode_value
            self.highlight_value[gma_type] = value
            return self
        
        def get_highlight(self, gma_type: button_types) -> tuple[int, int]:
            if gma_type in self.highlight_mode:
                return self.highlight_mode[gma_type], self.highlight_value[gma_type]
            else:
                return self.default_highlight_mode, self.default_highlight_value
            
        @classmethod
        def update_mode(cls, app: 'App', fader: 'App.Fader', gma_type: button_types, state: Literal['off', 'inactive', 'active', 'highlight']):
            match state:
                case 'off':
                    fader.state = 'off'
                    app.MIDI.send_control_change(
                        fader.device.output_name,
                        app.MIDI.MIDIMessageTypes.control_change,
                        fader.feedback_config_channel,
                        fader.feedback_config_signal,
                        fader.get_off()[0]
                    )
                    app.MIDI.send_control_change(
                        fader.device.output_name,
                        app.MIDI.MIDIMessageTypes.control_change,
                        fader.channel,
                        fader.signal,
                        fader.get_off()[1]
                    )
                case 'inactive':
                    fader.state = 'inactive'
                    app.MIDI.send_control_change(
                        fader.device.output_name,
                        app.MIDI.MIDIMessageTypes.control_change,
                        fader.feedback_config_channel,
                        fader.feedback_config_signal,
                        fader.get_inactive_mode(gma_type)
                    )
                case 'active':
                    fader.state = 'active'
                    app.MIDI.send_control_change(
                        fader.device.output_name,
                        app.MIDI.MIDIMessageTypes.control_change,
                        fader.channel,
                        fader.feedback_config_signal,
                        fader.get_active_mode(gma_type)
                    )
                case 'highlight':
                    with ThreadPool():
                        for i in range(0, 2):
                            app.MIDI.send_control_change(
                                fader.device.output_name,
                                app.MIDI.MIDIMessageTypes.control_change,
                                fader.feedback_config_channel,
                                fader.feedback_config_signal,
                                fader.get_off()[0]
                            )
                            app.MIDI.send_control_change(
                                fader.device.output_name,
                                app.MIDI.MIDIMessageTypes.control_change,
                                fader.channel,
                                fader.signal,
                                fader.get_off()[1]
                            )
                            sleep(0.05)
                            app.MIDI.send_control_change(
                                fader.device.output_name,
                                app.MIDI.MIDIMessageTypes.control_change,
                                fader.feedback_config_channel,
                                fader.feedback_config_signal,
                                fader.get_highlight(gma_type)[0]
                            )
                            app.MIDI.send_control_change(
                                fader.device.output_name,
                                app.MIDI.MIDIMessageTypes.control_change,
                                fader.channel,
                                fader.signal,
                                fader.get_highlight(gma_type)[1]
                            )
                            sleep(0.05)
                        fader.update_mode(app, fader, gma_type, fader.state)

    class Fader(FaderType):
        def __init__(self, app: 'App', device: 'App.MIDIHandler.Device', signal: int, channel: int, executor: int, latch: bool = True):
            super().__init__(app)
            self.app = app
            self.uid = str(uuid.uuid4().int)
            self.device = device
            self.signal = signal
            self.channel = channel
            self.feedback_config_signal = signal
            self.feedback_config_channel = channel
            self.executor = executor
            self.latch = latch
            self.old_value = -1
            self.value = -1
            self.gma_value = -1

            self.app.MIDI.add_route(device, self.app.MIDI.MIDIMessageTypes.control_change, channel, signal, self.trigger)

        def set_type(self, fader_type: 'App.FaderType') -> 'App.Fader':
            self.off_mode = fader_type.off_mode
            self.off_value = fader_type.off_value
            self.default_inactive_mode = fader_type.default_inactive_mode 
            self.default_active_mode = fader_type.default_active_mode
            self.default_highlight_mode = fader_type.default_highlight_mode
            self.default_highlight_value = fader_type.default_highlight_value
            self.inactive_mode = fader_type.inactive_mode
            self.active_mode = fader_type.active_mode
            self.highlight_mode = fader_type.highlight_mode
            self.highlight_value = fader_type.highlight_value
            return self

        def trigger(self, msg):
            value = remap(msg.value, 0, 127, 0, 100)
            self.value = value
            if self.gma_value != -1 and self.latch: 
                if (
                    self.gma_value > self.old_value
                ):  # If GMA3 value is greater than cached APC fader value, meaning the fader is under the latch
                    if (
                        self.gma_value > value
                    ):  # Then check if the current fader value is still less than the GMA3 value
                        # print(f'Fader {ch} at {value} | Waiting for latch above {State.fader_values[ch]}', flush=True)
                        return
                # Fader was over latch
                elif self.gma_value < self.old_value:
                    if self.gma_value < value:  # Still over latch?
                        # print(f'Fader {ch} at {value} | Waiting for latch below {State.fader_values[ch]}', flush=True)
                        return
            self.gma_value = -1
            # print(f'/Page{State.selected_page + 1}/Fader{ch} | {value}', flush=True)
            self.app.OSC.send(f"/Page{self.device.page + 1}/Fader{self.executor}", value)
            self.app.MIDI.send_control_change(self.device, self.app.MIDI.MIDIMessageTypes.control_change, self.channel, self.signal, int(remap(value, 0, 100, 0, 127)))

            # Update all associated faders
            associated_faders = self.app.get_faders(self.executor)
            for fader in associated_faders:
                fader.value = value
                fader.gma_value = -1
                self.app.MIDI.send_control_change(fader.device, self.app.MIDI.MIDIMessageTypes.control_change, fader.channel, fader.signal, int(remap(value, 0, 100, 0, 127)))
            
            # Store the current time of the value change
            self._last_value_change = time.time()
            
            # To avoid bogging down MA, wait to update buttons and faders until fader values have stopped updating for 0.25s
            def delayed_update():
                while True:
                    current_time = time.time()
                    if current_time - self._last_value_change >= 0.25:
                        associated_buttons = self.app.get_buttons(self.executor)
                        for button in associated_buttons:
                            button.request_update()
                        associated_faders = self.app.get_faders(self.executor)
                        for fader in associated_faders:
                            fader.request_update()
                        break
                    sleep(0.05)

            threading.Thread(target=delayed_update, daemon=True).start()
        
        def request_update(self):
            with ThreadPool():
                sleep(0.1)
                with open(Path("get_exec.lua"), "r") as f:
                    lua = f.readlines()
                    self.app.OSC.send(
                        "/cmd",
                        "lua '"
                        + ";".join(lua).replace("[[exec]]", str(self.executor)).replace("[[uid]]", self.uid).replace("\n", "")
                        + "'",
                    )
        
        def gma_update(self, address: str, *args):
            index, button_type, fader_type, fader_value, cue_number = args
            self.gma_value = fader_value
            self.old_value = self.value
            fader_value = int(remap(fader_value, 0, 100, 0, 127))
            self.app.MIDI.send_control_change(self.device, self.app.MIDI.MIDIMessageTypes.control_change, self.channel, self.signal, fader_value)
            if fader_type:
                self.update_mode(self.app, self, button_type, 'inactive')
                self.state = 'inactive'
            else:
                self.update_mode(self.app, self, button_type, 'off')
                self.state = 'off'

        def set_feedback_config(self, signal: int, channel: int):
            self.feedback_config_signal = signal
            self.feedback_config_channel = channel

    class ButtonType:
        """
        Define the behavior of a type of MIDI button
        """
        
        button_types = enum.Enum('button_types', [
            '>>>',
            '<<<',
            'Black',
            'DoubleSpeed', 
            'Flash',
            'Go+',
            'Go-',
            'Goto',
            'HalfSpeed',
            'Kill',
            'LearnSpeed',
            'Load',
            'On',
            'Off', 
            'Pause',
            'Rate1',
            'Select',
            'SelectFixtures',
            'Speed1',
            'Swap',
            'Temp',
            'Toggle',
            'Top'
        ])

        blinking = []

        def __init__(self, app: 'App'):
            self.app = app
            self.default_off = 0 # Default off for all buttons of type
            self.default_on = 1 # Default on for all buttons of type
            self.on = {} # Feedback settings for specific gma button types
            self.pressed = {} # Pressed feedback for specific gma button types
            self.active = {} # Active feedback for specific gma button types
            self.blink_off = {} # Blink off for specific gma button types
            self.blink_on = {} # Blink on for specific gma button types

        def set_blink_off(self, gma_type: button_types, value: int) -> 'App.ButtonType':
            self.blink_off[gma_type] = value
            return self

        def set_blink_on(self, gma_type: button_types, value: int) -> 'App.ButtonType':
            self.blink_on[gma_type] = value
            return self
        
        def get_blink_on(self, gma_type: button_types) -> int:
            blink_on = self.blink_on.get(gma_type, None)
            active = self.active.get(gma_type, None)
            pressed = self.pressed.get(gma_type, None)
            default = self.default_on.get(gma_type, None)
            if blink_on:
                return blink_on
            elif active:
                return active
            elif pressed:
                return pressed
            elif default:
                return default
            else:
                return 1
        
        def get_blink_off(self, gma_type: button_types) -> int:
            blink_off = self.blink_off.get(gma_type, None)
            if blink_off:
                return blink_off
            else:
                return 0
            
        def set_default_off(self, value: int) -> 'App.ButtonType':
            self.default_off = value
            return self

        def set_default_on(self, value: int) -> 'App.ButtonType':
            self.default_on = value
            return self
        
        def get_off(self) -> int:
            return self.default_off
        
        def set_on(self, gma_type: button_types, value: int) -> 'App.ButtonType':
            self.on[gma_type] = value
            return self
        
        def get_on(self, gma_type: button_types) -> int:
            if gma_type in self.on:
                return self.on[gma_type]
            else:
                return self.default_on

        def set_pressed(self, gma_type: button_types, value: int) -> 'App.ButtonType':
            self.pressed[gma_type] = value
            return self
        
        def get_pressed(self, gma_type: button_types) -> int:
            if gma_type in self.pressed:
                return self.pressed[gma_type]
            else:
                return self.default_on

        def set_active(self, gma_type: button_types, value: int) -> 'App.ButtonType':
            self.active[gma_type] = value
            return self
        
        def get_active(self, gma_type: button_types) -> int:
            if gma_type in self.active:
                return self.active[gma_type]
            else:
                return self.default_on
        
        @classmethod
        def update_feedback(cls, app: 'App', button: 'App.Button', gma_type: button_types, state: Literal['off', 'on', 'pressed', 'active']):
            match state:
                case 'off':
                    if button.is_blinkable():
                        cls.stop_blink(button)
                    app.MIDI.send_note(
                        button.device.output_name,
                        app.MIDI.MIDIMessageTypes.note_on,
                        button.channel,
                        button.signal,
                        button.get_off()
                    )
                case 'on':
                    if button.is_blinkable():
                        cls.stop_blink(button)
                    app.MIDI.send_note(
                        button.device.output_name,
                        app.MIDI.MIDIMessageTypes.note_on,
                        button.channel,
                        button.signal,
                        button.get_on(gma_type)
                    )
                case 'pressed':
                    if button.is_blinkable():
                        cls.stop_blink(button)
                    app.MIDI.send_note(
                        button.device.output_name,
                        app.MIDI.MIDIMessageTypes.note_on,
                        button.channel,
                        button.signal,
                        button.get_pressed(gma_type)
                    )
                case 'active':
                    app.MIDI.send_note(
                        button.device.output_name,
                        app.MIDI.MIDIMessageTypes.note_on,
                        button.channel,
                        button.signal,
                        button.get_active(gma_type)
                    )
                    if button.is_blinkable():
                        cls.start_blink(button)

        @classmethod
        def start_blink(cls, button: 'App.Button'):
            if button not in cls.blinking:
                cls.blinking.append(button)

        @classmethod
        def stop_blink(cls, button: 'App.Button'):
            if button in cls.blinking:
                cls.blinking.remove(button)

        @classmethod
        def clear_blink(cls):
            cls.blinking = []

        @classmethod
        def blink(cls, app: 'App'):
            while True:
                for btn in cls.blinking:
                    app.MIDI.send_note(
                        btn.device.output_name,
                        app.MIDI.MIDIMessageTypes.note_on,
                        btn.channel,
                        btn.signal,
                        btn.get_blink_on(btn.current_button_type)
                    )
                sleep(0.5)
                for btn in cls.blinking:
                    app.MIDI.send_note(
                        btn.device.output_name,
                        app.MIDI.MIDIMessageTypes.note_on,
                        btn.channel,
                        btn.signal,
                        btn.get_blink_off(btn.current_button_type)
                    )

    class Button(ButtonType):
        def __init__(self, app: 'App', device: 'App.MIDIHandler.Device', signal: int, channel: int, executor: int = None, select_page = None):
            super().__init__(app)
            self.uid = str(uuid.uuid4().int)
            self.device = device
            self.signal = signal
            self.channel = channel
            self.executor = executor
            self.select_page = select_page
            self.current_button_type = None

            self.app.OSC.add_route(self.uid, self.gma_update)
            self.app.MIDI.add_route(device, self.app.MIDI.MIDIMessageTypes.note_on, channel, signal, self.note_on)
            self.app.MIDI.add_route(device, self.app.MIDI.MIDIMessageTypes.note_off, channel, signal, self.note_off)

            self.request_update()

        def set_type(self, button_type: 'App.ButtonType') -> 'App.Button':
            self.default_off = button_type.default_off
            self.default_feedback = button_type.default_on
            self.off = button_type.off
            self.feedback = button_type.on
            self.pressed_feedback = button_type.pressed 
            self.active_feedback = button_type.active
            self.blink_off = button_type.blink_off
            self.blink_on = button_type.blink_on
            return self

        def note_on(self, msg: mido.Message):
            if self.executor:
                self.app.OSC.send(f"/Page{self.device.page + 1}/Key{self.executor}", 1)
            if self.select_page:
                self.device.set_page(self.select_page)
            associated_faders = self.app.get_faders(self.executor)
            for fader in associated_faders:
                fader.update_mode(self.app, fader, self.current_button_type, 'highlight')
        
        def note_off(self, msg: mido.Message):
            if self.executor:
                self.app.OSC.send(f"/Page{self.device.page + 1}/Key{self.executor}", 0)
                self.request_update()
            associated_buttons = self.app.get_buttons(self.executor)
            for button in associated_buttons:
                button.request_update()

        def gma_update(self, address: str, *args):
            index, button_type, fader_type, fader_value, cue_number = args
            self.current_button_type = button_type
            associated_faders = self.app.get_faders(self.executor)
            if self.is_blinkable():
                if cue_number != "None":
                    self.start_blink(self)
                    for fader in associated_faders:
                        fader.update_mode(self.app, fader, button_type, 'active')
                else:
                    self.stop_blink(self)
                    for fader in associated_faders:
                        fader.update_mode(self.app, fader, button_type, 'inactive')
            elif button_type:
                if cue_number != "None":
                    self.update_feedback(self, button_type, 'active')
                    for fader in associated_faders:
                        fader.update_mode(self.app, fader, button_type, 'active')
                else:
                    self.update_feedback(self, button_type, 'on')
                    for fader in associated_faders:
                        fader.update_mode(self.app, fader, button_type, 'inactive')
            else:
                self.update_feedback(self, button_type, 'off')


        def is_blinkable(self) -> bool:
            return self.blink_on.get(self.current_button_type, None) != None or self.blink_off.get(self.current_button_type, None) != None

        def request_update(self):
            if self.select_page:
                return
            with ThreadPool():
                sleep(0.1)
                with open(Path("get_exec.lua"), "r") as f:
                    lua = f.readlines()
                    self.app.OSC.send(
                        "/cmd",
                        "lua '"
                        + ";".join(lua).replace("[[exec]]", str(self.executor)).replace("[[uid]]", self.uid).replace("\n", "")
                        + "'",
                    )

def remap(old_val, old_min, old_max, new_min, new_max) -> float:
    """
    Remap values proportionally from existing range to target range

    :param old_val: Value to be remapped
    :param old_min: Min value for old_val
    :param old_max: Max value for old_val
    :param new_min: New min value
    :param new_max: New max value
    :return: Remapped value
    """
    return (new_max - new_min) * (old_val - old_min) / (old_max - old_min) + new_min
