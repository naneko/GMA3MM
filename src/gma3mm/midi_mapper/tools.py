import logging
from pathlib import Path
from time import sleep
import time
from typing import TYPE_CHECKING, Union

from gma3mm.midi_mapper.button import ButtonType

if TYPE_CHECKING:
    from midi_mapper.button import Button
    from midi_mapper.fader import Fader
    from midi_mapper.app import App


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


def request_update(control: Union['Button', 'Fader']):
    """
    Request data update from MA3 for a button or fader
    
    :param control: Button or Fader to request update for
    """
    sleep(0.1)  # Delay for MA to process the button press
    script_dir = Path(__file__).parent
    if control._executor is None or control._device._page is None:
        return
    with open(script_dir / "get_exec.lua", "r") as f:
        lua = f.readlines()
        control._app.OSC.send(
            "/cmd",
            "lua '"
            + ";".join(lua).replace("[[exec]]", str(control._executor)).replace(
                "[[uid]]", control._uid).replace("[[page]]", str(control._device._page + 1)).replace("\n", "")
            + "'",
        )


def encoder_plus(app: 'App', encoder_index: int):
    """
    Increment an encoder by the resolution setting

    :param app: Instance of the App class
    :param encoder_index: Index of the encoder (1-6)
    """
    if 1 <= encoder_index <= 4:
        lua_action = f"Pult():Children()[2]:Children()[1]:Children()[6]:Children()[5]:Children()[4]:Children()[3]:Children()[5]:Children()[{encoder_index + 2}]:Children()[3]:Children()[6].setplus()"
    elif 5 <= encoder_index <= 6:
        lua_action = f"Pult():Children()[2]:Children()[1]:Children()[6]:Children()[5]:Children()[4]:Children()[3]:Children()[5]:Children()[7]:Children()[{encoder_index + 2}]:Children()[3]:Children()[1].setplus()"

    app.OSC.send("/cmd", "lua '" + lua_action + "'")

def encoder_minus(app: 'App', encoder_index: int):
    """
    Decrement an encoder by the resolution setting

    :param app: Instance of the App class
    :param encoder_index: Index of the encoder (1-6)
    """
    if 1 <= encoder_index <= 4:
        lua_action = f"Pult():Children()[2]:Children()[1]:Children()[6]:Children()[5]:Children()[4]:Children()[3]:Children()[5]:Children()[{encoder_index + 2}]:Children()[3]:Children()[6].setminus()"
    elif 5 <= encoder_index <= 6:
        lua_action = f"Pult():Children()[2]:Children()[1]:Children()[6]:Children()[5]:Children()[4]:Children()[3]:Children()[5]:Children()[7]:Children()[{encoder_index + 2}]:Children()[3]:Children()[1].setminus()"

    app.OSC.send("/cmd", "lua '" + lua_action + "'")

def delayed_update(app: 'App', executor: int, last_value_change: float):
    while True:
        current_time = time.time()
        if current_time - last_value_change >= 0.15:
            associated_buttons = app.get_buttons(executor)
            for button in associated_buttons:
                button._request_update()
            for button in ButtonType.blinking:
                button._request_update()
            associated_faders = app.get_faders(executor)
            for fader in associated_faders:
                fader._request_update()
            break
        sleep(0.05)

def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Add a new logging level to the logging module.

    :param levelName: Name of the new logging level (e.g., 'VERBOSE')
    :param levelNum: Numeric value of the new logging level (e.g., 15)
    :param methodName: Optional name for the logging method (default is levelName.lower())
    :raises AttributeError: If the levelName or methodName already exists in logging module or logger class
    :raises ValueError: If levelNum is not an integer or is less than 0
    :raises TypeError: If levelName is not a string
    :example: addLoggingLevel('VERBOSE', 15)
    :example: addLoggingLevel('VERBOSE', 15, 'verbose')
    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError(
            '{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError(
            '{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError(
            '{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)
