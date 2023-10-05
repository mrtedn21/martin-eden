from chats import controllers
from users import controllers

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
from http_headers import HttpHeadersParser, create_response_headers
from openapi import openapi_object, write_pydantic_models_to_openapi
from routing import get_controller, register_route

db = DataBase()


@register_route('/schema/', ('get', ))
async def get_openapi_schema() -> str:
    return json.dumps(openapi_object)


async def handle_request(
    client_socket: socket.socket,
    loop: AbstractEventLoop,
):
    data = await loop.sock_recv(client_socket, 1024)
    message = data.decode()

    parser = HttpHeadersParser(message)
    path = parser.get_path()
    method = parser.get_method_name()
    query_params = parser.get_query_params()

    if method == 'OPTIONS':
        headers = create_response_headers(200, 'application/json')
        await loop.sock_sendall(
            client_socket,
            (headers + 'HTTP/1.1 204 No Content\nAllow: OPTIONS, GET, POST').encode('utf8'),
        )
        client_socket.close()
        return

    try:
        controller = get_controller(path, method)
    except KeyError:
        # temp decision for not existing paths
        return

    if method == 'POST':
        types = controller.__annotations__
        controller_schema = controller.request

        body = parser.get_body()
        parsed_dict = controller_schema.loads(body)

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
            key, value = list(query_params.items())[0]
            response: str = await controller(query_params=query_params_to_alchemy_filters(controller.query_params, key, value))
        else:
            response: str = await controller()

        if isinstance(response, list):
            response = json.dumps(response)

    headers = create_response_headers(200, 'application/json')
    await loop.sock_sendall(
        client_socket,
        (headers + response).encode('utf8'),
    )
    client_socket.close()


async def listen_for_connection(
    server_socket: socket,
    loop: AbstractEventLoop,
):
    while True:
        connection, address = await loop.sock_accept(server_socket)
        print(f'get request for connection from {address}')
        await asyncio.create_task(handle_request(connection, loop))


async def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = ('localhost', 8001)
    server_socket.setblocking(False)
    server_socket.bind(server_address)
    server_socket.listen()

    write_pydantic_models_to_openapi()
    await listen_for_connection(server_socket, asyncio.get_event_loop())


if __name__ == '__main__':
    # uvloop.install()
    asyncio.run(main(), debug=True)
