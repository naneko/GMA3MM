import enum
import logging
from multiprocessing.pool import ThreadPool
from pathlib import Path
import threading
from time import sleep
import time
from typing import TYPE_CHECKING, Literal, TypedDict
import uuid
if TYPE_CHECKING:
    from midi_mapper.app import App, button_types
from midi_mapper.tools import remap, request_update
from midi_mapper.midi_handler import Device, MIDIMessageTypes

class FaderType:
    """
    Define the behavior of a type of MIDI fader or encoder
    """

    def __init__(self, app: 'App'):
        self.app: 'App' = app
        self.off_mode: int = 0
        self.off_value: int = 0
        self.default_inactive_mode: int = 0
        self.default_active_mode: int = 1
        self.default_highlight_mode: int = None
        self.default_highlight_value: int = None
        self.inactive_mode: dict['button_types', int] = {} # Inactive mode for specific gma encoder types (based on gma button type)
        self.active_mode: dict['button_types', int] = {} # Active mode for specific gma encoder types (based on gma button type)
        self.highlight_mode: dict['button_types', int] = {} # Highlight mode for specific gma encoder types (based on gma button type)
        self.highlight_value: dict['button_types', int] = {} # Highlight value for specific gma encoder types (based on gma button type)
        self.state: Literal['off', 'inactive', 'active', 'highlight'] = 'off'

    def set_off(self, mode_value: int, value: int) -> 'FaderType':
        self.off_mode = mode_value
        self.off_value = value
        return self
    
    def get_off(self) -> tuple[int, int]:
        return self.off_mode, self.off_value
    
    def set_default_inactive_mode(self, value: int) -> 'FaderType':
        self.default_inactive_mode = value
        return self
    
    def set_default_active_mode(self, value: int) -> 'FaderType':
        self.default_active_mode = value
        return self
    
    def set_inactive_mode(self, gma_type: 'button_types', value: int) -> 'FaderType':
        self.inactive_mode[gma_type] = value
        return self
    
    def get_inactive_mode(self, gma_type: 'button_types') -> int:
        if gma_type in self.inactive_mode:
            return self.inactive_mode[gma_type]
        else:
            return self.default_inactive_mode
        
    def set_active_mode(self, gma_type: 'button_types', value: int) -> 'FaderType':
        self.active_mode[gma_type] = value
        return self
    
    def get_active_mode(self, gma_type: 'button_types') -> int:
        if gma_type in self.active_mode:
            return self.active_mode[gma_type]
        else:
            return self.default_active_mode
    
    def set_default_highlight(self, mode_value: int, value: int) -> 'FaderType':
        self.default_highlight_mode = mode_value
        self.default_highlight_value = value
        return self
    
    def set_highlight(self, gma_type: 'button_types', mode_value: int, value: int) -> 'FaderType':
        self.highlight_mode[gma_type] = mode_value
        self.highlight_value[gma_type] = value
        return self
    
    def get_highlight(self, gma_type: 'button_types') -> tuple[int, int]:
        if gma_type in self.highlight_mode:
            return self.highlight_mode[gma_type], self.highlight_value[gma_type]
        else:
            return self.default_highlight_mode, self.default_highlight_value
        
    @classmethod
    def update_mode(cls, app: 'App', fader: 'Fader', gma_type: 'button_types', state: Literal['off', 'inactive', 'active', 'highlight']):
        match state:
            case 'off':
                fader.state = 'off'
                app.MIDI.send_control_change(
                    fader.device.output_name,
                    MIDIMessageTypes.control_change,
                    fader.feedback_config_channel,
                    fader.feedback_config_signal,
                    fader.get_off()[0]
                )
                app.MIDI.send_control_change(
                    fader.device.output_name,
                    MIDIMessageTypes.control_change,
                    fader.channel,
                    fader.signal,
                    fader.get_off()[1]
                )
            case 'inactive':
                fader.state = 'inactive'
                app.MIDI.send_control_change(
                    fader.device.output_name,
                    MIDIMessageTypes.control_change,
                    fader.feedback_config_channel,
                    fader.feedback_config_signal,
                    fader.get_inactive_mode(gma_type)
                )
            case 'active':
                fader.state = 'active'
                app.MIDI.send_control_change(
                    fader.device.output_name,
                    MIDIMessageTypes.control_change,
                    fader.channel,
                    fader.feedback_config_signal,
                    fader.get_active_mode(gma_type)
                )
            case 'highlight':
                def highlight_flash():
                    for i in range(0, 2):
                        app.MIDI.send_control_change(
                            fader.device.output_name,
                            MIDIMessageTypes.control_change,
                            fader.feedback_config_channel,
                            fader.feedback_config_signal,
                            fader.get_off()[0]
                        )
                        app.MIDI.send_control_change(
                            fader.device.output_name,
                            MIDIMessageTypes.control_change,
                            fader.channel,
                            fader.signal,
                            fader.get_off()[1]
                        )
                        sleep(0.05)
                        app.MIDI.send_control_change(
                            fader.device.output_name,
                            MIDIMessageTypes.control_change,
                            fader.feedback_config_channel,
                            fader.feedback_config_signal,
                            fader.get_highlight(gma_type)[0]
                        )
                        app.MIDI.send_control_change(
                            fader.device.output_name,
                            MIDIMessageTypes.control_change,
                            fader.channel,
                            fader.signal,
                            fader.get_highlight(gma_type)[1]
                        )
                        sleep(0.05)
                    fader.update_mode(app, fader, gma_type, fader.state) # Restore original state

                threading.Thread(target=highlight_flash).start()

