from operator import itemgetter

from sqlalchemy import select

from database import DataBase
from routing import register_route
from users.data_classes import User
from users.models import CityOrm, CountryOrm, GenderOrm, LanguageOrm, UserOrm
from users.schemas import (user_create_schema, user_get_schema,
                           user_list_get_schema)

db = DataBase()


@register_route(
    '/users/', ('get', ),
    response_schema=user_list_get_schema,
    query_params={
        UserOrm: ['first_name', 'last_name'],
        CityOrm: ['name'],
        CountryOrm: ['name'],
        GenderOrm: ['name'],
    }
)
async def get_users(query_params) -> str:
    async with db.create_session() as session:
        sql_query = (
            select(
                UserOrm, CityOrm, CountryOrm, LanguageOrm, GenderOrm
            ).select_from(UserOrm)
            .outerjoin(CityOrm).outerjoin(CountryOrm)
            .outerjoin(LanguageOrm).outerjoin(GenderOrm)
            .filter(*query_params)
        )
        result = await session.execute(sql_query)
        return user_list_get_schema.dumps(map(itemgetter(0), result.fetchall()))


@register_route(
    '/users/', ('post', ),
    request_schema=user_create_schema,
    response_schema=user_get_schema,
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
            await session.flush()
            return user_get_schema.dump(user_obj)
