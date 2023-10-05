from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from database import Base


class UserOrm(Base):
    __tablename__ = 'users'

    pk: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date: Mapped[date]
    messages: Mapped['MessageOrm'] = relationship(back_populates='created_by')

    city_id: Mapped[int] = mapped_column(
        ForeignKey('cities.pk'), nullable=True,
    )
    city: Mapped['CityOrm'] = relationship(back_populates='city_users')

    language_id: Mapped[int] = mapped_column(
        ForeignKey('languages.pk'), nullable=True,
    )
    language: Mapped['LanguageOrm'] = relationship(back_populates='language_users')

    gender_id: Mapped[int] = mapped_column(
        ForeignKey('genders.pk'), nullable=True,
    )
    gender: Mapped['GenderOrm'] = relationship(back_populates='gender_users')


class CityOrm(Base):
    __tablename__ = 'cities'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country_id: Mapped[int] = mapped_column(ForeignKey('countries.pk'))
    country: Mapped['CountryOrm'] = relationship(back_populates='cities')
    city_users: Mapped[list['UserOrm']] = relationship(back_populates='city')


class CountryOrm(Base):
    __tablename__ = 'countries'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    cities: Mapped[list['CityOrm']] = relationship(back_populates='country')


class LanguageOrm(Base):
    __tablename__ = 'languages'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    language_users: Mapped[list['UserOrm']] = relationship(back_populates='language')


class GenderOrm(Base):
    __tablename__ = 'genders'

    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    gender_users: Mapped[list['UserOrm']] = relationship(back_populates='gender')
