"""Index of and generator of belt placement Problems"""
from typing import List, Optional

import random
import sys
from abc import ABC, abstractmethod

from attr import define, field

from ...factorio_server import world


@define
class Transform:
    position: world.Position
    direction: world.defines.direction


def random_position(x_excl: int, y_excl: int, prng: random.Random) -> world.Position:
    return world.Position(prng.randrange(x_excl), prng.randrange(y_excl))


_MAX_PATH_LENGTH_FACTOR = 4  # 4 times the side length is a tour of the entire space
_MAX_ITEMS_PER_BELT_TILE = 4
_FAST_TRANSPORT_BELT_TRAVEL_SPEED = 3.75 / 60  # tiles per-tick
_FAST_INSERTER_TICKS_PER_ROTATION = 26


@define
class Problem:
    dimension: int
    input_location: Transform
    output_location: Transform
    wall_obstacles: List[world.Position]
    input_ore_quantity: int = field()

    @input_ore_quantity.default
    def _default_input_ore_quantity(self):
        return self.dimension * _MAX_PATH_LENGTH_FACTOR * _MAX_ITEMS_PER_BELT_TILE

    ticks_for_evaluation: int = field()

    @ticks_for_evaluation.default
    def _default_ticks_for_evaluation(self):
        # Enough time to unload all the ore and do one more _MAX_PATH_LENGTH_FACTOR of journey
        return round(
            (self.input_ore_quantity * _FAST_INSERTER_TICKS_PER_ROTATION)
            + (
                (self.dimension * _MAX_PATH_LENGTH_FACTOR)
                / _FAST_TRANSPORT_BELT_TRAVEL_SPEED
            )
        )

    def get_input_chest_pos(self) -> world.Position:
        return world.offset_pos(
            self.input_location.position, self.input_location.direction, 1
        )

    def get_output_chest_pos(self) -> world.Position:
        return world.offset_pos(
            self.output_location.position, self.output_location.direction, -1
        )


def generate_problem(dimension: int, prng: random.Random) -> Problem:
    """Generates problems. Should be deterministic given the same prng state.
    A small fraction of problems may actually be un-solvable."""

    def random_outer_edge_pos(for_input):
        # possible positions are four times the side-length
        # sample a position and translate to a coordinate
        linear_pos = prng.randrange(dimension * 4)

        def linear_to_outer_edge_pos(i: int) -> Transform:
            edge = i % 4
            offset = i // 4
            #         3rd edge
            #            __
            # 1st edge  |__|  2nd edge
            #
            #          4th edge
            x = [-1, dimension, offset, offset][edge]
            y = [offset, offset, -1, dimension][edge]
            # inserter direction points towards the collection side
            direction = [
                world.defines.direction.east,
                world.defines.direction.west,
                world.defines.direction.south,
                world.defines.direction.north,
            ][edge]
            if for_input:
                direction = world.get_opposite_direction(direction)
            return Transform(world.Position(x, y), direction)

        return linear_to_outer_edge_pos(linear_pos)

    input_location = random_outer_edge_pos(True)
    output_location = random_outer_edge_pos(False)
    # we dont want a situation where the input already feeds the output (or is the same space either)
    while (
        world.manhattan_distance(input_location.position, output_location.position) < 3
    ):
        output_location = random_outer_edge_pos(False)
    input_drop_location = world.offset_pos(
        input_location.position, input_location.direction, -1
    )
    output_grab_location = world.offset_pos(
        output_location.position, output_location.direction, 1
    )
    wall_obstacles = []
    # dimension - 1 helps to avoid partitioning the space entirely
    # we could fit more obstacles if we bother to ensure solve-ablity
    for _ in range(dimension - 1):
        # Arbitrary iteration limit to avoid infinite loops
        for _ in range(1000):
            wall_pos = random_position(dimension, dimension, prng)
            if wall_pos == input_drop_location:
                continue
            if wall_pos == output_grab_location:
                continue
            if wall_pos in wall_obstacles:
                continue
            break
        else:
            raise Exception("Generation failed to add valid walls")
        wall_obstacles.append(wall_pos)
    return Problem(dimension, input_location, output_location, wall_obstacles)


class ProblemClass(ABC):
    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def get_instance(self) -> Problem:
        pass

    @abstractmethod
    def seed(self, seed: Optional[int]) -> None:
        pass

    @abstractmethod
    def get_seed(self) -> int:
        pass


@define
class StaticProblem(ProblemClass):
    problem: Problem

    def get_dimension(self) -> int:
        return self.problem.dimension

    def get_instance(self):
        return self.problem

    def seed(self, seed: Optional[int]) -> None:
        """Static problems aren't random"""

    def get_seed(self) -> int:
        """Static problems aren't random"""
        return 0


def _fix_seed(seed: Optional[int]) -> int:
    return random.randint(0, sys.maxsize) if seed is None else seed


@define
class DynamicProblem(ProblemClass):
    dimension: int
    _seed: int = _fix_seed(None)
    _prng = random.Random()

    def __attrs_post_init__(self):
        self._prng.seed(self._seed)

    def get_dimension(self) -> int:
        return self.dimension

    def get_instance(self):
        return generate_problem(self.dimension, self._prng)

    def seed(self, seed: Optional[int]) -> None:
        self._seed = _fix_seed(seed)
        self._prng.seed(self._seed)

    def get_seed(self) -> int:
        return self._seed


@define
class _ProblemCategory:
    SIZE_3x3: ProblemClass
    SIZE_6x6: ProblemClass
    SIZE_12x12: ProblemClass


@define
class _Problems:
    STATIC: _ProblemCategory
    DYNAMIC: _ProblemCategory


PROBLEMS = _Problems(
    STATIC=_ProblemCategory(
        StaticProblem(generate_problem(3, random.Random(42))),
        StaticProblem(generate_problem(6, random.Random(43))),
        StaticProblem(generate_problem(12, random.Random(44))),
    ),
    DYNAMIC=_ProblemCategory(DynamicProblem(3), DynamicProblem(6), DynamicProblem(12)),
)
