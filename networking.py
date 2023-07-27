import socket


def create_server_socket():
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(('localhost', 8001))
    sock.listen()
    sock.setblocking(False)
    return sock