class Fader(FaderType):
    def __init__(self, app: 'App', device: Device, signal: int, channel: int, executor: int, latch: bool = True):
        super().__init__(app)
        self.app: 'App' = app
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.uid: str = str(uuid.uuid4().int)
        self.device: Device = device
        self.signal: int = signal
        self.channel: int = channel
        self.feedback_config_signal: int = signal
        self.feedback_config_channel: int = channel
        self.executor: int = executor
        self.latch: bool = latch
        self.old_value: int = -1
        self.value: int = -1
        self.gma_value: int = -1

        self.app.OSC.add_route(f'/{self.uid}', self.gma_update)
        self.app.MIDI.add_route(device, MIDIMessageTypes.control_change, channel, signal, self.trigger)

    def set_type(self, fader_type: 'FaderType') -> 'Fader':
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
        self.app.MIDI.send_control_change(self.device, MIDIMessageTypes.control_change, self.channel, self.signal, int(remap(value, 0, 100, 0, 127)))

        # Update all associated faders
        associated_faders = self.app.get_faders(self.executor)
        for fader in associated_faders:
            fader.value = value
            fader.gma_value = -1
            self.app.MIDI.send_control_change(fader.device, MIDIMessageTypes.control_change, fader.channel, fader.signal, int(remap(value, 0, 100, 0, 127)))
        
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

        if not hasattr(self, '_update_thread') or not self._update_thread.is_alive():
            self._update_thread = threading.Thread(target=delayed_update)
            self._update_thread.start()
    
    def request_update(self):
            threading.Thread(target=request_update, args=(self,)).start()
    
    def gma_update(self, address: str, *args):
        self.log.debug(f"Fader update received | Executor: {self.executor} | {args}")
        index, button_type, fader_type, fader_value, cue_number = args
        self.gma_value = fader_value
        self.old_value = self.value
        fader_value = int(remap(fader_value, 0, 100, 0, 127))
        self.app.MIDI.send_control_change(self.device, MIDIMessageTypes.control_change, self.channel, self.signal, fader_value)
        if fader_type:
            self.update_mode(self.app, self, button_type, 'inactive')
            self.state = 'inactive'
        else:
            self.update_mode(self.app, self, button_type, 'off')
            self.state = 'off'

    def set_feedback_config(self, signal: int, channel: int):
        self.feedback_config_signal = signal
        self.feedback_config_channel = channel
