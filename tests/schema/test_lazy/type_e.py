from typing import TYPE_CHECKING, List, Optional
from typing_extensions import Annotated

import strawberry

if TYPE_CHECKING:
    from .type_d import TypeD, TypeDFilter
else:
    TypeD = Annotated["TypeD", strawberry.lazy(".type_d")]
    TypeDFilter = Annotated["TypeDFilter", strawberry.lazy(".type_d")]


@strawberry.type
class TypeE:
    @strawberry.field
    def type_d(self, filter: Optional[TypeDFilter]) -> List[TypeD]:
        raise NotImplementedError()
