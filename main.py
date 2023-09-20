import asyncio
from operator import itemgetter
from sqlalchemy.exc import MissingGreenlet
import json
import socket
from asyncio import AbstractEventLoop
from datetime import date
from database import Base

from pydantic import BaseModel
from sqlalchemy import select

from database import (
    CityOrm,
    CountryOrm,
    DataBase,
    SqlAlchemyToPydantic,
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


class LanguageGetModel(LanguageOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'


class LanguageCreateModel(LanguageOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__without_pk__'


class GenderGetModel(GenderOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'


class GenderCreateModel(GenderOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__without_pk__'


class UserGetModel(UserOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'
    city = CityGetModel
    language = LanguageGetModel
    gender = GenderGetModel


class UserCreateModel(UserOrm, metaclass=SqlAlchemyToPydantic):
    fields = '__without_pk__'
    city = CityCreateModel
    language = LanguageCreateModel
    gender = GenderCreateModel


@register_route('/users/', ('get', ))
async def get_users() -> list[UserGetModel]:
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
        return [
            UserGetModel.model_validate(user)
            for user in map(lambda obj: make_dict_from_orm_object(obj[0]), users)
        ]


def make_dict_from_orm_object(origin):
    """pydantic method - model_validate if sees attribute of orm object,
    that equal to None, then model_validate crashes. And for this, i
    write the function, make_dict_from_orm_object if sees that attribute is None,
    then resulting object won't have the attribute"""
    new_obj = {}
    for attribute_name in dir(origin):
        if attribute_name.startswith('_'):
            continue

        try:
            attribute_value = getattr(origin, attribute_name, None)
        except MissingGreenlet:
            pass

        if isinstance(attribute_value, Base):
            new_obj[attribute_name] = make_dict_from_orm_object(attribute_value)
        if type(attribute_value) in {int, str, date}:
            new_obj[attribute_name] = attribute_value
    return new_obj



@register_route('/users/', ('post', ))
async def create_user(new_user: UserCreateModel) -> UserCreateModel:
    async with db.create_session() as session:
        async with session.begin():
            country = CountryOrm(name=new_user.city.country.name)
            city = CityOrm(country=country, name=new_user.city.name)
            language = LanguageOrm(name=new_user.language.name)
            gender = GenderOrm(name=new_user.gender.name)
            session.add(UserOrm(
                first_name=new_user.first_name,
                last_name=new_user.last_name,
                birth_date=new_user.birth_date,
                city=city,
                language=language,
                gender=gender,
            ))
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
        for arg_name, arg_type in types.items():
            if issubclass(arg_type, BaseModel):
                body = parser.get_body()
                pydantic_object = arg_type.model_validate_json(body)
                response = await controller(**{arg_name: pydantic_object})
                if isinstance(response, BaseModel):
                    response = response.model_dump_json()
                break
    else:
        response: str = await controller()
        if isinstance(response, list):
            python_dicts = [obj.model_dump() for obj in response]
            response = json.dumps(python_dicts, default=str)

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
