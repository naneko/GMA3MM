import logging
from multiprocessing.pool import ThreadPool
import threading
from time import sleep
from typing import TYPE_CHECKING, List
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

if TYPE_CHECKING:
    from midi_mapper.button import Button
    from midi_mapper.fader import Fader
    from midi_mapper.app import App


class OSCHandler:
    """
    Handles OSC input and output
    """

    def __init__(self, app: 'App', client_ip: str, client_port: int, server_ip: str, server_port: int):
        self._app: 'App' = app
        self._client_ip: str = client_ip or "10.1.1.100"
        self._client_port: int = client_port or 8000
        self._server_ip: str = server_ip or "10.1.1.100"
        self._server_port: int = server_port or 8001
        self._connected = False
        self._lock = threading.Lock()
        self._log = logging.getLogger(self.__class__.__name__)
        
        self._dispatcher = Dispatcher()
        self._client = SimpleUDPClient(self._client_ip, self._client_port)
        self.add_route("/ping", self.__connection_response)
        self.add_route("*", self.default_route)

    def route(self, address: str) -> callable:
        """
        Decorator to execute a function via OSC
        :param address: OSC address
        :return: Wrapper function
        """
        def wrapper(func):
            with self._lock:
                self._log.fine(f"Adding OSC route to {func.__name__} | Address: {address}")
                self._dispatcher.map(address, func)
                return func

        return wrapper

    def default_route(self, address: str, *args):
        """
        Default route for all OSC messages
        :param address: OSC address
        :param args: OSC arguments
        """
        self._log.fine(f"OSC message received | Address: {address} | Args: {args}")

    def add_route(self, address: str, func: callable):
        """
        Map a route directly without a decorator
        :param address: OSC address
        :param func: Function to execute
        """
        with self._lock:
            self._log.fine(f"Adding OSC route to {func.__name__} | Address: {address}")
            self._dispatcher.map(address, func)

    def request_update_all(self, buttons: List['Button'], faders: List['Fader']):
        for button in buttons:
            button._request_update()
        for fader in faders:
            fader._request_update()

    def check_connection(self):
        """
        Check if the OSC client is connected
        """
        with self._lock:
            self._connected = False

        def check_connection_helper():
            while not self._connected:
                self._log.debug(f"Checking OSC connection | IP: {self._client_ip} | Port: {self._client_port}")
                self.send_no_check("/cmd", 'SendOSC 2 "/ping,i,0"')
                sleep(1)
        
        if not hasattr(self, '_connection_thread') or not self._connection_thread.is_alive():
            with self._lock:
                self._connection_thread = threading.Thread(target=check_connection_helper)
                self._connection_thread.start()
    
    def __connection_response(self, address: str, *args):
        """
        Response to the connection check
        """
        with self._lock:
            self._log.debug(f"OSC connection response | Address: {address} | Args: {args}")
            self._log.info("GMA3 OSC client connected")
            self._connected = True
            self.request_update_all(self._app._buttons, self._app._faders)
    
    def start(self):
        """
        Start OSC server
        """
        def start_helper():
            self._log.info("Checking GMA3 OSC connection")
            self.send_no_check("/cmd", 'Set OSC Property "EnableOutput" false')
            sleep(1)
            threading.Thread(target=self.__server).start()
            sleep(1)
            self.send_no_check("/cmd", 'Set OSC Property "EnableOutput" true')
        
        threading.Thread(target=start_helper).start()
    
    def __server(self):
        """
        Blocking OSC server
        """
        self._log.debug(
            "OSC Thread Started"
        )
        server = ThreadingOSCUDPServer((self._server_ip, self._server_port), self._dispatcher)
        server.serve_forever()

    def send(self, address: str, message: str):
        """
        Send OSC message to GMA3

        :param address: OSC address
        :param message: OSC message
        """
        if not self._connected:
            self._log.fine(f"OSC client not connected | Address: {address} | Message: {message}")
            self.check_connection()
        self._log.fine(f"Sending OSC message | Address: {address} | Message: {message}")
        self._client.send_message(address, message)

    def send_no_check(self, address: str, message: str):
        """
        Send OSC message to GMA3 without checking connection

        :param address: OSC address
        :param message: OSC message
        """
        self._log.fine(f"Sending OSC message | Address: {address} | Message: {message}")
        self._client.send_message(address, message)