import logging
from midi_mapper.app import App

logging.basicConfig(level=logging.DEBUG)

app = App("0.0.0.0", 8000, "0.0.0.0", 8001)

launch_control = app.MIDI.add_device("Launch Control XL", "Launch Control XL")

app.register_button(launch_control, 101, 41, 8)

app.start()