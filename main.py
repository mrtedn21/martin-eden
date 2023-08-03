import asyncio
import uvloop


class EchoServerProtocol(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.transport = None

    def connection_made(self, transport: asyncio.Transport):
        peername = transport.get_extra_info('peername')
        print(f'connection from {peername}')
        self.transport = transport

    def data_received(self, data: bytes):
        message = data.decode()
        print(f'get data: {message}')

        self.transport.write(b'HTTP/1.0 200 OK\n\nHello World')
        self.transport.close()


async def main():
    event_loop = asyncio.get_running_loop()
    server = await event_loop.create_server(
        lambda: EchoServerProtocol(),
        '0', 8001,
    )
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    uvloop.install()
    asyncio.run(main())
