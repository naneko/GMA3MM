import logging
from multiprocessing.pool import ThreadPool
import threading
from time import sleep
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient


class OSCHandler:
    """
    Handles OSC input and output
    """

    log = logging.getLogger()

    def __init__(self, client_ip: str, client_port: int, server_ip: str, server_port: int):
        self.client_ip: str = client_ip or "10.1.1.100"
        self.client_port: int = client_port or 8000
        self.server_ip: str = server_ip or "10.1.1.100"
        self.server_port: int = server_port or 8001
        self.connected = False
        self.lock = threading.Lock()
        
        self.dispatcher = Dispatcher()
        self.client = SimpleUDPClient(self.client_ip, self.client_port)
        self.add_route("/ping", self.connection_response)
        self.add_route("*", self.default_route)

    def route(self, address: str) -> callable:
        """
        Decorator to execute a function via OSC
        :param address: OSC address
        :return: Wrapper function
        """
        def wrapper(func):
            with self.lock:
                self.log.debug(f"Adding OSC route to {func.__name__} | Address: {address}")
                self.dispatcher.map(address, func)
                return func

        return wrapper

    def default_route(self, address: str, *args):
        """
        Default route for all OSC messages
        :param address: OSC address
        :param args: OSC arguments
        """
        self.log.debug(f"OSC message received | Address: {address} | Args: {args}")

    def add_route(self, address: str, func: callable):
        """
        Map a route directly without a decorator
        :param address: OSC address
        :param func: Function to execute
        """
        with self.lock:
            self.log.debug(f"Adding OSC route to {func.__name__} | Address: {address}")
            self.dispatcher.map(address, func)

    def check_connection(self):
        """
        Check if the OSC client is connected
        """
        with self.lock:
            self.connected = False

        def check_connection_helper():
            while not self.connected:
                self.log.debug(f"Checking OSC connection | IP: {self.client_ip} | Port: {self.client_port}")
                self.send_no_check("/cmd", 'SendOSC 2 "/ping,i,0"')
                sleep(1)
        
        if not hasattr(self, '_connection_thread') or not self._connection_thread.is_alive():
            with self.lock:
                self._connection_thread = threading.Thread(target=check_connection_helper)
                self._connection_thread.start()
    
    def connection_response(self, address: str, *args):
        """
        Response to the connection check
        """
        with self.lock:
            self.log.debug(f"OSC connection response | Address: {address} | Args: {args}")
            self.log.info("OSC client connected")
            self.connected = True
    
    def start(self):
        """
        Start OSC server
        """
        def start_helper():
            self.send("/cmd", 'Set OSC Property "EnableOutput" false')
            sleep(1)
            threading.Thread(target=self.server).start()
            sleep(1)
            self.send("/cmd", 'Set OSC Property "EnableOutput" true')
        
        threading.Thread(target=start_helper).start()
    
    def server(self):
        """
        Blocking OSC server
        """
        self.log.debug(
            "OSC Thread Started"
        )
        server = ThreadingOSCUDPServer((self.server_ip, self.server_port), self.dispatcher)
        server.serve_forever()

    def send(self, address: str, message: str):
        """
        Send OSC message to GMA3

        :param address: OSC address
        :param message: OSC message
        """
        if not self.connected:
            self.log.warning("OSC client not connected")
            self.check_connection()
        self.log.debug(f"Sending OSC message | Address: {address} | Message: {message}")
        self.client.send_message(address, message)

    def send_no_check(self, address: str, message: str):
        """
        Send OSC message to GMA3 without checking connection

        :param address: OSC address
        :param message: OSC message
        """
        self.log.debug(f"Sending OSC message | Address: {address} | Message: {message}")
        self.client.send_message(address, message)