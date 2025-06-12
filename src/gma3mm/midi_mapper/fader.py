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
    from midi_mapper.app import App, ButtonTypes
from midi_mapper.tools import delayed_update, encoder_minus, encoder_plus, remap, request_update
from midi_mapper.midi_handler import Device, MIDIMessageTypes

class FaderType:
    """
    Define the behavior of a type of MIDI fader or encoder
    """

    def __init__(self, app: 'App'):
        """
        Args:
            app (App): GMA3MM App instance
        """
        self._app: 'App' = app
        self._off_mode: int = 0
        self._off_value: int = 0
        self._default_inactive_mode: int = 0
        self._default_active_mode: int = 1
        self._default_highlight_mode: int = None
        self._default_highlight_value: int = None
        self._inactive_mode: dict['ButtonTypes', int] = {} # Inactive mode for specific gma encoder types (based on gma button type)
        self._active_mode: dict['ButtonTypes', int] = {} # Active mode for specific gma encoder types (based on gma button type)
        self._highlight_mode: dict['ButtonTypes', int] = {} # Highlight mode for specific gma encoder types (based on gma button type)
        self._highlight_value: dict['ButtonTypes', int] = {} # Highlight value for specific gma encoder types (based on gma button type)
        self._state: Literal['off', 'inactive', 'active'] = 'off'

    def set_off(self, mode_value: int, value: int) -> 'FaderType':
        """Set the off mode and value for the fader's feedback

        Args:
            mode_value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.
            value (int): The MIDI value to send for the respective fader when it is off

        Returns:
            FaderType: self for chaining
        """
        self._off_mode = mode_value
        self._off_value = value
        return self
    
    def get_off(self) -> tuple[int, int]:
        """Get the off mode and value for the fader's feedback

        Returns:
            tuple[int, int]: off mode, off value
        """
        return self._off_mode, self._off_value
    
    def set_default_inactive_mode(self, value: int) -> 'FaderType':
        """Set the default inactive mode for the fader type. This is the fader's behavior when a GMA3 executor is inactive.

        Args:
            value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.

        Returns:
            FaderType: self for chaining
        """
        self._default_inactive_mode = value
        return self
    
    def set_default_active_mode(self, value: int) -> 'FaderType':
        """Set the default active mode for the fader type. This is the fader's behavior when a GMA3 executor is active.

        Args:
            value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.

        Returns:
            FaderType: self for chaining
        """
        self._default_active_mode = value
        return self
    
    def set_inactive_mode(self, gma_type: 'ButtonTypes', value: int) -> 'FaderType':
        """Set the inactive mode for a specific GMA3 executor button type

        Args:
            gma_type (ButtonTypes): GMA3 executor button type
            value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.

        Returns:
            FaderType: self for chaining
        """
        self._inactive_mode[gma_type] = value
        return self
    
    def get_inactive_mode(self, gma_type: 'ButtonTypes') -> int:
        """Get the inactive mode for a specific GMA3 executor button type

        Args:
            gma_type (ButtonTypes): GMA3 executor button type

        Returns:
            int: MIDI Mode value
        """
        if gma_type in self._inactive_mode:
            return self._inactive_mode[gma_type]
        else:
            return self._default_inactive_mode
        
    def set_active_mode(self, gma_type: 'ButtonTypes', value: int) -> 'FaderType':
        """Set the active mode for a specific GMA3 executor button type

        Args:
            gma_type (ButtonTypes): GMA3 executor button type
            value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.

        Returns:
            FaderType: self for chaining
        """
        self._active_mode[gma_type] = value
        return self
    
    def get_active_mode(self, gma_type: 'ButtonTypes') -> int:
        """Get the active mode for a specific GMA3 executor button type

        Args:
            gma_type (ButtonTypes): GMA3 executor button type

        Returns:
            int: MIDI Mode value
        """
        if gma_type in self._active_mode:
            return self._active_mode[gma_type]
        else:
            return self._default_active_mode
    
    def set_default_highlight(self, mode_value: int, value: int) -> 'FaderType':
        """Set the default highlight mode and value for the fader's feedback. The highlight is a brief flashing animation that occurs when an associated button is pressed to let you know which fader or knob is associated with that button.

        Args:
            mode_value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.
            value (int): The MIDI value to send for the respective fader when it is highlighted

        Returns:
            FaderType: self for chaining
        """
        self._default_highlight_mode = mode_value
        self._default_highlight_value = value
        return self
    
    def set_highlight(self, gma_type: 'ButtonTypes', mode_value: int, value: int) -> 'FaderType':
        """Set the highlight mode and value for a specific GMA3 executor button type. The highlight is a brief flashing animation that occurs when an associated button is pressed to let you know which fader or knob is associated with that button.

        Args:
            gma_type (ButtonTypes): GMA3 executor button type
            mode_value (int): MIDI value for the mode. For example, a knob may have an off, panning, and volume style of feedback as potential modes.
            value (int): The MIDI value to send for the respective fader when it is highlighted

        Returns:
            FaderType: self for chaining
        """
        self._highlight_mode[gma_type] = mode_value
        self._highlight_value[gma_type] = value
        return self
    
    def get_highlight(self, gma_type: 'ButtonTypes') -> tuple[int, int]:
        """Get the highlight mode and value for a specific GMA3 executor button type. The highlight is a brief flashing animation that occurs when an associated button is pressed to let you know which fader or knob is associated with that button.

        Args:
            gma_type (ButtonTypes): GMA3 executor button type

        Returns:
            tuple[int, int]: highlight mode, highlight value
        """
        if gma_type in self._highlight_mode:
            return self._highlight_mode[gma_type], self._highlight_value[gma_type]
        else:
            return self._default_highlight_mode, self._default_highlight_value
        
    @classmethod
    def _update_mode(cls, app: 'App', fader: 'Fader', gma_type: 'ButtonTypes', state: Literal['off', 'inactive', 'active', 'highlight', 'super_highlight']) -> None:
        match state:
            case 'off':
                fader._state = 'off'
                app.MIDI.send_control_change(
                    fader._device,
                    MIDIMessageTypes.control_change,
                    fader._feedback_config_channel,
                    fader._feedback_config_signal,
                    fader.get_off()[0]
                )
                app.MIDI.send_control_change(
                    fader._device,
                    MIDIMessageTypes.control_change,
                    fader._channel,
                    fader._signal,
                    fader.get_off()[1]
                )
            case 'inactive':
                fader._state = 'inactive'
                app.MIDI.send_control_change(
                    fader._device,
                    MIDIMessageTypes.control_change,
                    fader._feedback_config_channel,
                    fader._feedback_config_signal,
                    fader.get_inactive_mode(gma_type)
                )
            case 'active':
                fader._state = 'active'
                app.MIDI.send_control_change(
                    fader._device,
                    MIDIMessageTypes.control_change,
                    fader._channel,
                    fader._feedback_config_signal,
                    fader.get_active_mode(gma_type)
                )
            case 'highlight':
                def highlight_flash():
                    if fader.get_highlight(gma_type)[0] is None or fader.get_highlight(gma_type)[1] is None:
                        return
                    for i in range(0, 2):
                        app.MIDI.send_control_change(
                            fader._device,
                            MIDIMessageTypes.control_change,
                            fader._feedback_config_channel,
                            fader._feedback_config_signal,
                            fader.get_off()[0]
                        )
                        app.MIDI.send_control_change(
                            fader._device,
                            MIDIMessageTypes.control_change,
                            fader._channel,
                            fader._signal,
                            fader.get_off()[1]
                        )
                        sleep(0.05)
                        app.MIDI.send_control_change(
                            fader._device,
                            MIDIMessageTypes.control_change,
                            fader._feedback_config_channel,
                            fader._feedback_config_signal,
                            fader.get_highlight(gma_type)[0]
                        )
                        app.MIDI.send_control_change(
                            fader._device,
                            MIDIMessageTypes.control_change,
                            fader._channel,
                            fader._signal,
                            fader.get_highlight(gma_type)[1]
                        )
                        sleep(0.05)
                    fader._update_mode(app, fader, gma_type, fader._state) # Restore original state
                    if fader._value >= 0:
                        app.MIDI.send_control_change(
                            fader._device,
                            MIDIMessageTypes.control_change,
                            fader._channel,
                            fader._signal,
                            int(remap(fader._value, 0, 100, 1, 127))
                        )

                threading.Thread(target=highlight_flash).start()
            case 'super_highlight':
                app.MIDI.send_control_change(
                    fader._device,
                    MIDIMessageTypes.control_change,
                    fader._feedback_config_channel,
                    fader._feedback_config_signal,
                    fader.get_highlight(gma_type)[0]
                )
                app.MIDI.send_control_change(
                    fader._device,
                    MIDIMessageTypes.control_change,
                    fader._channel,
                    fader._signal,
                    fader.get_highlight(gma_type)[1]
                )

