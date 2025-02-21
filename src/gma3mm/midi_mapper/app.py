from abc import ABC
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

from midi_mapper.osc_handler import OSCHandler
from midi_mapper.midi_handler import MIDIHandler
from midi_mapper.fader import Fader, FaderType
from midi_mapper.button import Button, ButtonType
from midi_mapper.midi_handler import Device

# TODO: Do this on windows only
# os.add_dll_directory(Path(__file__).parent)

# TODO: On crash, send error midi state and then restart

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
        self.OSC: OSCHandler = OSCHandler(osc_client_ip, osc_client_port, osc_server_ip, osc_server_port)
        self.MIDI: MIDIHandler = MIDIHandler(self)
        self.log: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.buttons: list[Button] = []
        self.encoders: list[Fader] = []
        self.faders: list[Fader] = []
        self.log.info("Initialized GMA3MM")

    def start(self):
        """
        Starts GMA3MM app
        """
        # Workaround allows GMA3MM to bind to port 8001 by telling GMA3 to disable OSC output for a second and then turning back on so it can't bind to the port itself
        self.log.info("Starting GMA3MM")
        self.MIDI.start()
        self.OSC.start()
        threading.Thread(target=ButtonType.blink, args=(self,)).start()
        self.OSC.check_connection()
        self.log.info("GMA3MM Started")

    def register_fader(self, device: Device, executor: int, signal: int, channel: int, latch: bool) -> Fader:
        self.log.debug(f"Registering fader | Device: {device.input_name} | Executor: {executor} | Signal: {signal} | Channel: {channel} | Latch: {latch}")
        fader = Fader(self, device, signal, channel, executor, latch=latch)
        self.faders.append(fader)
        return fader

    def register_button(self, device: Device, executor: int, signal: int, channel: int) -> Fader:
        self.log.debug(f"Registering button | Device: {device.input_name} | Executor: {executor} | Signal: {signal} | Channel: {channel}")
        button = Button(self, device, signal, channel, executor=executor)
        self.buttons.append(button)
        return button

    def register_page_button(self, device: Device, page: int, signal: int, channel: int) -> Button:
        self.log.debug(f"Registering page button | Device: {device.input_name} | Page: {page} | Signal: {signal} | Channel: {channel}")
        button = Button(self, device, signal, channel, select_page=page)
        self.buttons.append(button)
        return button
    
    def get_faders(self, executor: int) -> list[Fader]:
        return [f for f in self.faders if f.executor == executor]
    
    def get_buttons(self, executor: int) -> list[Button]:
        return [b for b in self.buttons if b.executor == executor]

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