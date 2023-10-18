from chats.models import ChatOrm, MessageOrm
from database import DataBase, SqlAlchemyToMarshmallow
from users.schemas import UserSchema

db = DataBase()


class ChatSchema(ChatOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class ShortMessageSchema(MessageOrm, metaclass=SqlAlchemyToMarshmallow):
    pass


class MessageSchema(MessageOrm, metaclass=SqlAlchemyToMarshmallow):
    created_by = UserSchema(only=('pk', 'first_name', 'last_name'))
    reply_to_message = ShortMessageSchema(only=('pk', 'text', 'created_by_id'))


message_get_schema = MessageSchema(
    exclude=('reply_to_message', 'created_by_id', 'chat_id',),
    many=True,
    json_schema_name='MessageGetSchema',
)
message_create_schema = MessageSchema(
    exclude=('pk', 'created_by', 'reply_to_message'),
    json_schema_name='MessageCreateSchema',
)
chat_get_schema = ChatSchema(
    exclude=('last_message_id',),
    many=True,
    json_schema_name='ChatGetSchema',
)
chat_create_schema = ChatSchema(
    exclude=('last_message_id',),
    json_schema_name='ChatCreateSchema',
)
