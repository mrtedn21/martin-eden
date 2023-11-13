import asyncio
import dataclasses
import json
import socket
from asyncio import AbstractEventLoop
from typing import Any, Optional

from dacite import from_dict as dataclass_from_dict

from martin_eden.base import Controller
from martin_eden.database import DataBase, query_params_to_alchemy_filters
from martin_eden.http_utils import (HttpHeadersParser, HttpMethod,
                                    create_response_headers)
from martin_eden.openapi import OpenApiBuilder
from martin_eden.routing import (ControllerDefinitionError,
                                 FindControllerError, get_controller,
                                 register_route)
from martin_eden.utils import get_argument_names

db = DataBase()


@register_route('/schema/', 'get')
async def get_openapi_schema() -> str:
    return json.dumps(OpenApiBuilder().openapi_object)


class HttpMessageHandler:
    def __init__(self, message: bytes) -> None:
        self.http_message = message.decode('utf8')

    async def handle_request(self) -> bytes:
        http_parser = HttpHeadersParser(self.http_message)

        if http_parser.method_name == HttpMethod.OPTIONS:
            return self._get_response_for_options_method()

        try:
            controller = get_controller(
                http_parser.path, http_parser.method_name,
            )
        except FindControllerError:
            return self._get_response_for_get_and_post_methods(
                '404 not found'
            )

        if http_parser.method_name == HttpMethod.POST:
            response = await self._get_response_for_post_method(
                controller, http_parser.body,
            )
        else:
            response = await self._get_response_for_get_method(
                controller, http_parser.query_params,
            )

        return self._get_response_for_get_and_post_methods(response)

    @staticmethod
    def _get_response_for_get_and_post_methods(response: str) -> bytes:
        headers = create_response_headers(200, content_type='application/json')
        return (headers + response).encode('utf8')

    @staticmethod
    def _get_response_for_options_method() -> bytes:
        headers: str = create_response_headers(200, for_options=True)
        return headers.encode('utf8')

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
    def __init__(self) -> None:
        self.event_loop: Optional[AbstractEventLoop] = None
        self.server_socket: Optional[socket.socket] = None
        self._configure_sockets()
        OpenApiBuilder().write_marshmallow_schemas_to_openapi_doc()

    def _configure_sockets(self) -> None:
        self.server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM,
        )
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1,
        )

        server_address = ('localhost', 8001)
        self.server_socket.setblocking(False)
        self.server_socket.bind(server_address)

    async def handle_request(self, client_socket: socket.socket) -> None:
        message = b''
        while chunk := await self.event_loop.sock_recv(client_socket, 1024):
            message += chunk

        handler = HttpMessageHandler(message)
        message = await handler.handle_request()

        await self.event_loop.sock_sendall(client_socket, message)
        client_socket.close()

    async def main(self) -> None:
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
