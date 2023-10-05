from database import MarshmallowToDataclass
from users.schemas import (
    CountrySchema,
    LanguageSchema,
    GenderSchema,
    CitySchema,
    UserSchema,
)


class Country(CountrySchema, metaclass=MarshmallowToDataclass):
    pass


class Language(LanguageSchema, metaclass=MarshmallowToDataclass):
    pass


class Gender(GenderSchema, metaclass=MarshmallowToDataclass):
    pass


class City(CitySchema, metaclass=MarshmallowToDataclass):
    country: Country = None


class User(UserSchema, metaclass=MarshmallowToDataclass):
    city: City = None
    language: Language = None
    gender: Gender = None
