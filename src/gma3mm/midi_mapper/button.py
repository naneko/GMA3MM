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

from midi_mapper.tools import request_update

if TYPE_CHECKING:
    from midi_mapper.app import App, button_types
from midi_mapper.midi_handler import Device, MIDIMessageTypes


class ButtonType:
    """
    Define the behavior of a type of MIDI button
    """

    blinking: 'Button' = []

    def __init__(self, app: 'App'):
        self.app: 'App' = app
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.default_off: int = 0  # Default off for all buttons of type
        self.default_on: int = 1  # Default on for all buttons of type
        self.on: dict['button_types': int] = {}  # Feedback settings for specific gma button types
        self.pressed: dict['button_types': int] = {}  # Pressed feedback for specific gma button types
        self.active: dict['button_types': int] = {}  # Active feedback for specific gma button types
        self.blink_off: dict['button_types': int] = {}  # Blink off for specific gma button types
        self.blink_on: dict['button_types': int] = {}  # Blink on for specific gma button types

    def set_blink_off(self, gma_type: 'button_types', value: int) -> 'ButtonType':
        self.blink_off[gma_type] = value
        return self

    def set_blink_on(self, gma_type: 'button_types', value: int) -> 'ButtonType':
        self.blink_on[gma_type] = value
        return self

    def get_blink_on(self, gma_type: 'button_types') -> int:
        blink_on = self.blink_on.get(gma_type, None)
        active = self.active.get(gma_type, None)
        pressed = self.pressed.get(gma_type, None)
        default = self.default_on
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

    def get_blink_off(self, gma_type: 'button_types') -> int:
        blink_off = self.blink_off.get(gma_type, None)
        if blink_off:
            return blink_off
        else:
            return 0

    def set_default_off(self, value: int) -> 'ButtonType':
        self.default_off = value
        return self

    def set_default_on(self, value: int) -> 'ButtonType':
        self.default_on = value
        return self

    def get_off(self) -> int:
        return self.default_off

    def set_on(self, gma_type: 'button_types', value: int) -> 'ButtonType':
        self.on[gma_type] = value
        return self

    def get_on(self, gma_type: 'button_types') -> int:
        if gma_type in self.on:
            return self.on[gma_type]
        else:
            return self.default_on

    def set_pressed(self, gma_type: 'button_types', value: int) -> 'ButtonType':
        self.pressed[gma_type] = value
        return self

    def get_pressed(self, gma_type: 'button_types') -> int:
        if gma_type in self.pressed:
            return self.pressed[gma_type]
        else:
            return self.default_on

    def set_active(self, gma_type: 'button_types', value: int) -> 'ButtonType':
        self.active[gma_type] = value
        return self

    def get_active(self, gma_type: 'button_types') -> int:
        if gma_type in self.active:
            return self.active[gma_type]
        else:
            return self.default_on

    @classmethod
    def update_feedback(cls, app: 'App', button: 'Button', gma_type: 'button_types', state: Literal['off', 'on', 'pressed', 'active']):
        match state:
            case 'off':
                if button.is_blinkable():
                    cls.stop_blink(button)
                app.MIDI.send_note(
                    button.device,
                    MIDIMessageTypes.note_on,
                    button.channel,
                    button.signal,
                    button.get_off()
                )
            case 'on':
                if button.is_blinkable():
                    cls.stop_blink(button)
                app.MIDI.send_note(
                    button.device,
                    MIDIMessageTypes.note_on,
                    button.channel,
                    button.signal,
                    button.get_on(gma_type)
                )
            case 'pressed':
                if button.is_blinkable():
                    cls.stop_blink(button)
                app.MIDI.send_note(
                    button.device,
                    MIDIMessageTypes.note_on,
                    button.channel,
                    button.signal,
                    button.get_pressed(gma_type)
                )
            case 'active':
                app.MIDI.send_note(
                    button.device,
                    MIDIMessageTypes.note_on,
                    button.channel,
                    button.signal,
                    button.get_active(gma_type)
                )
                if button.is_blinkable():
                    cls.start_blink(button)

    @classmethod
    def start_blink(cls, button: 'Button'):
        if button not in cls.blinking:
            cls.blinking.append(button)

    @classmethod
    def stop_blink(cls, button: 'Button'):
        if button in cls.blinking:
            cls.blinking.remove(button)

    @classmethod
    def clear_blink(cls):
        cls.blinking = []

    @classmethod
    def blink(cls, app: 'App'):
        logging.debug('Blink thread started')
        while True:
            for btn in cls.blinking:
                app.MIDI.send_note(
                    btn.device,
                    MIDIMessageTypes.note_on,
                    btn.channel,
                    btn.signal,
                    btn.get_blink_on(btn.current_button_type)
                )
            sleep(0.5)
            for btn in cls.blinking:
                app.MIDI.send_note(
                    btn.device,
                    MIDIMessageTypes.note_on,
                    btn.channel,
                    btn.signal,
                    btn.get_blink_off(btn.current_button_type)
                )
            sleep(0.5)

