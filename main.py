from custom_asyncio import EventLoop
import socket
from networking import create_server_socket


async def listen_client(event_loop: EventLoop, client_socket: socket.socket):
    while True:
        client_connection_future = event_loop.register_client_socket(client_socket)
        await client_connection_future


async def main(event_loop: EventLoop):
    sock = create_server_socket()
    while True:
        connection_future = event_loop.register_server_socket(sock)
        client_socket = await connection_future
        event_loop.add_coroutine(listen_client(event_loop, client_socket))


if __name__ == '__main__':
    loop = EventLoop()
    loop.run(main(loop))
