from typing import AsyncIterator, Tuple

from contextlib import asynccontextmanager

from attr import define
from grpclib.client import Channel

from .proto.fle import (
    CreateEvaluatorRequest,
    CreateEvaluatorRequestProblemCategory,
    CreateEvaluatorRequestProblemSize,
    CreateWorldRequest,
    EvaluateFitnessRequest,
    EvaluatorHandle,
    LogisticsBeltPlacementProblemStub,
    NdArray,
    SaveWorldRequest,
)


@define
class CommandLineClient:
    """A client with an interface designed for the command line interface.
    All params are flattened to scalars"""

    host: str = ""
    port: int = 0

    async def create_evaluator(
        self, problem_category: str, problem_size: str, deterministic: bool
    ) -> str:
        converted_problem_category = CreateEvaluatorRequestProblemCategory.from_string(
            problem_category
        )
        converted_problem_size = CreateEvaluatorRequestProblemSize.from_string(
            problem_size
        )
        # Because from_string can't return Self type prior to python 3.11
        assert isinstance(
            converted_problem_category, CreateEvaluatorRequestProblemCategory
        )
        assert isinstance(converted_problem_size, CreateEvaluatorRequestProblemSize)
        create_evaluator_request = CreateEvaluatorRequest(
            converted_problem_category, converted_problem_size, deterministic
        )
        async with self._lbpp_stub() as lbpp:
            response = await lbpp.create_evaluator(create_evaluator_request)
            return response.uuid

    async def destroy_evaluator(self, evaluator_id: str) -> None:
        evaluator_handle = EvaluatorHandle(evaluator_id)
        async with self._lbpp_stub() as lbpp:
            await lbpp.destroy_evaluator(evaluator_handle)

    async def create_world(self, evaluator_id: str) -> Tuple[str, str]:
        create_world_request = CreateWorldRequest(EvaluatorHandle(evaluator_id))
        async with self._lbpp_stub() as lbpp:
            response = await lbpp.create_world(create_world_request)
            return ",".join([str(s) for s in response.shape]), " ".join(
                [str(val) for val in response.data]
            )

    async def save_world(self, evaluator_id: str, save_file_path: str) -> None:
        save_world_request = SaveWorldRequest(
            EvaluatorHandle(evaluator_id), save_file_path
        )
        async with self._lbpp_stub() as lbpp:
            await lbpp.save_world(save_world_request)

    async def evaluate_fitness(
        self,
        evaluator_id: str,
        solution_matrix_shape: str,
        solution_matrix_data: str,
    ) -> int:
        solution_matrix_shape_parsed = [
            int(s) for s in solution_matrix_shape.split(",")
        ]
        solution_matrix_data_parsed = [int(s) for s in solution_matrix_data.split()]
        evaluate_fitness_request = EvaluateFitnessRequest(
            EvaluatorHandle(evaluator_id),
            NdArray(solution_matrix_shape_parsed, solution_matrix_data_parsed),
        )
        async with self._lbpp_stub() as lbpp:
            response = await lbpp.evaluate_fitness(evaluate_fitness_request)
            return response.fitness

    async def get_connection_info(
        self,
        evaluator_id: str,
    ) -> str:
        async with self._lbpp_stub() as lbpp:
            response = await lbpp.get_connection_info(EvaluatorHandle(evaluator_id))
            return response.to_json()

    @asynccontextmanager
    async def _lbpp_stub(
        self,
    ) -> AsyncIterator[LogisticsBeltPlacementProblemStub]:
        async with Channel(self.host, self.port) as channel:
            yield LogisticsBeltPlacementProblemStub(channel)