class Button(ButtonType):
    def __init__(self, app: 'App', device: Device, signal: int, channel: int, executor: int = None, select_page: int = None):
        super().__init__(app)
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.uid: str = str(uuid.uuid4().int)
        self.device: Device = device
        self.signal: int = signal
        self.channel: int = channel
        self.executor: int = executor
        self.select_page: int = select_page
        self.current_button_type: 'button_types' = None

        self.app.OSC.add_route(f'/{self.uid}', self.gma_update)
        self.app.MIDI.add_route(device, MIDIMessageTypes.note_on, channel, signal, self.note_on)
        self.app.MIDI.add_route(device, MIDIMessageTypes.note_off, channel, signal, self.note_off)

        self.request_update()

    def set_type(self, button_type: ButtonType) -> 'Button':
        self.default_off = button_type.default_off
        self.default_feedback = button_type.default_on
        self.feedback = button_type.on
        self.pressed_feedback = button_type.pressed 
        self.active_feedback = button_type.active
        self.blink_off = button_type.blink_off
        self.blink_on = button_type.blink_on
        return self

    def note_on(self, msg: mido.Message):
        self.log.debug(f"Button pressed | Executor: {self.executor} | Page: {self.select_page} | Current Button Type: {self.current_button_type} | {msg}")
        if self.executor:
            self.app.OSC.send(f"/Page{self.device.page + 1}/Key{self.executor}", 1)
        if self.select_page:
            self.device.set_page(self.select_page)
        associated_faders = self.app.get_faders(self.executor)
        for fader in associated_faders:
            fader.update_mode(self.app, fader, self.current_button_type, 'highlight')
    
    def note_off(self, msg: mido.Message):
        self.log.debug(f"Button released | Executor: {self.executor} | Page: {self.select_page} | Current Button Type: {self.current_button_type} | {msg}")
        if self.executor:
            self.app.OSC.send(f"/Page{self.device.page + 1}/Key{self.executor}", 0)
        
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

    def gma_update(self, address: str, *args):
        self.log.debug(f"Button update received | Executor: {self.executor} | Page: {self.select_page} | Current Button Type: {self.current_button_type} | {args}")
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
                self.update_feedback(self.app, self, button_type, 'active')
                for fader in associated_faders:
                    fader.update_mode(self.app, fader, button_type, 'active')
            else:
                self.update_feedback(self.app, self, button_type, 'on')
                for fader in associated_faders:
                    fader.update_mode(self.app, fader, button_type, 'inactive')
        else:
            self.update_feedback(self.app, self, button_type, 'off')


    def is_blinkable(self) -> bool:
        return self.blink_on.get(self.current_button_type, None) != None or self.blink_off.get(self.current_button_type, None) != None

    def request_update(self):
        if self.select_page:
            return
        
        threading.Thread(target=request_update, args=(self,)).start()