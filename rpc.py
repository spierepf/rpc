import json
import logging
import socket
from select import select

logger = logging.getLogger(__name__)


class RPCServer:
    def __init__(self, instance, port=0):
        self._instance = instance
        self._methods =  {k : v for k in dir(self._instance) for v in [getattr(self._instance, k)] if callable(getattr(self._instance, k))}
        self._port = port
        self._server_socket = None
        self._sockets = []

    def _handle_call(self, buffer):
        method_name, args, kwargs = json.loads(buffer)
        try:
            result = (True, self._methods[method_name](*args, **kwargs)) if method_name in self._methods else (False, repr( AttributeError(f"'{self._instance.__class__.__name__}' object has no attribute '{method_name}'")))
        except BaseException as e:
            result = (False, repr(e))
        return json.dumps(result).encode()

    def run(self):
        if len(self._sockets) == 0:
            return False
        (r, _, _) = select(self._sockets, [], [])
        for s in r:
            if s == self._server_socket:
                client, address = self._server_socket.accept()
                logger.info(f'Accepted connection from {address}')
                self._sockets.append(client)
            else:
                try:
                    buffer = s.recv(1024)
                    if len(buffer) == 0:
                        logger.info(f'Closed connection from {socket}')
                        self._sockets.remove(s)
                    else:
                        s.sendall(self._handle_call(buffer))
                except OSError:
                    if s in self._sockets:
                        self._sockets.remove(s)
        return True

    def connect(self):
        if self._server_socket is None:
            logger.info(f'Starting server for {object}')
            self._server_socket = socket.socket()
            self._server_socket.bind(socket.getaddrinfo('0.0.0.0', self._port)[0][-1])
            self._server_socket.listen()
            if 'getsockname' in dir(self._server_socket):
                self._port = self._server_socket.getsockname()[1]
            self._sockets += [self._server_socket]

    def disconnect(self):
        self._sockets.remove(self._server_socket)
        self._server_socket.close()
        self._server_socket = None


class RPCClient:
    def __init__(self, address):
        self._address = address
        self._socket = None

    def connect(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect(self._address)

    def disconnect(self):
        self._socket.close()

    def __getattr__(self, method_name: str):
        def do(*args, **kwargs):
            self._socket.sendall(json.dumps((method_name, args, kwargs)).encode())
            success, result = json.loads(self._socket.recv(1024).decode())
            if success:
                return result
            else:
                raise Exception(result)

        return do

    def __del__(self):
        self.disconnect()
