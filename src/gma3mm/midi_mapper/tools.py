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
    sleep(0.1) # Delay for MA to process the button press
    script_dir = Path(__file__).parent
    with open(script_dir / "get_exec.lua", "r") as f:
        lua = f.readlines()
        control._app.OSC.send(
            "/cmd",
            "lua '"
            + ";".join(lua).replace("[[exec]]", str(control._executor)).replace("[[uid]]", control._uid).replace("[[page]]", str(control._device._page + 1)).replace("\n", "")
            + "'",
        )