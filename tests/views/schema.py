import asyncio
import typing
from enum import Enum

from graphql import GraphQLError

import strawberry
from strawberry.channels.context import StrawberryChannelsContext
from strawberry.extensions import SchemaExtension
from strawberry.file_uploads import Upload
from strawberry.permission import BasePermission
from strawberry.subscriptions.protocols.graphql_transport_ws.types import PingMessage
from strawberry.types import Info


class AlwaysFailPermission(BasePermission):
    message = "You are not authorized"

    def has_permission(self, source, info, **kwargs) -> bool:
        return False


class MyExtension(SchemaExtension):
    def get_results(self) -> typing.Dict[str, str]:
        return {"example": "example"}


def _read_file(text_file: Upload) -> str:
    from starlette.datastructures import UploadFile

    # allow to keep this function synchronous, starlette's files have
    # async methods for reading
    if isinstance(text_file, UploadFile):
        text_file = text_file.file._file  # type: ignore

    return text_file.read().decode()


@strawberry.enum
class Flavor(Enum):
    VANILLA = "vanilla"
    STRAWBERRY = "strawberry"
    CHOCOLATE = "chocolate"


@strawberry.input
class FolderInput:
    files: typing.List[Upload]


@strawberry.type
class DebugInfo:
    num_active_result_handlers: int
    is_connection_init_timeout_task_done: typing.Optional[bool]


@strawberry.type
class Query:
    @strawberry.field
    def greetings(self) -> str:
        return "hello"

    @strawberry.field
    def hello(self, name: typing.Optional[str] = None) -> str:
        return f"Hello {name or 'world'}"

    @strawberry.field
    async def async_hello(
        self, name: typing.Optional[str] = None, delay: float = 0
    ) -> str:
        await asyncio.sleep(delay)
        return f"Hello {name or 'world'}"

    @strawberry.field(permission_classes=[AlwaysFailPermission])
    def always_fail(self) -> typing.Optional[str]:
        return "Hey"

    @strawberry.field
    async def exception(self, message: str) -> str:
        raise ValueError(message)
        return message

    @strawberry.field
    def teapot(self, info: Info[typing.Any, None]) -> str:
        info.context["response"].status_code = 418

        return "🫖"

    @strawberry.field
    def root_name(self) -> str:
        return type(self).__name__

    @strawberry.field
    def value_from_context(self, info: Info) -> str:
        return info.context["custom_value"]

    @strawberry.field
    def returns_401(self, info: Info) -> str:
        response = info.context["response"]

        if hasattr(response, "set_status"):
            response.set_status(401)
        else:
            response.status_code = 401

        return "hey"


@strawberry.type
class Mutation:
    @strawberry.mutation
    def echo(self, string_to_echo: str) -> str:
        return string_to_echo

    @strawberry.mutation
    def hello(self) -> str:
        return "strawberry"

    @strawberry.mutation
    def read_text(self, text_file: Upload) -> str:
        return _read_file(text_file)

    @strawberry.mutation
    def read_files(self, files: typing.List[Upload]) -> typing.List[str]:
        return list(map(_read_file, files))

    @strawberry.mutation
    def read_folder(self, folder: FolderInput) -> typing.List[str]:
        return list(map(_read_file, folder.files))

    @strawberry.mutation
    def match_text(self, text_file: Upload, pattern: str) -> str:
        text = text_file.read().decode()
        return pattern if pattern in text else ""


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def echo(
        self, message: str, delay: float = 0
    ) -> typing.AsyncGenerator[str, None]:
        await asyncio.sleep(delay)
        yield message

    @strawberry.subscription
    async def request_ping(self, info) -> typing.AsyncGenerator[bool, None]:
        ws = info.context["ws"]
        await ws.send_json(PingMessage().as_dict())
        yield True

    @strawberry.subscription
    async def infinity(self, message: str) -> typing.AsyncGenerator[str, None]:
        while True:
            yield message
            await asyncio.sleep(1)

    @strawberry.subscription
    async def context(self, info) -> typing.AsyncGenerator[str, None]:
        yield info.context["custom_value"]

    @strawberry.subscription
    async def error(self, message: str) -> typing.AsyncGenerator[str, None]:
        yield GraphQLError(message)  # type: ignore

    @strawberry.subscription
    async def exception(self, message: str) -> typing.AsyncGenerator[str, None]:
        raise ValueError(message)

        # Without this yield, the method is not recognised as an async generator
        yield "Hi"

    @strawberry.subscription
    async def flavors(self) -> typing.AsyncGenerator[Flavor, None]:
        yield Flavor.VANILLA
        yield Flavor.STRAWBERRY
        yield Flavor.CHOCOLATE

    @strawberry.subscription
    async def debug(self, info) -> typing.AsyncGenerator[DebugInfo, None]:
        active_result_handlers = [
            task for task in info.context["tasks"].values() if not task.done()
        ]

        connection_init_timeout_task = info.context["connectionInitTimeoutTask"]
        is_connection_init_timeout_task_done = (
            connection_init_timeout_task.done()
            if connection_init_timeout_task
            else None
        )

        yield DebugInfo(
            num_active_result_handlers=len(active_result_handlers),
            is_connection_init_timeout_task_done=is_connection_init_timeout_task_done,
        )

    @strawberry.subscription
    async def listener(
        self,
        info: Info[StrawberryChannelsContext, typing.Any],
        timeout: typing.Optional[float] = None,
        group: typing.Optional[str] = None,
    ) -> typing.AsyncGenerator[str, None]:
        yield info.context.request.channel_name

        async for message in info.context.request.channel_listen(
            type="test.message",
            timeout=timeout,
            groups=[group] if group is not None else [],
        ):
            yield message["text"]

    @strawberry.subscription
    async def connection_params(self, info) -> typing.AsyncGenerator[str, None]:
        yield info.context["connection_params"]["strawberry"]


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    extensions=[MyExtension],
)
