import enum
from multiprocessing.pool import ThreadPool
from pathlib import Path
import threading
from time import sleep
import time
from typing import TYPE_CHECKING, Literal
import uuid
import mido
import logging

from midi_mapper.tools import delayed_update, request_update

if TYPE_CHECKING:
    from midi_mapper.app import App, ButtonTypes
from midi_mapper.midi_handler import Device, MIDIMessageTypes


class ButtonType:
    """
    Define the behavior of a type of MIDI button
    """

    blinking: list['Button'] = []

    def __init__(self, app: 'App'):
        """
        Args:
            app (App): GMA3MM App instance
        """
        self._app: 'App' = app
        self._log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._off: int = 0  # Default off for all buttons of type
        self._default_on: int = 1  # Default on for all buttons of type
        self._on: dict['button_types': int] = {}  # Feedback settings for specific gma button types
        self._pressed: dict['button_types': int] = {}  # Pressed feedback for specific gma button types
        self._active: dict['button_types': int] = {}  # Active feedback for specific gma button types
        self._blink_off: dict['button_types': int] = {}  # Blink off for specific gma button types
        self._blink_on: dict['button_types': int] = {}  # Blink on for specific gma button types

    def set_blink_off(self, gma_type: 'ButtonTypes', value: int) -> 'ButtonType':
        """Sets the blink off value for a GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._blink_off[gma_type] = value
        return self

    def set_blink_on(self, gma_type: 'ButtonTypes', value: int) -> 'ButtonType':
        """Sets the blink on value for a GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._blink_on[gma_type] = value
        return self

    def get_blink_on(self, gma_type: 'ButtonTypes') -> int:
        """Get the blink on value for a GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type

        Returns:
            int: Blink on MIDI value
        """
        blink_on = self._blink_on.get(gma_type, None)
        active = self._active.get(gma_type, None)
        pressed = self._pressed.get(gma_type, None)
        default = self._default_on
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

    def get_blink_off(self, gma_type: 'ButtonTypes') -> int:
        """Get the blink off value for a GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type

        Returns:
            int: Blink off MIDI value
        """
        blink_off = self._blink_off.get(gma_type, None)
        if blink_off:
            return blink_off
        else:
            return 0

    def set_default_off(self, value: int) -> 'ButtonType':
        """Set the default on value for all unmapped GMA3 button types. This is the feedback when an executor is not assigned on the current page.

        Args:
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._off = value
        return self

    def set_default_on(self, value: int) -> 'ButtonType':
        """Set the default on value for all unmapped GMA3 button types. This is the feedback when an executor is assigned on the current page but is not pressed or active.

        Args:
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._default_on = value
        return self

    def get_off(self) -> int:
        """Get the off value for all buttons using this ButtonType

        Returns:
            int: MIDI value
        """
        return self._off

    def set_on(self, gma_type: 'ButtonTypes', value: int) -> 'ButtonType':
        """Set the on value for a specific GMA3 button type. This is the feedback when the executor exists but is not pressed or active.

        Args:
            gma_type (button_types): GMA3 button type
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._on[gma_type] = value
        return self

    def get_on(self, gma_type: 'ButtonTypes') -> int:
        """Get the on value for a specific GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type

        Returns:
            int: MIDI value
        """
        if gma_type in self._on:
            return self._on[gma_type]
        else:
            return self._default_on

    def set_pressed(self, gma_type: 'ButtonTypes', value: int) -> 'ButtonType':
        """Set the pressed value for a specific GMA3 button type. This is the feedback when the button is pressed.

        Args:
            gma_type (button_types): GMA3 button type
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._pressed[gma_type] = value
        return self

    def get_pressed(self, gma_type: 'ButtonTypes') -> int:
        """Get the pressed value for a specific GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type

        Returns:
            int: MIDI value
        """
        if gma_type in self._pressed:
            return self._pressed[gma_type]
        else:
            return self._default_on

    def set_active(self, gma_type: 'ButtonTypes', value: int) -> 'ButtonType':
        """Set the active value for a specific GMA3 button type. This is the feedback when the mapped executor is active, on a toggle executor for example.

        Args:
            gma_type (button_types): GMA3 button type
            value (int): MIDI value

        Returns:
            ButtonType: self for chaining
        """
        self._active[gma_type] = value
        return self

    def get_active(self, gma_type: 'ButtonTypes') -> int:
        """Gets the active value for a specific GMA3 button type

        Args:
            gma_type (button_types): GMA3 button type

        Returns:
            int: MIDI value
        """
        if gma_type in self._active:
            return self._active[gma_type]
        else:
            return self._default_on

    @classmethod
    def _update_feedback(cls, app: 'App', button: 'Button', gma_type: 'ButtonTypes', state: Literal['off', 'on', 'pressed', 'active']):
        """Update the feedback state of a button

        Args:
            app (App): GMA3MM App instance
            button (Button): Button to update
            gma_type (button_types): GMA3 button type
            state (Literal['off', 'on', 'pressed', 'active']): State to set the button to
        """
        match state:
            case 'off':
                if button._is_blinkable():
                    cls._stop_blink(button)
                app.MIDI.send_note(
                    button._device,
                    MIDIMessageTypes.note_on,
                    button._channel,
                    button._signal,
                    button.get_off()
                )
            case 'on':
                if button._is_blinkable():
                    cls._stop_blink(button)
                app.MIDI.send_note(
                    button._device,
                    MIDIMessageTypes.note_on,
                    button._channel,
                    button._signal,
                    button.get_on(gma_type)
                )
            case 'pressed':
                if button._is_blinkable():
                    cls._stop_blink(button)
                app.MIDI.send_note(
                    button._device,
                    MIDIMessageTypes.note_on,
                    button._channel,
                    button._signal,
                    button.get_pressed(gma_type)
                )
            case 'active':
                app.MIDI.send_note(
                    button._device,
                    MIDIMessageTypes.note_on,
                    button._channel,
                    button._signal,
                    button.get_active(gma_type)
                )
                if button._is_blinkable():
                    cls._start_blink(button)

    @classmethod
    def _start_blink(cls, button: 'Button'):
        """Start blinking a button

        Args:
            button (Button): Button to blink
        """
        if button not in cls.blinking:
            cls.blinking.append(button)

    @classmethod
    def _stop_blink(cls, button: 'Button'):
        """Stop blinking a button

        Args:
            button (Button): Button to stop blinking
        """
        if button in cls.blinking:
            cls.blinking.remove(button)
            button._update_feedback(button._app, button, button._current_button_type, 'on')

    @classmethod
    def _clear_blink(cls):
        """Stop all blinking buttons
        """
        cls.blinking = []

    @classmethod
    def _blink(cls, app: 'App'):
        """Blinking button thread

        Args:
            app (App): GMA3MM App instance
        """
        logging.debug('Blink thread started')
        while True:
            for btn in cls.blinking:
                app.MIDI.send_note(
                    btn._device,
                    MIDIMessageTypes.note_on,
                    btn._channel,
                    btn._signal,
                    btn.get_blink_on(btn._current_button_type)
                )
            sleep(0.5)
            for btn in cls.blinking:
                app.MIDI.send_note(
                    btn._device,
                    MIDIMessageTypes.note_on,
                    btn._channel,
                    btn._signal,
                    btn.get_blink_off(btn._current_button_type)
                )
            sleep(0.5)

