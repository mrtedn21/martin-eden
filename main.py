import asyncio
from dacite import from_dict
import dataclasses
from operator import itemgetter
import json
import socket
from asyncio import AbstractEventLoop

from sqlalchemy import select
from sqlalchemy.orm import aliased

from database import (
    CityOrm,
    CountryOrm,
    DataBase,
    SqlAlchemyToMarshmallow,
    MarshmallowToDataclass,
    UserOrm,
    GenderOrm,
    LanguageOrm,
    MessageOrm,
    ChatOrm,
)
from http_headers import HttpHeadersParser, create_response_headers
from openapi import openapi_object, write_pydantic_models_to_openapi
from routing import get_controller, register_route

db = DataBase()


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


#class ShortMessageSchema(MessageOrm, metaclass=SqlAlchemyToMarshmallow):
#    pass


class ChatSchema(ChatOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class ShortMessageSchema(MessageOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class MessageSchema(MessageOrm, metaclass=SqlAlchemyToMarshmallow):
    created_by = UserSchema(only=('pk', 'first_name', 'last_name'))
    reply_to_message = ShortMessageSchema(only=('pk', 'text', 'created_by_id'))


class Country(CountrySchema, metaclass=MarshmallowToDataclass):
    pass


class Language(LanguageSchema, metaclass=MarshmallowToDataclass):
    pass


class Gender(GenderSchema, metaclass=MarshmallowToDataclass):
    pass


class City(CitySchema, metaclass=MarshmallowToDataclass):
    country: Country = None


class Chat(ChatSchema, metaclass=MarshmallowToDataclass):
    pass


class User(UserSchema, metaclass=MarshmallowToDataclass):
    city: City = None
    language: Language = None
    gender: Gender = None


class Message(MessageSchema, metaclass=MarshmallowToDataclass):
    created_by: User = None
    reply_to_message: "Message" = None


user_create_schema = UserSchema(exclude=('pk', 'city_id', 'language_id', 'gender_id'), json_schema_name='UserCreateSchema')
user_get_schema = UserSchema(exclude=('pk', 'city_id', 'language_id', 'gender_id'), many=True, json_schema_name='UserGetSchema')
message_get_schema = MessageSchema(exclude=('reply_to_message', 'created_by_id', 'chat_id',), many=True, json_schema_name='MessageGetSchema')
message_create_schema = MessageSchema(exclude=('pk', 'created_by', 'reply_to_message'), json_schema_name='MessageCreateSchema')
#chat_get_schema = ChatSchema(exclude=('participants', 'messages', 'last_message_id'), many=True, json_schema_name='ChatGetSchema')
#chat_create_schema = ChatSchema(exclude=('participants', 'messages', 'last_message', 'last_message_id'), json_schema_name='ChatCreateSchema')

chat_get_schema = ChatSchema(exclude=('last_message_id',), many=True, json_schema_name='ChatGetSchema')
chat_create_schema = ChatSchema(exclude=('last_message_id',), json_schema_name='ChatCreateSchema')

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


@register_route(
    '/messages/', ('get', ),
    response=message_get_schema,
)
async def get_messages() -> list[Message]:
    async with db.create_session() as session:
        sql_query = (
            select(
                MessageOrm, UserOrm
            ).select_from(MessageOrm)
            .outerjoin(UserOrm)
        )

        result = await session.execute(sql_query)
        messages = result.fetchall()
        return message_get_schema.dump(map(itemgetter(0), messages))


@register_route(
    '/messages/', ('post',),
    request=message_create_schema,
    response=message_create_schema,
)
async def create_message(new_message: Message) -> Message:
    async with db.create_session() as session:
        async with session.begin():
            message_obj = MessageOrm(
                chat_id=new_message.chat_id,
                created_by_id=new_message.created_by_id,
                date_time=new_message.date_time.replace(tzinfo=None),
                reply_to_message_id=new_message.reply_to_message_id,
                text=new_message.text,
            )
            session.add(message_obj)
    return new_message


@register_route(
    '/chats/', ('get', ),
    response=chat_get_schema,
)
async def get_messages() -> list[Chat]:
    async with db.create_session() as session:
        sql_query = (select(ChatOrm))
        result = await session.execute(sql_query)
        chats = result.fetchall()
        return chat_get_schema.dump(map(itemgetter(0), chats))


@register_route(
    '/chats/', ('post',),
    request=chat_create_schema,
    response=chat_create_schema,
)
async def create_message(new_chat: Chat) -> Chat:
    async with db.create_session() as session:
        async with session.begin():
            message_obj = ChatOrm(
                name=new_chat.name,
                chat_type=new_chat.chat_type,
            )
            session.add(message_obj)
    return new_chat


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
