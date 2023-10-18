import enum
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ChatType(enum.Enum):
    DIRECT = 'direct'
    GROUP = 'group'
    SELF = 'self'


class ChatOrm(Base):
    __tablename__ = 'chats'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=True)
    chat_type: Mapped[ChatType] = mapped_column(default=ChatType.DIRECT)

    last_message_id: Mapped[int] = mapped_column(ForeignKey('users.pk'), nullable=True)
    last_message: Mapped['MessageOrm'] = relationship(back_populates='last_message_in_chat')
    messages: Mapped[list['MessageOrm']] = relationship(back_populates='chat')

    participants: Mapped[list['UserOrm']] = relationship(secondary=Table(
        "chats_to_users",
        Base.metadata,
        Column("chat_id", ForeignKey("chats.pk")),
        Column("user_id", ForeignKey("users.pk")),
    ))


class MessageOrm(Base):
    __tablename__ = 'messages'

    pk: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    date_time: Mapped[datetime] = mapped_column(default=datetime.now)

    created_by_id: Mapped[int] = mapped_column(ForeignKey('users.pk'))
    created_by: Mapped['UserOrm'] = relationship(back_populates='messages')

    chat_id: Mapped[int] = mapped_column(ForeignKey('chats.pk'))
    chat: Mapped['ChatOrm'] = relationship(back_populates='messages')
    last_message_in_chat: Mapped['ChatOrm'] = relationship(back_populates='last_message')

    reply_to_message_id: Mapped[int] = mapped_column(ForeignKey('messages.pk'), nullable=True)
    reply_to_message: Mapped['MessageOrm'] = relationship(remote_side=[pk])
