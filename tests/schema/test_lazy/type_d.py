from typing import TYPE_CHECKING, List
from typing_extensions import Annotated

import strawberry

if TYPE_CHECKING:
    from .type_e import TypeE
else:
    TypeE = Annotated["TypeE", strawberry.lazy(".type_e")]


@strawberry.input
class TypeDFilter:
    name: str


@strawberry.type
class TypeD:
    @strawberry.field
    def type_e(self) -> List[TypeE]:
        raise NotImplementedError()
