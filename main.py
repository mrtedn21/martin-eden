import functools
import selectors
import socket
from selectors import BaseSelector
from collections.abc import Coroutine
from typing import Callable


class Future:
    def __init__(self):
        self._result = None
        self._is_finished = None
        self._done_callback = None

    def result(self):
        return self._result

    def is_finished(self):
        return self._is_finished

    def set_result(self, result):
        self._result = result
        self._is_finished = True
        if self._done_callback:
            self._done_callback(result)

    def add_done_callback(self, fn):
        self._done_callback = fn

    def __await__(self):
        while True:
            if not self._is_finished:
                yield self
            else:
                return self.result()


class EventLoop:
    def __init__(self):
        self._selector: BaseSelector = selectors.DefaultSelector()
        self._coroutines: list[Coroutine] = []

    def add_coroutine(self, coroutine: Coroutine):
        self._coroutines.append(coroutine)

    @staticmethod
    def accept_connection_callback(future: Future, server_socket: socket.socket):
        client_socket, client_address = server_socket.accept()
        print(f'new client with address: {client_address}')
        client_socket.setblocking(False)
        future.set_result(client_socket)

    @staticmethod
    def receive_data_callback(future: Future, client_socket: socket.socket):
        result = b''
        while True:
            try:
                data = client_socket.recv(3)
            except BlockingIOError:
                break
            result += data
        print(f'new message from client: {result}')
        future.set_result(result)

    def _register_socket(self, sock: socket.socket, callback: Callable):
        future = Future()
        try:
            self._selector.get_key(sock)
        except KeyError:
            self._selector.register(
                sock,
                selectors.EVENT_READ,
                functools.partial(callback, future),
            )
        else:
            self._selector.modify(
                sock,
                selectors.EVENT_READ,
                functools.partial(callback, future),
            )
        return future

    def register_server_socket(self, sock: socket.socket):
        return self._register_socket(sock, self.accept_connection_callback)

    def register_client_socket(self, sock: socket.socket):
        return self._register_socket(sock, self.receive_data_callback)

    def run(self, coroutine: Coroutine):
        while True:
            try:
                coroutine.send(None)
                for coro in self._coroutines:
                    coro.send(None)

                events = self._selector.select()

                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj)
            except StopIteration:
                break


async def listen_client(event_loop: EventLoop, client_socket: socket.socket):
    while True:
        client_connection_future = event_loop.register_client_socket(client_socket)
        await client_connection_future


async def main(event_loop: EventLoop):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(('localhost', 8001))
    sock.listen()
    sock.setblocking(False)

    while True:
        connection_future = event_loop.register_server_socket(sock)
        client_socket = await connection_future

        event_loop.add_coroutine(listen_client(event_loop, client_socket))


if __name__ == '__main__':
    loop = EventLoop()
    loop.run(main(loop))
