from typing import Optional

import importlib.resources
import logging
import math
from pathlib import Path

import anyio.abc
import numpy as np
import numpy.typing as npt
from attr import define

from ... import factorio_server
from ...factorio_server import world
from .. import shared_maps
from .encoding import decode_action, encode_observation
from .problems import Problem, ProblemClass

LOG = logging.getLogger(__name__)


def integer_position_equal(a: world.Position, b: world.Position) -> bool:
    """Returns true if the positions are equal (using floor before comparison)"""
    return math.floor(a.x) == math.floor(b.x) and math.floor(a.y) == math.floor(b.y)


@define
class Evaluator(anyio.abc.AsyncResource):
    problem_class: ProblemClass
    # The RNG seed is a persisted part of the simulation state which cannot be re-seeded
    # after the initial map creation (from a seed) occurs. Thie means that we have a choice
    # between full determinism (reloading the world on each triel) vs less determinism
    # (re-using the existing world for each trial). On short experiments, the server spin-up
    # cost is non-trivial and so the non-deterministic option may be preferable for the perf.
    deterministic: bool
    server: Optional[factorio_server.FactorioServer] = None
    current_problem: Optional[Problem] = None
    current_input_chest: Optional[world.EntityDescription] = None
    current_output_chest: Optional[world.EntityDescription] = None

    async def create_world(self) -> None:
        if self.deterministic:
            await self.aclose()
        if self.server is None:
            with importlib.resources.open_binary(
                shared_maps, "128_sandbox.zip"
            ) as save:
                server_config = factorio_server.FactorioServerConfig(save)
                self.server = await factorio_server.create_server(server_config)
        await self.server.world.destroy_all_entities()
        self.current_problem = self.problem_class.get_instance()
        input_chest_pos = self.current_problem.get_input_chest_pos()
        output_chest_pos = self.current_problem.get_output_chest_pos()
        entities = []
        for x in range(-2, self.current_problem.dimension + 2):
            for y in range(-2, self.current_problem.dimension + 2):
                pos = world.Position(x, y)
                if pos == self.current_problem.input_location.position:
                    entities.append(
                        world.CreateEntityParams(
                            "fle-void-fast-inserter",
                            self.current_problem.input_location.position,
                            self.current_problem.input_location.direction,
                        )
                    )
                elif pos == self.current_problem.output_location.position:
                    entities.append(
                        world.CreateEntityParams(
                            "fle-void-fast-inserter",
                            self.current_problem.output_location.position,
                            self.current_problem.output_location.direction,
                        )
                    )
                elif pos == input_chest_pos:
                    entities.append(
                        world.CreateEntityParams("steel-chest", input_chest_pos)
                    )
                elif pos == output_chest_pos:
                    entities.append(
                        world.CreateEntityParams("steel-chest", output_chest_pos)
                    )
                elif (
                    pos.x < 0
                    or pos.y < 0
                    or pos.x >= self.current_problem.dimension
                    or pos.y >= self.current_problem.dimension
                ):
                    entities.append(world.CreateEntityParams("stone-wall", pos))
        for wall_pos in self.current_problem.wall_obstacles:
            entities.append(world.CreateEntityParams("stone-wall", wall_pos))
        created_result = await self.server.world.create_entities(entities)
        if not all(created_result):
            LOG.error("created_result: %s", created_result)
            LOG.error("Preserving the world with tmpdir %s", self.server.tmpdir)
            self.server.delete_tmpdir = False
            await self.server.save_world(str(Path(self.server.tmpdir, "debug.zip")))
        assert all(
            created_result
        ), "None of the entities in the problem definition should fail to create"
        for e in created_result:
            # we just asserted this but mypy is not smart enough to realize
            assert e is not None
            if e.name == "steel-chest":
                if integer_position_equal(e.position, input_chest_pos):
                    self.current_input_chest = e
                elif integer_position_equal(e.position, output_chest_pos):
                    self.current_output_chest = e
                else:
                    assert False, "There should not be any other chests"
        assert self.current_input_chest is not None
        quantity_inserted = await self.server.world.insert_items(
            self.current_input_chest,
            world.SimpleItemStack("iron-ore", self.current_problem.input_ore_quantity),
        )
        assert quantity_inserted == self.current_problem.input_ore_quantity

    async def get_observation(self) -> npt.NDArray[np.uint8]:
        assert self.current_problem is not None
        assert self.server is not None
        max_coord = self.current_problem.dimension + 2
        entities = await self.server.world.find_entities(
            (
                world.Position(-2, -2),
                world.Position(max_coord, max_coord),
            )
        )
        return encode_observation(self.current_problem.dimension, entities)

    async def _get_iron_ore_quantity(
        self, entity_description: world.EntityDescription
    ) -> int:
        assert self.server is not None
        output_contents = await self.server.world.get_inventory_contents(
            entity_description
        )
        return output_contents.get("iron-ore", 0)

    async def evaluate_fitness(self, solution_matrix: npt.ArrayLike) -> int:
        assert self.current_problem is not None
        assert self.server is not None
        assert self.current_input_chest is not None
        assert self.current_output_chest is not None
        entities_to_create = decode_action(
            self.current_problem.dimension, solution_matrix
        )
        await self.server.world.create_entities(entities_to_create)
        await self.server.world.step(self.current_problem.ticks_for_evaluation)
        # Could be expanded to account for construction costs
        score = (
            self.current_problem.input_ore_quantity
            - await self._get_iron_ore_quantity(self.current_input_chest)
            + (
                await self._get_iron_ore_quantity(self.current_output_chest)
                * self.current_problem.input_ore_quantity
            )
        )
        return score

    async def save_world(self, save_file_path: str) -> None:
        assert self.server is not None
        await self.server.save_world(save_file_path)

    async def aclose(self):
        if self.server is not None:
            await self.server.aclose()
            self.server = None
