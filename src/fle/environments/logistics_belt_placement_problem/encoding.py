""" Handles conversion between the `world` api domain and the integer matrix domain of the belt problem"""
from typing import List, Optional

import math

import numpy as np
import numpy.typing as npt
from attr import define

from ...factorio_server import world

# entities we care to encode
ENTITY_TYPES = [
    "fast-transport-belt",
    "stone-wall",
    "fle-void-fast-inserter",
    "steel-chest",
]

# directions we care to encode
DIRECTIONS = [
    world.defines.direction.north,
    world.defines.direction.east,
    world.defines.direction.south,
    world.defines.direction.west,
]


@define
class EntityNameAndDirection:
    name: str
    direction: world.defines.direction


def encode_entity(e: EntityNameAndDirection) -> int:
    assert e.name in ENTITY_TYPES, "Un-encodable entity"
    assert e.direction in DIRECTIONS, "Un-encodable direction"
    # +1 for the zero which == empty space
    return (
        (ENTITY_TYPES.index(e.name) * len(DIRECTIONS))
        + DIRECTIONS.index(e.direction)
        + 1
    )


def get_max_encoded_action_value_exclusive():
    return 6  # empty space + 4 belts


def get_max_encoded_observation_value_exclusive():
    """Returns 1 past the lagest valid number the encoder can produce"""
    return encode_entity(EntityNameAndDirection(ENTITY_TYPES[-1], DIRECTIONS[-1]))


def decode_entity(num: int) -> Optional[EntityNameAndDirection]:
    """Returns None for un-decodable input"""
    # -1 for the zero which == empty space
    type_index, direction_index = divmod(num - 1, len(DIRECTIONS))
    if type_index < len(ENTITY_TYPES):
        return EntityNameAndDirection(
            ENTITY_TYPES[type_index], DIRECTIONS[direction_index]
        )
    return None


def encode_observation(
    dimension: int, entities: List[world.EntityDescription]
) -> npt.NDArray[np.uint8]:
    result = np.zeros((dimension + 4, dimension + 4), dtype=np.uint8)
    for entity in entities:
        if entity.name not in ENTITY_TYPES:
            # Disregard entities which we are not encoding
            continue
        # Factorio reports in floating coords, using the midpoint of squares
        x = math.floor(entity.position.x)
        y = math.floor(entity.position.y)
        # Offset by 2 for the walls
        x += 2
        y += 2
        cur_value = result[x, y]
        assert cur_value == 0, "Entity overlap was unexpected"
        result[x, y] = encode_entity(
            EntityNameAndDirection(entity.name, entity.direction)
        )
    return result


def decode_action(
    dimension: int, _matrix: npt.ArrayLike
) -> List[world.CreateEntityParams]:
    matrix = np.asarray(_matrix)
    assert len(matrix) == dimension
    entities_to_construct = []
    for x, col in enumerate(matrix):
        assert len(col) == dimension
        for y, encoded_entity in enumerate(col):
            name_and_direction = decode_entity(encoded_entity)
            if name_and_direction is not None:
                # The only item we allow creation of atm
                if name_and_direction.name == "fast-transport-belt":
                    entities_to_construct.append(
                        world.CreateEntityParams(
                            name_and_direction.name,
                            world.Position(x, y),
                            name_and_direction.direction,
                        )
                    )
    return entities_to_construct
