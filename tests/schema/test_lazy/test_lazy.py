import textwrap
from typing import Optional, _eval_type  # type: ignore
from typing_extensions import Annotated

import pytest

import strawberry
from strawberry.printer import print_schema


def test_cyclic_import():
    from .type_a import TypeA
    from .type_b import TypeB

    @strawberry.type
    class Query:
        a: TypeA
        b: TypeB

    expected = """
    type Query {
      a: TypeA!
      b: TypeB!
    }

    type TypeA {
      listOfB: [TypeB!]
      typeB: TypeB!
    }

    type TypeB {
      typeA: TypeA!
    }
    """

    schema = strawberry.Schema(Query)

    assert print_schema(schema) == textwrap.dedent(expected).strip()


def test_infinite_recursion_on_field_argument():
    """Ensure infinite recursion doesn't occur when lazy type is used in an argument."""
    from .type_d import TypeD
    from .type_e import TypeE

    @strawberry.type
    class Query:
        d: TypeD
        e: TypeE

    expected = """
    type Query {
      d: TypeD!
      e: TypeE!
    }

    type TypeD {
      typeE: [TypeE!]!
    }

    input TypeDFilter {
      name: String!
    }

    type TypeE {
      typeD(filter: TypeDFilter): [TypeD!]!
    }
    """

    schema = strawberry.Schema(Query)

    assert print_schema(schema) == textwrap.dedent(expected).strip()


@pytest.mark.xfail(strict=True, raises=RecursionError)
def test_recursion_error_eval_type():
    """Test infinite recursion on `_eval_type` with Generic Alias and Annotated.

    This edge-case is caused when the type name referenced within an `Annotated` type
    is assigned to a type alias of the same name. This leads to the evaluated type
    returning a `ForwardRef` to the same type name, causing infinite recursion.

    This test demonstrates that this behavior is not caused by `strawberry.lazy`.
    """

    class Foo:
        pass

    FooType = Annotated["Foo", None]

    try:
        _eval_type(Optional[FooType], globals(), locals())
    except RecursionError:
        raise RuntimeError(
            "Recursion error should not have been raised when a variable name "
            "that is different than the foward referenced type is used."
        )

    Foo = Annotated["Foo", None]  # type: ignore # noqa: F811

    _eval_type(Optional[Foo], globals(), locals())


def test_recursion_error_eval_type_stringified():
    Foo = Annotated["Foo", None]  # type: ignore

    type = _eval_type("Optional[Foo]", globals(), locals())


def test_recursion_error_eval_type_partial_stringified():
    class Foo:
        pass

    type = _eval_type(Optional["Foo"], globals(), locals())
    assert type == Optional[Foo]
