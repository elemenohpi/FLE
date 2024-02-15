from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, NoReturn

import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

import anyio.abc
import grpclib
import numpy as np
import numpy.typing as npt
from grpclib.reflection.service import ServerReflection
from grpclib.server import Server

from ..environments import logistics_belt_placement_problem as lbpp
from .proto.fle import (
    CreateEvaluatorRequest,
    CreateEvaluatorRequestProblemCategory,
    CreateEvaluatorRequestProblemSize,
    CreateWorldRequest,
    Empty,
    EvaluateFitnessRequest,
    EvaluateFitnessResponse,
    EvaluatorHandle,
    LogisticsBeltPlacementProblemBase,
    NdArray,
    SaveWorldRequest,
    ServerConnectionInfo,
)

if TYPE_CHECKING:
    from grpclib.server import IServable

LOG = logging.getLogger(__name__)


def _invalid_argument(msg: str) -> NoReturn:
    raise grpclib.exceptions.GRPCError(grpclib.Status.INVALID_ARGUMENT, msg)


def _uuid() -> str:
    return str(uuid.uuid4())


def _np_to_proto(arr: npt.NDArray[Any]) -> NdArray:
    return NdArray(list(arr.shape), arr.flatten().tolist())


def _proto_to_np(arr: NdArray) -> npt.NDArray[Any]:
    expected_entries = np.prod(arr.shape)
    num_entries = len(arr.data)
    if num_entries != expected_entries:
        _invalid_argument(
            f"Expected {expected_entries} entries in array with shape ({arr.shape}) but got {num_entries}"
        )
    return np.array(arr.data).reshape(arr.shape)


class LBPPService(LogisticsBeltPlacementProblemBase, anyio.abc.AsyncResource):
    def __init__(self):
        # TODO cap the number of evaluators we allow
        self.evaluators: Dict[str, lbpp.Evaluator] = {}

    async def aclose(self):
        await asyncio.gather(*[ev.aclose() for ev in self.evaluators.values()])

    async def create_evaluator(
        self, create_evaluator_request: CreateEvaluatorRequest
    ) -> EvaluatorHandle:
        problem_category_map = {
            CreateEvaluatorRequestProblemCategory.STATIC: lbpp.PROBLEMS.STATIC,
            CreateEvaluatorRequestProblemCategory.DYNAMIC: lbpp.PROBLEMS.DYNAMIC,
        }
        if not create_evaluator_request.problem_category in problem_category_map:
            _invalid_argument(
                f"Invalid problem_category {create_evaluator_request.problem_category}"
            )
        category = problem_category_map[create_evaluator_request.problem_category]
        problem_size_map = {
            CreateEvaluatorRequestProblemSize.SIZE_3X3: category.SIZE_3x3,
            CreateEvaluatorRequestProblemSize.SIZE_6X6: category.SIZE_6x6,
            CreateEvaluatorRequestProblemSize.SIZE_12X12: category.SIZE_12x12,
        }
        if not create_evaluator_request.problem_size in problem_size_map:
            _invalid_argument(
                f"Invalid problem_size {create_evaluator_request.problem_size}"
            )
        problem_class = problem_size_map[create_evaluator_request.problem_size]
        evaluator_id = _uuid()
        evaluator = lbpp.Evaluator(
            problem_class, create_evaluator_request.deterministic
        )
        self.evaluators[evaluator_id] = evaluator
        return EvaluatorHandle(evaluator_id)

    async def destroy_evaluator(self, evaluator_handle: EvaluatorHandle) -> Empty:
        evaluator_inst = self._lookup_evaluator(evaluator_handle)
        del self.evaluators[evaluator_handle.uuid]
        await evaluator_inst.aclose()
        return Empty()

    async def create_world(self, create_world_request: CreateWorldRequest) -> NdArray:
        evaluator_instance = self._lookup_evaluator(create_world_request.evaluator)
        await evaluator_instance.create_world()
        obs = await evaluator_instance.get_observation()
        return _np_to_proto(obs)

    async def save_world(self, save_world_request: SaveWorldRequest) -> Empty:
        evaluator_instance = self._lookup_evaluator(save_world_request.evaluator)
        await evaluator_instance.save_world(save_world_request.save_file_path)
        return Empty()

    async def evaluate_fitness(
        self, evaluate_fitness_request: EvaluateFitnessRequest
    ) -> EvaluateFitnessResponse:
        evaluator_instance = self._lookup_evaluator(evaluate_fitness_request.evaluator)
        solution_mat = _proto_to_np(evaluate_fitness_request.solution)
        fitness = await evaluator_instance.evaluate_fitness(solution_mat)
        return EvaluateFitnessResponse(fitness)

    async def get_connection_info(
        self, evaluator_handle: EvaluatorHandle
    ) -> ServerConnectionInfo:
        evaluator_instance = self._lookup_evaluator(evaluator_handle)
        if evaluator_instance.server is None:
            raise grpclib.exceptions.GRPCError(
                grpclib.Status.FAILED_PRECONDITION,
                "No running server is associated with this evaluator. A world must be created before connection info can be available.",
            )
        return ServerConnectionInfo(
            game_port=evaluator_instance.server.port,
            game_password="",  # There are no game passwords in the current setup
            rcon_port=evaluator_instance.server.rcon.port,
            rcon_password=evaluator_instance.server.rcon.password,
        )

    def _lookup_evaluator(self, evaluator_handle: EvaluatorHandle) -> lbpp.Evaluator:
        """Finds the evaluator or raises _invalid_argument"""
        if not evaluator_handle.uuid:
            _invalid_argument("Expected evaluator_handle.uuid")
        evaluator = self.evaluators.get(evaluator_handle.uuid, None)
        if evaluator is None:
            _invalid_argument(f"No evaluator with id {evaluator_handle.uuid}")
        return evaluator


@asynccontextmanager
async def create_server(bind_address: str, port: int) -> AsyncIterator[Server]:
    """Yields the grpclib.server.Server once it is running"""
    async with LBPPService() as lbpp_service:
        services: List["IServable"] = [lbpp_service]
        services = ServerReflection.extend(services)
        # TODO Remove mypy ignore if https://github.com/vmagamedov/grpclib/issues/158 is ever solved
        server = Server(services)  # type: ignore[abstract]
        await server.start(bind_address, port)
        LOG.info(
            "factorio-learning-environment server is now running on %s:%s",
            bind_address,
            port,
        )
        yield server
        await server.wait_closed()


async def run(bind_address: str, port: int) -> None:
    async with create_server(bind_address, port) as _:
        pass