class Fader(FaderType):
    _last_value_change: float = 0

    def __init__(self, app: 'App', device: Device, signal: int, channel: int, executor: int, latch: bool = True, encoder_layer_number: int = None):
        """
        Args:
            app (App): GMA3MM App instance
            device (Device): MIDI Device to register fader to
            signal (int): MIDI control signal to listen for
            channel (int): MIDI channel to listen on
            executor (int): GMA3 Executor to control
            latch (bool): On page change, hold the value that the fader controls until the fader equals that value. This will prevent the fader from jumping to the new value when the page is changed.
            encoder_layer_number (int): Only works on knobs. When encoder layer is toggled, the encoder this knob controls.
        """
        super().__init__(app)
        self._app: 'App' = app
        self._log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._uid: str = str(uuid.uuid4().int)
        self._device: Device = device
        self._signal: int = signal
        self._channel: int = channel
        self._feedback_config_signal: int = signal
        self._feedback_config_channel: int = channel
        self._executor: int = executor
        self._latch: bool = latch
        self._current_fader_type = None
        self._old_value: int = -1
        self._value: int = -1
        self._gma_value: int = -1
        self._encoder_layer_number: int = encoder_layer_number
        self._encoder_value_cache: int = 64

        self._app.OSC.add_route(f'/{self._uid}', self.__gma_update)
        self._app.MIDI.add_route(device, MIDIMessageTypes.control_change, channel, signal, self.__trigger)

    def set_type(self, fader_type: 'FaderType') -> 'Fader':
        self._off_mode = fader_type._off_mode
        self._off_value = fader_type._off_value
        self._default_inactive_mode = fader_type._default_inactive_mode 
        self._default_active_mode = fader_type._default_active_mode
        self._default_highlight_mode = fader_type._default_highlight_mode
        self._default_highlight_value = fader_type._default_highlight_value
        self._inactive_mode = fader_type._inactive_mode
        self._active_mode = fader_type._active_mode
        self._highlight_mode = fader_type._highlight_mode
        self._highlight_value = fader_type._highlight_value
        return self

    def __trigger(self, msg):
        # Encoder layer override default functionality
        if self._encoder_layer_number is not None and self._app._encoder_layer:
            self._update_mode(self.app, self, None, 'super_highlight')
            if msg.value == 127 or msg.value > self._encoder_value_cache:
                encoder_plus(self._app, self._encoder_layer_number)
            elif msg.value == 0 or msg.value < self._encoder_value_cache:
                encoder_minus(self._app, self._encoder_layer_number)
            return

        value = remap(msg.value, 0, 127, 0, 100)
        self._value = value

        if self._current_fader_type is '':
            return

        if self._gma_value != -1 and self._latch: 
            if (
                self._gma_value > self._old_value
            ):  # If GMA3 value is greater than cached APC fader value, meaning the fader is under the latch
                if (
                    self._gma_value > value
                ):  # Then check if the current fader value is still less than the GMA3 value
                    # print(f'Fader {ch} at {value} | Waiting for latch above {State.fader_values[ch]}', flush=True)
                    return
            # Fader was over latch
            elif self._gma_value < self._old_value:
                if self._gma_value < value:  # Still over latch?
                    # print(f'Fader {ch} at {value} | Waiting for latch below {State.fader_values[ch]}', flush=True)
                    return
        self._gma_value = -1
        # print(f'/Page{State.selected_page + 1}/Fader{ch} | {value}', flush=True)
        self._app.OSC.send(f"/Page{self._device._page + 1}/Fader{self._executor}", value)
        self._app.MIDI.send_control_change(self._device, MIDIMessageTypes.control_change, self._channel, self._signal, int(remap(value, 0, 100, 1, 127)))

        # Update all associated faders
        associated_faders = self._app.get_faders(self._executor)
        for fader in associated_faders:
            fader._value = value
            fader._gma_value = -1
            self._app.MIDI.send_control_change(fader._device, MIDIMessageTypes.control_change, fader._channel, fader._signal, int(remap(value, 0, 100, 1, 127)))
        
        # TODO: Make sure speed faders are updated together, as well as periodically

        # Store the current time of the value change
        Fader._last_value_change = time.time()
        
        # To avoid bogging down MA, wait to update buttons and faders until fader values have stopped updating for 0.25s
        delayed_update(self._app, self._executor, Fader._last_value_change)

        if not hasattr(self, '_update_thread') or not self._update_thread.is_alive() and not self._latch:
            self._update_thread = threading.Thread(target=delayed_update)
            self._update_thread.start()
    
    def _request_update(self):
            threading.Thread(target=request_update, args=(self,)).start()
    
    def __gma_update(self, address: str, *args):
        self._log.debug(f"Fader update received | Executor: {self._executor} | {args}")
        index, button_type, fader_type, fader_value, cue_number = args
        self._value = fader_value
        self._gma_value = fader_value
        self._old_value = self._value
        fader_value = int(remap(fader_value, 0, 100, 1, 127))
        self._app.MIDI.send_control_change(self._device, MIDIMessageTypes.control_change, self._channel, self._signal, fader_value)
        self._current_fader_type = fader_type
        # if not fader_type:
        # #     self._update_mode(self._app, self, button_type, self._state)
        # # else:
        #     self._update_mode(self._app, self, button_type, 'off')
        #     self._state = 'off'

    def set_feedback_config(self, signal: int, channel: int):
        self._feedback_config_signal = signal
        self._feedback_config_channel = channel
