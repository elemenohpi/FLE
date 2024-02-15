""" Interface to the simulation inside the game, as well as our mod
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

import asyncio
import json
import logging
from enum import Enum

import cattrs
import cattrs.preconf.json
from attr import define, field
from cattrs.converters import is_optional as _is_optional

from . import rcon

LOG = logging.getLogger(__name__)


# TODO consider generating this stuff from the factorio API json
# https://lua-api.factorio.com/next/json-docs.html


@define
class Position:
    x: float
    y: float


def manhattan_distance(a: Position, b: Position) -> float:
    return abs(b.x - a.x) + abs(b.y - a.y)


class defines:  # pylint: disable=invalid-name
    class direction(Enum):
        north = "north"
        northeast = "northeast"
        east = "east"
        southeast = "southeast"
        south = "south"
        southwest = "southwest"
        west = "west"
        northwest = "northwest"


def get_direction_vector(direction: defines.direction) -> Position:
    # x points east, y points south
    vectors = {
        defines.direction.north: [0, -1],
        defines.direction.northeast: [1, -1],
        defines.direction.east: [1, 0],
        defines.direction.southeast: [1, 1],
        defines.direction.south: [0, 1],
        defines.direction.southwest: [-1, 1],
        defines.direction.west: [-1, 0],
        defines.direction.northwest: [-1, -1],
    }
    return Position(*vectors[direction])


def offset_pos(pos: Position, direction: defines.direction, multiple: int) -> Position:
    offset = get_direction_vector(direction)
    return Position(pos.x + (multiple * offset.x), pos.y + (multiple * offset.y))


def get_opposite_direction(direction: defines.direction) -> defines.direction:
    opposites = {
        defines.direction.north: defines.direction.south,
        defines.direction.northeast: defines.direction.southwest,
        defines.direction.east: defines.direction.west,
        defines.direction.southeast: defines.direction.northwest,
        defines.direction.south: defines.direction.north,
        defines.direction.southwest: defines.direction.northeast,
        defines.direction.west: defines.direction.east,
        defines.direction.northwest: defines.direction.southeast,
    }
    return opposites[direction]


@define
class CreateEntityParams:
    """See https://lua-api.factorio.com/latest/LuaSurface.html#LuaSurface.create_entity"""

    name: str
    position: Optional[Position]
    direction: Optional[defines.direction] = defines.direction.north
    force: Optional[str] = "player"
    surface: str = "nauvis"


@define
class EntityDescription:
    surface: str
    name: str
    position: Position
    direction: defines.direction
    force: str
    # Things like "item-on-ground" dont have unit_numbers
    # the = None default is required so that cattrs can handle
    # the absent key when structuring
    unit_number: Optional[int] = None


@define
class SimpleItemStack:
    name: str
    count: int


@define
class RpcRequest:
    method: str
    params: List[Any]


@define
class RpcError:
    code: int
    message: str
    data: Optional[Any] = None


# ReturnTypeT must be compatible with cattrs, but im not sure how to make that constraint official
ReturnTypeT = TypeVar("ReturnTypeT")


@define
class RpcResponse(Generic[ReturnTypeT]):
    result: Optional[ReturnTypeT] = None
    error: Optional[RpcError] = None


@define
class RpcException(Exception):
    message: str
    request: RpcRequest
    response: Optional[RpcResponse[Any]]

    def __str__(self):
        return f"${self.message} : {self.response} while calling {self.request}"


class Returns(Generic[ReturnTypeT]):
    if not TYPE_CHECKING:

        def __class_getitem__(cls, item: object) -> object:
            """Called when Returns is used as an Annotation at runtime.
            We just return the type we're given"""
            return item


