from typing import Optional

import random

import gym
import numpy as np
import pytest

import fle.environments.logistics_belt_placement_problem as lbpp
from fle.gym import register_fle_with_gym

EXPECTED_STATIC_3X3_OBS = [
    [5, 5, 13, 5, 5, 5, 5],
    [5, 5, 10, 5, 5, 5, 5],
    [5, 5, 0, 0, 5, 5, 5],
    [5, 5, 0, 0, 0, 5, 5],
    [13, 9, 0, 5, 0, 5, 5],
    [5, 5, 5, 5, 5, 5, 5],
    [5, 5, 5, 5, 5, 5, 5],
]


async def test_determinism_of_problems():
    a = lbpp.generate_problem(12, random.Random(42))
    b = lbpp.generate_problem(12, random.Random(42))
    assert a == b


@pytest.mark.parametrize("deterministic", [True, False])
async def test_static_problem_correct_solution(deterministic: bool) -> None:
    problem_class = lbpp.PROBLEMS.STATIC.SIZE_3x3
    async with lbpp.Evaluator(problem_class, deterministic) as evaluator:
        last_server_pid: Optional[int] = None
        for _ in range(2):
            await evaluator.create_world()
            assert evaluator.server is not None
            if deterministic:
                # confirm that server pid is changed
                assert evaluator.server.process.pid != last_server_pid
            else:
                if last_server_pid is None:
                    last_server_pid = evaluator.server.process.pid
                # confirm that server pid is unchanged
                assert evaluator.server.process.pid == last_server_pid
            last_server_pid = evaluator.server.process.pid
            obs = await evaluator.get_observation()
            # The correct observation for this static problem:
            expected_obs = EXPECTED_STATIC_3X3_OBS
            assert (obs == expected_obs).all()
            solution = [[4, 0, 0], [4, 0, 0], [4, 0, 0]]
            fitness = await evaluator.evaluate_fitness(solution)
            assert fitness == 2352


@pytest.mark.parametrize("deterministic", [True, False])
async def test_dynamic_problem(deterministic: bool) -> None:
    problem_class = lbpp.PROBLEMS.DYNAMIC.SIZE_12x12
    async with lbpp.Evaluator(problem_class, deterministic) as evaluator:
        # Run 2 cycles to confirm the evaluator handles re-use
        observations = []
        for _ in range(2):
            await evaluator.create_world()
            obs = await evaluator.get_observation()
            observations.append(obs)
            solution = np.ones((12, 12), dtype=np.uint8)
            fitness = await evaluator.evaluate_fitness(solution)
            assert fitness >= 0
        # Confirm the problems were different
        assert (observations[0] != observations[1]).any()


@pytest.fixture(scope="module", autouse=True)
def gym_registration():
    register_fle_with_gym()


def test_gym_api():
    with gym.make(
        "factorio-learning-environment/LogisticsBeltPlacementProblem-Static-3x3-Nondeterministic-v0"
    ) as env:

        # First episode: Random action
        observation = env.reset()
        assert isinstance(observation, np.ndarray)
        action = env.action_space.sample()
        assert isinstance(action, np.ndarray)
        observation, reward, done, info = env.step(action)
        assert isinstance(observation, np.ndarray)
        assert reward >= 3
        assert done
        assert isinstance(info, dict)

        # Second episode: Winning action
        observation = env.reset()
        assert isinstance(observation, np.ndarray)
        action = [4, 0, 0, 4, 0, 0, 4, 0, 0]
        observation, reward, done, info = env.step(action)
        assert isinstance(observation, np.ndarray)
        assert reward == 2352
        assert done
        assert isinstance(info, dict)


def test_another_gym_env():
    """Test that other environment options work"""
    with gym.make(
        "factorio-learning-environment/LogisticsBeltPlacementProblem-Dynamic-6x6-Deterministic-v0"
    ) as env:
        # First episode: Random action
        observation = env.reset()
        assert isinstance(observation, np.ndarray)
        action = env.action_space.sample()
        assert isinstance(action, np.ndarray)
        observation, reward, done, info = env.step(action)
        assert isinstance(observation, np.ndarray)
        assert reward >= 3
        assert done
        assert isinstance(info, dict)
