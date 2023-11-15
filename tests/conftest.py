import json
from sqlalchemy.orm import Mapped, mapped_column

from martin_eden.database import (Base, MarshmallowToDataclass,
                                  SqlAlchemyToMarshmallow)
from martin_eden.routing import register_route

base_http_request = (
    'GET /users/ HTTP/1.1\n'
    'Host: localhost:8001\n'
    'Connection: keep-alive\n'
    'sec-ch-ua: "Chromium";v="118", "Google Chrome";v="118", '
    '"Not=A?Brand";v="99"\n'
    'sec-ch-ua-mobile: ?0\n'
    'sec-ch-ua-platform: "macOS"\n'
    'Upgrade-Insecure-Requests: 1\n'
    'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 '
    'Safari/537.36\n'
    'Accept: text/html,application/xhtml+xml,application/xml;'
    'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
    'application/signed-exchange;v=b3;q=0.7\n'
    'Sec-Fetch-Site: none\n'
    'Sec-Fetch-Mode: navigate\n'
    'Sec-Fetch-User: ?1\n'
    'Sec-Fetch-Dest: document\n'
    'Accept-Encoding: gzip, deflate, br\n'
    'Accept-Language: en-US,en;q=0.9,ru;q=0.8,ru-RU;q=0.7\n'
    'Cookie: token=a0966813f9b27b2a545c75966fd87815660787a3; '
    'person_pk=1; csrftoken=3fQjKaaBDsfYyAERtNK9rZpY2gX2yQWl; '
    'session=bc8145dc-7e09-46f5-b5fa-789863559f3a.'
    'EetDaRq0uVnaC8vMKj2YhEYL5Fs\n'
)

# These headers are makes by framework
# And needs to compare in asserts
base_http_result_headers = (
    'HTTP/1.0 200\n'
    'Access-Control-Allow-Origin: *\n'
    'Access-Control-Allow-Methods: POST, GET, OPTIONS\n'
    'Access-Control-Allow-Headers: origin, content-type, accept\n'
    'Access-Control-Allow-Credentials: true\n'
    'Access-Control-Max-Age: 86400\n\n'
)


class TestModel(Base):
    __tablename__ = 'test'
    __table_args__ = {'extend_existing': True}
    pk: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]


class TestSchema(TestModel, metaclass=SqlAlchemyToMarshmallow):
    pass


class TestDataclass(TestSchema, metaclass=MarshmallowToDataclass):
    pass


@register_route(
    '/test_query/', 'get',
    response_schema=TestSchema(),
    query_params={TestModel: ['name', 'age']},
)
async def get_users(query_params: list) -> str:
    return json.dumps(list(map(str, query_params)))


@register_route('/test/', 'get')
async def get_openapi_schema() -> str:
    return 'test'


@register_route(
    '/test/', 'post',
    request_schema=TestSchema(),
    response_schema=TestSchema(),
)
async def create_test(test: TestDataclass) -> list[TestDataclass]:
    return [test.pk, test.name, test.age]
