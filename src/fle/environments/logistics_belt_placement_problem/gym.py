""" Implements the open ai gym Env for this problem """

from typing import Any, Dict, List, Optional, Tuple, Union

from functools import partial

import gym.spaces
import numpy as np
import numpy.typing as npt
from gym.envs import register as _register

from ...gym.async_env import AsyncEnv
from . import encoding
from .evaluator import Evaluator
from .problems import PROBLEMS, ProblemClass, _ProblemCategory


class GymEnv(
    AsyncEnv[
        npt.NDArray[np.uint8],
        npt.NDArray[np.uint8],
    ]
):
    """Adapts the logistics belt placement problem to a gym interface"""

    def __init__(self, problem_class: ProblemClass, deterministic: bool) -> None:
        super().__init__()
        self.problem_class = problem_class
        self.evaluator = Evaluator(self.problem_class, deterministic)
        dim = self.problem_class.get_dimension()
        max_action = encoding.get_max_encoded_action_value_exclusive()
        # pylint: disable-next=attribute-defined-outside-init
        self.action_space = gym.spaces.MultiDiscrete([max_action] * (dim * dim))
        max_observation = encoding.get_max_encoded_observation_value_exclusive()
        num_observation_tiles = (dim + 4) * (dim + 4)
        # pylint: disable-next=attribute-defined-outside-init
        self.observation_space = gym.spaces.MultiDiscrete(
            [max_observation] * num_observation_tiles
        )

    async def _get_1d_observation(self) -> npt.NDArray[np.uint8]:
        dim = self.problem_class.get_dimension() + 4
        obs_matrix = await self.evaluator.get_observation()
        obs_array = obs_matrix.reshape(dim * dim)
        return obs_array

    async def _step_async(
        self, action: npt.ArrayLike
    ) -> Tuple[npt.NDArray[np.uint8], float, bool, Dict[str, Any]]:
        dim = self.problem_class.get_dimension()
        action_matrix = np.asarray(action).reshape((dim, dim))
        fitness = await self.evaluator.evaluate_fitness(action_matrix)
        obs = await self._get_1d_observation()
        return (obs, fitness, True, {})

    async def _reset_async(
        self,
        *,
        seed: Optional[int] = None,
        return_info: bool = False,
        options: Optional[Dict[str, object]] = None,  # pylint: disable=unused-argument
    ) -> Union[npt.NDArray[np.uint8], Tuple[npt.NDArray[np.uint8], Dict[str, object]]]:
        if seed is not None:
            self.problem_class.seed(seed)
        await self.evaluator.create_world()
        obs = await self._get_1d_observation()
        if return_info:
            return (obs, {})
        return obs

    async def _close_async(self) -> None:
        await self.evaluator.aclose()

    async def _seed_async(self, seed: Optional[int] = None) -> List[int]:
        self.problem_class.seed(seed)
        return [self.problem_class.get_seed()]


def _get_problem_class(cat: _ProblemCategory, size_name: str) -> ProblemClass:
    if size_name == "3x3":
        return cat.SIZE_3x3
    if size_name == "6x6":
        return cat.SIZE_6x6
    if size_name == "12x12":
        return cat.SIZE_12x12
    raise Exception(f"Bad size {size_name}")


def register():
    categories = {"Static": PROBLEMS.STATIC, "Dynamic": PROBLEMS.DYNAMIC}
    size_names = ["3x3", "6x6", "12x12"]
    determinism_option = {
        "Deterministic": True,
        "Nondeterministic": False,
    }
    for category_name, category in categories.items():
        for size_name in size_names:
            for (
                determinism_option_name,
                determinism_option_value,
            ) in determinism_option.items():
                problem_class = _get_problem_class(category, size_name)
                _register(
                    id=f"factorio-learning-environment/LogisticsBeltPlacementProblem-{category_name}-{size_name}-{determinism_option_name}-v0",
                    entry_point=partial(
                        GymEnv, problem_class, determinism_option_value
                    ),
                    kwargs={},
                    reward_threshold=2352,
                )
