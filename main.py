import asyncio
import dataclasses
import json
import socket
from asyncio import AbstractEventLoop
from typing import Any, Optional

from dacite import from_dict as dataclass_from_dict

from chats import controllers as chat_controllers  # noqa: F401
from core import Controller
from database import DataBase, query_params_to_alchemy_filters
from http_utils import HttpHeadersParser, HttpMethod, create_response_headers
from openapi import OpenApiBuilder
from routing import ControllerDefinitionError, get_controller, register_route
from users import controllers as user_controllers  # noqa: F401
from utils import get_argument_names

db = DataBase()


@register_route('/schema/', 'get')
async def get_openapi_schema() -> str:
    return json.dumps(OpenApiBuilder().openapi_object)


class HttpRequestHandler:
    def __init__(
        self, event_loop: AbstractEventLoop, client_socket: socket.socket,
    ):
        self.event_loop = event_loop
        self.client_socket = client_socket

    async def handle_request(self):
        http_message: str = await self._read_message_from_socket()
        http_parser = HttpHeadersParser(http_message)

        if http_parser.method_name == HttpMethod.OPTIONS:
            return await self._send_response_for_options_method()

        controller = get_controller(http_parser.path, http_parser.method_name)

        if http_parser.method_name == HttpMethod.POST:
            response = await self._get_response_for_post_method(
                controller, http_parser.body,
            )
        else:
            response = await self._get_response_for_get_method(
                controller, http_parser.query_params,
            )

        await self._write_post_or_get_response_to_socket(response)

    async def _write_post_or_get_response_to_socket(self, response: str):
        headers = create_response_headers(200, content_type='application/json')
        await self.event_loop.sock_sendall(
            self.client_socket, (headers + response).encode('utf8'),
        )
        self.client_socket.close()

    async def _read_message_from_socket(self) -> str:
        data = await self.event_loop.sock_recv(self.client_socket, 1024)
        message = data.decode()
        return message

    async def _send_response_for_options_method(self) -> None:
        headers: str = create_response_headers(200, for_options=True)
        await self.event_loop.sock_sendall(
            self.client_socket, headers.encode('utf8'),
        )
        self.client_socket.close()

    async def _get_response_for_get_method(
        self, controller: Controller, query_params: dict,
    ) -> str:
        controller_argument_names = get_argument_names(controller)
        if 'query_params' in controller_argument_names:
            query_params = self._prepare_query_parameters(
                controller, query_params,
            )
            response = await controller(query_params)
        else:
            response = await controller()

        if isinstance(response, (list, dict)):
            response = json.dumps(response)
        return response

    @staticmethod
    def _prepare_query_parameters(
        controller: Controller, query_params: dict,
    ) -> list:
        """If request contains query parameters, then this method
        returns list of translated query params to sqlalchemy filters.
        But if query params is empty, this method returns [True]
        that means, no filter and return all data.

        But anyway, filters must be list. In this case, user, in
        controllers can use *filters and python correctly fill filters"""
        if query_params:
            alchemy_filters = []
            for query_name, query_value in query_params.items():
                new_filter = query_params_to_alchemy_filters(
                    controller.query_params, query_name, query_value,
                )
                alchemy_filters.append(new_filter)
            return alchemy_filters
        else:
            return [True]

    async def _get_response_for_post_method(
        self, controller: Controller, http_body: str,
    ) -> str:
        request_data = controller.request_schema.loads(http_body)
        dataclass_name, dataclass_object = (
            self._get_dataclass_from_argument_for_post_method(controller)
        )

        response = await controller(**{
            dataclass_name: dataclass_from_dict(dataclass_object, request_data)
        })
        response = self._response_of_controller_to_str(controller, response)
        return response

    @staticmethod
    def _response_of_controller_to_str(
        controller: Controller, response: Any,
    ) -> str:
        if dataclasses.is_dataclass(response):
            response = dataclasses.asdict(response)
        if isinstance(response, dict):
            try:
                response = controller.response_schema.dumps(response)
            except TypeError:
                response = json.dumps(response)
        return response

    @staticmethod
    def _get_dataclass_from_argument_for_post_method(
        controller: Controller,
    ) -> tuple:
        controller_annotations = controller.__annotations__.copy()
        controller_annotations.pop('return', None)
        dataclass_name, dataclass_object = controller_annotations.popitem()
        if any((
            len(controller_annotations) > 0,
            not dataclasses.is_dataclass(dataclass_object),
        )):
            raise ControllerDefinitionError(
                'in post controller only one '
                'argument can be defined - dataclass',
            )
        return dataclass_name, dataclass_object


class Backend:
    def __init__(self):
        self.event_loop: Optional[AbstractEventLoop] = None
        self.server_socket: Optional[socket.socket] = None
        self._configure_sockets()
        OpenApiBuilder().write_marshmallow_schemas_to_openapi_doc()

    def _configure_sockets(self):
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM,
        )
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,
        )

        server_address = ('localhost', 8001)
        self.server_socket.setblocking(False)
        self.server_socket.bind(server_address)

    async def handle_request(self, client_socket: socket.socket):
        handler = HttpRequestHandler(self.event_loop, client_socket)
        await handler.handle_request()

    async def main(self):
        """The method listen server socket for connections, if connection
        is gotten, creates client_socket and sends response to it."""

        # Getting of event loop in main because it must be in asyncio.run
        self.event_loop = asyncio.get_event_loop()
        self.server_socket.listen()
        while True:
            client_socket, client_address = (
                await self.event_loop.sock_accept(self.server_socket)
            )
            print(f'get request for connection from {client_address}')
            await asyncio.create_task(
                self.handle_request(client_socket),
            )


if __name__ == '__main__':
    # uvloop.install()
    backend = Backend()
    asyncio.run(backend.main(), debug=True)
