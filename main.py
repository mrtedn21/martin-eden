import functools
import selectors
import socket
from selectors import BaseSelector


registered_coroutines = []


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


def accept_connection(future: Future, connection: socket):
    client_socket, client_address = connection.accept()
    client_socket.setblocking(False)
    future.set_result((client_socket, client_address))


def receive_data(future: Future, client_socket: socket):
    result = b''
    while True:
        try:
            data = client_socket.recv(3)
        except BlockingIOError:
            break
        result += data
    print(result)
    future.set_result(result)


def register_connection_in_selector(sel: BaseSelector, sock, callback) -> socket:
    future = Future()
    try:
        sel.get_key(sock)
    except KeyError:
        sel.register(
            sock,
            selectors.EVENT_READ,
            functools.partial(callback, future),
        )
    else:
        sel.modify(
            sock,
            selectors.EVENT_READ,
            functools.partial(callback, future),
        )
    return future


async def listen_client(sel, client_socket):
    while True:
        client_connection_future = register_connection_in_selector(sel, client_socket, receive_data)
        await client_connection_future


async def main(sel: BaseSelector):
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(('localhost', 8001))
    sock.listen()
    sock.setblocking(False)

    while True:
        connection_future = register_connection_in_selector(sel, sock, accept_connection)
        client_socket, client_address = await connection_future

        global registered_coroutines
        registered_coroutines.append(listen_client(sel, client_socket))


if __name__ == '__main__':
    selector = selectors.DefaultSelector()

    coro = main(selector)

    while True:
        try:
            state = coro.send(None)
            for coroutine in registered_coroutines:
                coroutine.send(None)

            events = selector.select()

            for key, mask in events:
                callback = key.data
                callback(key.fileobj)
        except StopIteration as si:
            break
