from chats.schemas import ChatSchema, MessageSchema
from database import MarshmallowToDataclass
from users.data_classes import User


class Chat(ChatSchema, metaclass=MarshmallowToDataclass):
    pass


class Message(MessageSchema, metaclass=MarshmallowToDataclass):
    created_by: User = None
    reply_to_message: "Message" = None