@define
class World:
    rcon: rcon.RCONClient
    _initial_tick: int
    _cur_tick: int = field(init=False)
    _cur_target_tick: int = field(init=False)
    _converter = cattrs.preconf.json.make_converter()

    def __attrs_post_init__(self):
        self._cur_tick = self._initial_tick
        self._cur_target_tick = self._initial_tick
        # cattrs has what might be considered a bug. It inspects type annotations to determine
        # how to unstructure types. When it sees the List[Any] in a field, it then fails to find
        # a converter for typing.Any . This causes unstructuring to miss the elements of the list.
        # This unstructure hook tells cattrs to recurse on the actual object when it sees Any
        self._converter.register_unstructure_hook_func(
            lambda a: a is Any,
            self._converter.unstructure,
        )

    # We need to specify overloads for call_mod because the real type signature is a little too confusing for mypy
    # See https://github.com/python/mypy/issues/9003 for details of the limitation we're running in to.
    # Mainly it's the lack of something like TypeForm that allows represenatation of both runtime types and typing types

    # This signature handles "typing" types like Union / Optional, you need to wrap them in Returns[...]
    @overload
    async def call_mod(
        self,
        return_type: Type[Returns[ReturnTypeT]],
        method: str,
        params: Optional[List[Any]] = None,
    ) -> ReturnTypeT:
        pass

    # This signature handles "real" types like call_mod(int) or call_mod(SomeClass)
    @overload
    async def call_mod(
        self,
        return_type: Type[ReturnTypeT],
        method: str,
        params: Optional[List[Any]] = None,
    ) -> ReturnTypeT:
        pass

    @overload
    async def call_mod(
        self,
        return_type: None,
        method: str,
        params: Optional[List[Any]] = None,
    ) -> None:
        pass

    async def call_mod(
        self,
        return_type: Union[Type[Returns[ReturnTypeT]], Type[ReturnTypeT], None],
        method: str,
        params: Optional[List[Any]] = None,
    ) -> Optional[ReturnTypeT]:
        params = [] if params is None else params
        req = RpcRequest(method, params)
        unstructured_req = self._converter.unstructure(req)
        serialized_request = json.dumps(unstructured_req)
        # TODO: Add some kind of escaping
        if "'" in serialized_request:
            raise NotImplementedError(
                "rpc contains a single quote which will break the rcon call"
            )
        command = f"/silent-command rcon.print(remote.call('fle', 'call', '{serialized_request}'))"
        serialized_response = await self.rcon.send_command(command)
        json_response = json.loads(serialized_response)
        response = self._converter.structure(
            json_response, RpcResponse[return_type]  # type: ignore
        )
        if response.error is not None:
            raise RpcException("Received error", req, response)
        # because response.result is always optional (due to the error case),
        # we need an additional check on whether
        # None is valid as the return_type of the call.
        if response.result is None:
            if (
                return_type is not None
                and return_type is not type(None)
                and not _is_optional(return_type)
            ):
                raise RpcException("Unexpected None result", req, response)
        return response.result

    def get_current_tick(self):
        """The current tick
        This is relative to the tick at which the world was loaded
        """
        return self._cur_tick - self._initial_tick

    async def step(self, num_ticks: int) -> None:
        """Steps forward simulations by num_ticks, returns when complete"""
        self._cur_target_tick += num_ticks
        await self.call_mod(None, "step", [num_ticks])
        while self._cur_tick < self._cur_target_tick:
            await asyncio.sleep(0.05)
            cur_tick_str = await self.rcon.send_command(
                "/silent-command rcon.print(game.tick)"
            )
            self._cur_tick = int(cur_tick_str)
        assert (
            self._cur_tick == self._cur_target_tick
        ), "We lost precise control of time somehow"

    async def create_entities(
        self, entities: List[CreateEntityParams]
    ) -> List[Optional[EntityDescription]]:
        """Try to create a list of entities

        Returns an array of the same length as the input.
        Entities which fail the can_place_entity collision check are None, in the return array.
        Other Errors are raised as exceptions.
        Check the response list if you cannot accept any collision failures.
        """
        rpc_results = await asyncio.gather(
            *[
                self.call_mod(
                    Returns[Optional[EntityDescription]], "create_entity", [e]
                )
                for e in entities
            ],
            return_exceptions=True,
        )
        results: List[Optional[EntityDescription]] = []
        errors: List[Exception] = []
        for r in rpc_results:
            if isinstance(r, Exception):
                errors.append(r)
            else:
                results.append(r)
        if errors:
            for error in errors:
                LOG.error(repr(error))
            raise Exception("Errors encountered during create_entities, see logs")
        return results

    async def find_entities(
        self, area: Tuple[Position, Position], surface: Optional[str] = None
    ) -> List[EntityDescription]:
        surface = "nauvis" if surface is None else surface
        entities = await self.call_mod(
            List[EntityDescription], "find_entities", [area, surface]
        )
        return entities

    async def insert_items(
        self, entity_description: EntityDescription, item_stack: SimpleItemStack
    ) -> int:
        """Inserts the items in to the entity with the given name at the given position, on the given surface
        Raises errors if the entity lookup fails.
        Returns number of items inserted. May be less than total requested.
        """
        return await self.call_mod(
            int, "insert_items", [entity_description, item_stack]
        )

    async def get_inventory_contents(
        self, entity_description: EntityDescription
    ) -> Dict[str, int]:
        """Returns the inventory contents for the entity with the given name at the given position, on the given surface.
        Raises errors if the entity lookup fails.
        """
        return await self.call_mod(
            Returns[Dict[str, int]], "get_inventory_contents", [entity_description]
        )

    async def destroy_all_entities(self, surface: str = "nauvis") -> None:
        """A light-weight version of https://lua-api.factorio.com/latest/LuaSurface.html#LuaSurface.clear

        Unlike LuaSurface.clear, it does not delete the chunks themselves, thus avoiding a slightly costly regeneration process.
        """
        return await self.call_mod(None, "destroy_all_entities", [surface])
