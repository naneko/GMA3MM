import enum
import logging
import logging.handlers
import os
import platform
import sys
import threading
from pathlib import Path

import mido
from midi_mapper.tools import addLoggingLevel
from midi_mapper.button import Button, ButtonType
from midi_mapper.fader import Fader
from midi_mapper.midi_handler import Device, MIDIHandler
from midi_mapper.osc_handler import OSCHandler

if platform.system() == "Windows":
    os.add_dll_directory(Path(__file__).parent)
    mido.set_backend('mido.backends.portmidi')

# TODO: On crash, send error midi state and then restart

addLoggingLevel('FINE', logging.DEBUG - 5)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(
    "gma3mm.log", maxBytes=5*1024*1024, backupCount=2)
file_handler.setLevel(logging.DEBUG)

logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d][%(levelname)s][%(name)s] %(message)s",
    datefmt="%Y-%m-%d,%H:%M:%S",
    handlers=[console_handler, file_handler],
    level=logging.DEBUG,
)

class App:
    """
    Main GMA3MM app class
    """

    def __init__(
        self,
        osc_client_ip: str,
        osc_client_port: int,
        osc_server_ip: str,
        osc_server_port: int,
    ):
        """
        Args:
            osc_client_ip (str): OSC Client IP address (Sends OSC messages to GMA3)
            osc_client_port (int): OSC Client Port
            osc_server_ip (str): OSC Server IP address (Receives OSC messages from GMA3)
            osc_server_port (int): OSC Server Port
        """
        self.OSC: OSCHandler = OSCHandler(
            self, osc_client_ip, osc_client_port, osc_server_ip, osc_server_port
        )
        self.MIDI: MIDIHandler = MIDIHandler(self)
        self._log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._buttons: list[Button] = []
        self._encoders: list[Fader] = []
        self._faders: list[Fader] = []
        self._log.info("Initialized GMA3MM")

    @staticmethod
    def __exception_hook(exception_type, value, traceback):
        import traceback
        from notifypy import Notify
        traceback.print_exception(exception_type, value, traceback)
        logging.exception("GMA3MM Crashed")
        notif = Notify()
        notif.title = "ALERT: GMA3MM Crashed"
        notif.send()    

    def start(self, exception_hook: bool = False):
        """
        Starts GMA3MM app
        """
        # Workaround allows GMA3MM to bind to port 8001 by telling GMA3 to disable OSC output for a second and then turning back on so it can't bind to the port itself
        self._log.info("Starting GMA3MM")
        self.MIDI.start()
        self.OSC.start()
        threading.Thread(target=ButtonType._blink, args=(self,)).start()
        self.OSC.check_connection()
        self._log.info("GMA3MM Started")
        if exception_hook:
            sys.excepthook = self.__exception_hook

    def register_fader(
        self, device: Device, executor: int, signal: int, channel: int, latch: bool
    ) -> Fader:
        """Register a MIDI fader

        Args:
            device (Device): MIDI Device to register fader to
            executor (int): GMA3 Executor to control
            signal (int): MIDI control signal to listen for
            channel (int): MIDI channel to listen on
            latch (bool): When page is changed, should to new value be latched until the fader is equal to that value. This is useful for static faders and will prevent the fader from jumping to the new value when the page is changed.

        Returns:
            Fader: Newly created fader object
        """
        self._log.fine(
            f"Registering fader | Device: {device._input_name} | Executor: {executor} | Signal: {signal} | Channel: {channel} | Latch: {latch}"
        )
        fader = Fader(self, device, signal, channel, executor, latch=latch)
        self._faders.append(fader)
        return fader

    def register_button(
        self, device: Device, executor: int, signal: int, channel: int
    ) -> Button:
        """Register a MIDI button

        Args:
            device (Device): MIDI Device to register button to
            executor (int): GM3 Executor to control
            signal (int): MIDI note to listen for
            channel (int): MIDI channel to listen on

        Returns:
            Button: Newly created button object
        """
        self._log.fine(
            f"Registering button | Device: {device._input_name} | Executor: {executor} | Signal: {signal} | Channel: {channel}"
        )
        button = Button(self, device, signal, channel, executor=executor)
        self._buttons.append(button)
        return button

    def register_page_button(
        self, device: Device, page: int, signal: int, channel: int
    ) -> Button:
        """Register a MIDI page button

        This will change the executor page the MIDI device is controlling

        Args:
            device (Device): MIDI Device to register button to
            page (int): Page to change to
            signal (int): MIDI note to listen for
            channel (int): MIDI channel to listen on

        Returns:
            Button: Newly created button object
        """
        self._log.fine(
            f"Registering page button | Device: {device._input_name} | Page: {page} | Signal: {signal} | Channel: {channel}"
        )
        button = Button(self, device, signal, channel, select_page=page)
        self._buttons.append(button)
        return button

    def get_faders(self, executor: int) -> list[Fader]:
        """Get all faders for a specific executor

        Args:
            executor (int): GMA3 executor number

        Returns:
            list[Fader]: List of fader objects
        """
        return [f for f in self._faders if f._executor == executor]

    def get_buttons(self, executor: int) -> list[Button]:
        """Get all buttons for a specific executor

        Args:
            executor (int): GMA3 executor number

        Returns:
            list[Button]: List of button objects
        """
        return [b for b in self._buttons if b._executor == executor]


class ButtonTypes(enum.Enum):
    """GMA3 executor button types"""

    def __str__(self):
        return str(self.value)

    FORWARD = ">>>"
    BACKWARD = "<<<"
    BLACK = "Black"
    DOUBLE_SPEED = "DoubleSpeed"
    FLASH = "Flash"
    GO_FORWARD = "Go+"
    GO_BACKWARD = "Go-"
    GOTO = "Goto"
    HALF_SPEED = "HalfSpeed"
    KILL = "Kill"
    LEARN_SPEED = "LearnSpeed"
    LOAD = "Load"
    ON = "On"
    OFF = "Off"
    PAUSE = "Pause"
    RATE_1 = "Rate1"
    SELECT = "Select"
    SELECT_FIXTURES = "SelectFixtures"
    SPEED_1 = "Speed1"
    SWAP = "Swap"
    TEMP = "Temp"
    TOGGLE = "Toggle"
    TOP = "Top"