class Button(ButtonType):
    """A MIDI button"""

    _last_value_change: float = 0

    def __init__(self, app: 'App', device: Device, signal: int, channel: int, executor: int = None, select_page: int = None, toggle_encoder_layer: bool = False):
        """
        Args:
            app (App): GMA3MM App instance
            device (Device): MIDI device the button belongs to
            signal (int): Button MIDI note
            channel (int): Button MIDI channel
            executor (int, optional): GMA3 Executor to map to. Defaults to None.
            select_page (int, optional): GMA3 executor page to select for device. Defaults to None.
            toggle_encoder_layer (bool, optional): If True, the button will toggle the encoder layer on the device. Defaults to False.

        Raises:
            ValueError: Button can only have one purpose: executor, select_page, or toggle_encoder_layer
        """
        if (executor is not None) + (select_page is not None) + (toggle_encoder_layer is not False) != 1:
            raise ValueError("Button can only have one purpose: executor, select_page, or toggle_encoder_layer")

        super().__init__(app)
        self._log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._uid: str = str(uuid.uuid4().int)
        self._device: Device = device
        self._signal: int = signal
        self._channel: int = channel
        self._executor: int = executor
        self._select_page: int = select_page
        self._current_button_type: 'ButtonTypes' = None
        self._toggle_encoder_layer: bool = toggle_encoder_layer

        self._app.OSC.add_route(f'/{self._uid}', self.__gma_update)
        self._app.MIDI.add_route(device, MIDIMessageTypes.note_on, channel, signal, self.__note_on)
        self._app.MIDI.add_route(device, MIDIMessageTypes.note_off, channel, signal, self.__note_off)

    def set_type(self, button_type: ButtonType) -> 'Button':
        """Set the feedback behavior of the button using a ButtonType

        Args:
            button_type (ButtonType): ButtonType to use

        Returns:
            Button: self for chaining
        """
        self._off = button_type._off
        self._default_on = button_type._default_on
        self._on = button_type._on
        self._pressed = button_type._pressed 
        self._active = button_type._active
        self._blink_off = button_type._blink_off
        self._blink_on = button_type._blink_on
        return self

    def __note_on(self, msg: mido.Message):
        self._log.debug(f"Button pressed | Executor: {self._executor} | Page: {self._select_page} | Current Button Type: {self._current_button_type} | {msg}")
        if self._executor:
            if not self._current_button_type:
                return
            self._app.OSC.send(f"/Page{self._device._page + 1}/Key{self._executor}", 1)
            associated_faders = self._app.get_faders(self._executor)
            for fader in associated_faders:
                if fader._current_fader_type:
                    fader._update_mode(self._app, fader, self._current_button_type, 'highlight')
        elif self._select_page != None:
            self._device._set_page(self._select_page)
        elif self._toggle_encoder_layer:
            self._app._encoder_layer = not self._app._encoder_layer
            if self._app._encoder_layer:
                for fader in self._app.get_encoders():
                    # fader._update_mode(fader._app, fader, None, 'highlight')
                    fader._encoder_value_cache = 64
                    fader._app.MIDI.send_control_change(fader._device, MIDIMessageTypes.control_change, fader._channel, fader._signal, 64)
                    fader._update_mode(fader._app, fader, None, 'super_highlight')
            else:
                for fader in self._app.get_encoders():
                    fader._update_mode(fader._app, fader, fader._current_fader_type, 'highlight')

    
    def __note_off(self, msg: mido.Message):
        self._log.fine(f"Button released | Executor: {self._executor} | Page: {self._select_page} | Current Button Type: {self._current_button_type} | {msg}")
        if self._executor:
            if not self._current_button_type:
                return
            self._app.OSC.send(f"/Page{self._device._page + 1}/Key{self._executor}", 0)
        
        if self._executor or self._select_page:
            # Store the current time of the value change
            Button._last_value_change = time.time()
            
            # To avoid bogging down MA, wait to update buttons and faders until fader values have stopped updating for 0.25s
            if not hasattr(self, '_update_thread') or not self._update_thread.is_alive():
                self._update_thread = threading.Thread(target=delayed_update, args=(self._app, self._executor, Button._last_value_change))
                self._update_thread.start()

    def __gma_update(self, address: str, *args):
        self._log.debug(f"Button update received | Executor: {self._executor} | Page: {self._select_page} | Current Button Type: {self._current_button_type} | {args}")
        index, button_type, fader_type, fader_value, cue_number = args
        self._current_button_type = button_type
        associated_faders = self._app.get_faders(self._executor)
        if self._is_blinkable():
            if cue_number != "None":
                self._start_blink(self)
                for fader in associated_faders:
                    if fader._current_fader_type:
                        fader._update_mode(self._app, fader, button_type, 'active')
            else:
                self._stop_blink(self)
                self._update_feedback(self._app, self, button_type, 'on')
                for fader in associated_faders:
                    if fader._current_fader_type:
                        fader._update_mode(self._app, fader, button_type, 'inactive')
        elif button_type:
            if cue_number != "None":
                self._update_feedback(self._app, self, button_type, 'active')
                for fader in associated_faders:
                    if fader._current_fader_type:
                        fader._update_mode(self._app, fader, button_type, 'active')
            else:
                self._update_feedback(self._app, self, button_type, 'on')
                for fader in associated_faders:
                    if fader._current_fader_type:
                        fader._update_mode(self._app, fader, button_type, 'inactive')
        else:
            self._update_feedback(self._app, self, button_type, 'off')


    def _is_blinkable(self) -> bool:
        """Get if the button is blinkable

        Returns:
            bool: Whether the button is blinkable
        """
        return self._blink_on.get(self._current_button_type, None) != None or self._blink_off.get(self._current_button_type, None) != None

    def _request_update(self):
        """Request an update to the button feedback state from GMA3"""
        if self._select_page:
            return
        
        threading.Thread(target=request_update, args=(self,)).start()