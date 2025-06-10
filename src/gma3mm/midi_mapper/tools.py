import logging
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from midi_mapper.button import Button
    from midi_mapper.fader import Fader


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


def addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

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
