from users.models import (
    CityOrm,
    CountryOrm,
    UserOrm,
    GenderOrm,
    LanguageOrm,
)

from database import SqlAlchemyToMarshmallow


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


user_create_schema = UserSchema(
    exclude=('pk', 'city_id', 'language_id', 'gender_id'),
    json_schema_name='UserCreateSchema',
)
user_list_get_schema = UserSchema(
    exclude=('city_id', 'language_id', 'gender_id'),
    many=True,
    json_schema_name='UserGetSchema',
)
user_get_schema = UserSchema(
    exclude=('city_id', 'language_id', 'gender_id'),
    json_schema_name='UserGetSchema',
)
