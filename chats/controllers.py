from operator import itemgetter

from sqlalchemy import select

from chats.models import (
    UserOrm,
    MessageOrm,
    ChatOrm,
)
from chats.data_classes import Message, Chat
from chats.schemas import message_get_schema, message_create_schema, chat_create_schema, chat_get_schema
from database import (
    DataBase,
)
from routing import register_route

db = DataBase()


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
async def get_chats() -> list[Chat]:
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
async def create_chat(new_chat: Chat) -> Chat:
    async with db.create_session() as session:
        async with session.begin():
            message_obj = ChatOrm(
                name=new_chat.name,
                chat_type=new_chat.chat_type,
            )
            session.add(message_obj)
    return new_chat
