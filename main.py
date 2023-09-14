import asyncio
import json
import socket
from asyncio import AbstractEventLoop
from datetime import date

from pydantic import BaseModel
from sqlalchemy import select

from database import DataBase, SqlAlchemyToPydantic, UserOrm, CountryOrm, CityOrm
from http_headers import HttpHeadersParser, create_response_headers
from openapi import openapi_object
from routing import get_controller, register_route

db = DataBase()


def get_dict_from_orm_object(some_object):
    result_data = {}
    for attr in dir(some_object):
        attr_type = type(getattr(some_object, attr))
        if attr.startswith('_'):
            continue

        if attr_type in (str, int):
            result_data[attr] = getattr(some_object, attr)
        elif attr_type == date:
            attr_date: date = getattr(some_object, attr)
            str_date_time = attr_date.strftime('%d-%m-%Y')
            result_data[attr] = str_date_time

    return result_data


class CountryGetModel(CountryOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'


class CountryCreateModel(CountryOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__without_pk__'


class CityGetModel(CityOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'
    country = CountryGetModel


class CityCreateModel(CityOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__without_pk__'
    country = CountryCreateModel


class UserGetModel(UserOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'
    city = CityGetModel


class UserCreateModel(UserOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__without_pk__'
    city = CityCreateModel


@register_route('/users/', ('get', ))
async def get_users() -> list[UserGetModel]:
    async with db.create_session() as session:
        sql_query = select(
            UserOrm, CityOrm, CountryOrm
        ).select_from(UserOrm).join(CityOrm).join(CountryOrm)
        result = await session.execute(sql_query)

        users = []
        for user in result.fetchall():
            user_pydantic = UserGetModel.model_validate(user[0])
            user_dict = user_pydantic.model_dump()
            user_dict['birth_date'] = str(user_dict['birth_date'])
            users.append(user_dict)
    return json.dumps(users)


@register_route('/users/', ('post', ))
async def create_user(new_user: UserCreateModel) -> UserCreateModel:
    async with db.create_session() as session:
        async with session.begin():
            session.add(UserOrm(**dict(new_user)))
    return new_user.model_dump_json()


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

    try:
        controller = get_controller(path, method)
    except KeyError:
        # temp decision for not existing paths
        return

    if method == 'POST':
        types = controller.__annotations__
        for arg_name, arg_type in types.items():
            if issubclass(arg_type, BaseModel):
                body = parser.get_body()
                pydantic_object = arg_type.model_validate_json(body)
                response: str = await controller(**{arg_name: pydantic_object})
                break

    else:
        response: str = await controller()

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

    await listen_for_connection(server_socket, asyncio.get_event_loop())


if __name__ == '__main__':
    # uvloop.install()
    asyncio.run(main(), debug=True)
