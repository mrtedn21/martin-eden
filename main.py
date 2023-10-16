from chats import controllers
from users import controllers

from typing import Optional
import asyncio
from inspect import signature
from dacite import from_dict
import dataclasses
import json
import socket
from asyncio import AbstractEventLoop
from database import query_params_to_alchemy_filters

from database import (
    DataBase,
)
from http_utils import HttpHeadersParser, create_response_headers, HttpMethod
from openapi import openapi_object, write_pydantic_models_to_openapi
from routing import get_controller, register_route

db = DataBase()


@register_route('/schema/', ('get', ))
async def get_openapi_schema() -> str:
    return json.dumps(openapi_object)


class App:
    def __init__(self):
        self.event_loop: Optional[AbstractEventLoop] = None
        self.server_socket: Optional[socket.socket] = None
        self._configure_sockets()
        write_pydantic_models_to_openapi()

    def _configure_sockets(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server_address = ('localhost', 8001)
        self.server_socket.setblocking(False)
        self.server_socket.bind(server_address)

    async def handle_request(self, client_socket: socket.socket):
        message: str = await self._read_message_from_socket(client_socket)
        http_parser = HttpHeadersParser(message)

        if http_parser.method_name == HttpMethod.OPTIONS:
            headers = create_response_headers(
                200, content_type='application/json', for_options=True,
            )
            await self.event_loop.sock_sendall(
                client_socket,
                (headers + 'HTTP/1.1 204 No Content\nAllow: OPTIONS, GET, POST').encode('utf8'),
            )
            client_socket.close()
            return

        try:
            controller = get_controller(http_parser.path, http_parser.method_name)
        except KeyError:
            # temp decision for not existing paths
            return

        if http_parser.method_name == 'POST':
            types = controller.__annotations__
            controller_schema = controller.request

            parsed_dict = controller_schema.loads(http_parser.body)

            for arg_name, arg_type in types.items():
                if dataclasses.is_dataclass(arg_type):
                    response = await controller(**{arg_name: from_dict(arg_type, parsed_dict)})
                    if dataclasses.is_dataclass(response):
                        response = dataclasses.asdict(response)
                    if isinstance(response, dict):
                        try:
                            response = controller_schema.dumps(response)
                        except TypeError:
                            response = json.dumps(response)
                    break
        else:
            if 'query_params' in list(dict(signature(controller).parameters).keys()):
                key, value = list(http_parser.query_params.items())[0]
                response: str = await controller(
                    query_params=query_params_to_alchemy_filters(controller.query_params, key, value)
                )
            else:
                response: str = await controller()

            if isinstance(response, list):
                response = json.dumps(response)

        headers = create_response_headers(200, content_type='application/json')
        await self.event_loop.sock_sendall(
            client_socket,
            (headers + response).encode('utf8'),
        )
        client_socket.close()

    async def _read_message_from_socket(self, client_socket: socket.socket) -> str:
        data = await self.event_loop.sock_recv(client_socket, 1024)
        message = data.decode()
        return message

    async def main(self):
        """The method listen server socket for connections,if connection
        is gotten, creates client_socket and sends response to it."""

        # Getting of event loop in main because it must be in asyncio.run
        self.event_loop = asyncio.get_event_loop()
        self.server_socket.listen()
        while True:
            client_connection, client_address = (
                await self.event_loop.sock_accept(self.server_socket)
            )
            print(f'get request for connection from {client_address}')
            await asyncio.create_task(
                self.handle_request(client_connection)
            )


if __name__ == '__main__':
    # uvloop.install()
    app = App()
    asyncio.run(app.main(), debug=True)
