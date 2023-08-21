import asyncio
from pydantic import ConfigDict
import socket
from asyncio import AbstractEventLoop
from datetime import datetime
from pydantic import create_model

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (AsyncAttrs, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from http_headers import HttpHeadersParser, create_response_headers
from routing import get_controller, register_route


class Base(AsyncAttrs, DeclarativeBase):
    pass


def get_json_from_orm_object(some_object):
    result_data = {}
    for attr in dir(some_object):
        attr_type = type(getattr(some_object, attr))
        if attr.startswith('_'):
            continue

        if attr_type in (str, int):
            result_data[attr] = getattr(some_object, attr)
        elif attr_type == datetime:
            date_time: datetime = getattr(some_object, attr)
            str_date_time = date_time.strftime('%d-%m-%Y')
            result_data[attr] = str_date_time

    return result_data


class SqlAlchemyToPydantic(type(Base)):
    """
    Metaclass that look and sql alchemy model fields, creates pydantic model

    Example:
    class NewModel(SomeSqlAlchemyModel, metaclass=SqlAlchemyToPydantic):
        fields = '__all__'

    fields attribute can be on of:
    * '__all__' - means that pydantic model will be with all fields of alchemy model
    * '__without_pk__' - means will be all fields instead of pk
    * tuple[str] - is tuple of fields that will be used
    """
    def __new__(cls, name, bases, fields):
        origin_model = bases[0]

        origin_model_field_names = [
            field_name for field_name in dir(origin_model)
            if not field_name.startswith('_')
            and field_name not in ('registry', 'metadata', 'awaitable_attrs')
        ]

        defined_fields = fields['fields']
        if defined_fields == '__all__':
            defined_fields = origin_model_field_names
        elif defined_fields == '__without_pk__':
            defined_fields = tuple(set(origin_model_field_names) - {'pk'})

        result_fields = {
            field_name: (getattr(origin_model, field_name).type.python_type, ...)
            for field_name in defined_fields
            if field_name in origin_model_field_names
        }
        return create_model(
            'UserReadModel',
            **result_fields,
            __config__=ConfigDict(from_attributes=True),
        )


class User(Base):
    __tablename__ = 'users'

    pk: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    # TODO fix datetime to date
    birth_date: Mapped[datetime]


class UserReadModel(User, metaclass=SqlAlchemyToPydantic):
    fields = '__all__'


@register_route('/', ('get',))
async def root() -> str:
    engine = create_async_engine(
        'postgresql+asyncpg://alexander.bezgin:123@localhost/framework',
        echo=True,
    )

    async with engine.begin() as conn:
        print('now will create tables')
        await conn.run_sync(Base.metadata.create_all)
        print('tables has created')

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    #async with async_session() as session:
    #    async with session.begin():
    #        session.add_all([
    #            UserOrm(
    #                first_name='test1',
    #                last_name='test1',
    #                birth_date=datetime.now(),
    #            ),
    #            UserOrm(
    #                first_name='test2',
    #                last_name='test2',
    #                birth_date=datetime.now(),
    #            ),
    #        ])

    async with async_session() as session:
        sql_query = select(User)
        result = await session.execute(sql_query)
        users = result.scalars().all()

        pyd_user = UserReadModel.model_validate(users[0])

    await engine.dispose()
    return pyd_user.model_dump_json()


async def handle_request(
    client_socket: socket.socket, loop: AbstractEventLoop,
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
    response: str = await controller()

    headers = create_response_headers(200, 'application/json')
    await loop.sock_sendall(
        client_socket, (headers + response).encode('utf8'),
    )
    client_socket.close()


async def listen_for_connection(
    server_socket: socket, loop: AbstractEventLoop,
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
