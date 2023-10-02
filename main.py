import asyncio
from dacite import from_dict
import dataclasses
from marshmallow import Schema
from operator import itemgetter
from sqlalchemy.exc import MissingGreenlet
import json
import socket
from asyncio import AbstractEventLoop
from datetime import date
from database import Base

from sqlalchemy import select

from database import (
    CityOrm,
    CountryOrm,
    DataBase,
    SqlAlchemyToMarshmallow,
    MarshmallowToDataclass,
    UserOrm,
    GenderOrm,
    LanguageOrm,
)
from http_headers import HttpHeadersParser, create_response_headers
from openapi import openapi_object, write_pydantic_models_to_openapi
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


class CountrySchema(CountryOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class LanguageSchema(LanguageOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class GenderSchema(GenderOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class CitySchema(CityOrm, metaclass=SqlAlchemyToMarshmallow):
    country = CountrySchema


class UserSchema(UserOrm, metaclass=SqlAlchemyToMarshmallow):
    city = CitySchema
    language = LanguageSchema
    gender = GenderSchema


class Country(CountrySchema, metaclass=MarshmallowToDataclass):
    pass


class Language(LanguageSchema, metaclass=MarshmallowToDataclass):
    pass


class Gender(GenderSchema, metaclass=MarshmallowToDataclass):
    pass


class City(CitySchema, metaclass=MarshmallowToDataclass):
    country: Country = None


class User(UserSchema, metaclass=MarshmallowToDataclass):
    city: City = None
    language: Language = None
    gender: Gender = None


user_create_schema = UserSchema(exclude=('pk',), json_schema_name='UserCreateSchema')
user_get_schema = UserSchema(many=True, json_schema_name='UserGetSchema')


@register_route(
    '/users/', ('get', ),
    response=user_get_schema,
)
async def get_users() -> list[User]:
    async with db.create_session() as session:
        sql_query = (
            select(
                UserOrm, CityOrm, CountryOrm, LanguageOrm, GenderOrm
            ).select_from(UserOrm)
            .outerjoin(CityOrm).outerjoin(CountryOrm)
            .outerjoin(LanguageOrm).outerjoin(GenderOrm)
        )

        result = await session.execute(sql_query)
        users = result.fetchall()
        schema = UserSchema(many=True)
        return schema.dump(map(itemgetter(0), users))


@register_route(
    '/users/', ('post', ),
    request=user_create_schema,
    response=user_create_schema,
)
async def create_user(new_user: User) -> User:
    async with db.create_session() as session:
        async with session.begin():
            country = CountryOrm(name=new_user.city.country.name)
            city = CityOrm(country=country, name=new_user.city.name)
            language = LanguageOrm(name=new_user.language.name)
            gender = GenderOrm(name=new_user.gender.name)
            user_obj = UserOrm(
                first_name=new_user.first_name,
                last_name=new_user.last_name,
                birth_date=new_user.birth_date,
                city=city,
                language=language,
                gender=gender,
            )
            session.add(user_obj)
    return new_user


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
                    response = controller_schema.dumps(response)
                break
    else:
        response: str = await controller()
        if isinstance(response, list):
            #python_dicts = [obj.model_dump() for obj in response]
            #response = json.dumps(python_dicts, default=str)
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
