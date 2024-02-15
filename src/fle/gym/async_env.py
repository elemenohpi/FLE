""" An async version of gym.Env """

from typing import Any, Awaitable, Dict, List, Optional, Tuple, TypeVar, Union

import asyncio
from abc import ABC, abstractmethod

import gym
import gym.version
from anyio.abc import AsyncResource

ObsTypeT = TypeVar("ObsTypeT")
ActTypeT = TypeVar("ActTypeT")


class AsyncEnv(gym.Env[ObsTypeT, ActTypeT], ABC, AsyncResource):
    """Factorio problems should implement this abstract class in order to be used as an open ai gym.

    The concrete sync methods wrap the abstract async methods to provide the sync api used by gym.

    These API docs are replicated from https://github.com/openai/gym/blob/2af816241e4d7f41a000f6144f22e12c8231a112/gym/core.py#L17

    Implement these methods:
        _step_async
        _reset_async
        _close_async
        _seed_async

    Always set these instance members:
        action_space: The Space object corresponding to valid actions
        observation_space: The Space object corresponding to valid observations

    Optionally set these instance members:
        metadata: See gym source for how this is used
        reward_range: A tuple corresponding to the min and max possible rewards
            Note: a default reward range set to [-inf,+inf] already exists. Set it if you want a narrower range.
    """

    #
    # Async abstract methods
    #

    @abstractmethod
    async def _step_async(
        self, action: ActTypeT
    ) -> Tuple[ObsTypeT, float, bool, Dict[str, Any]]:
        """Run one timestep of the environment's dynamics. When end of
        episode is reached, you are responsible for calling `reset()`
        to reset this environment's state.

        Accepts an action and returns a tuple (observation, reward, done, info).

        Args:
            action (ActTypeT): an action provided by the agent

        Returns:
            observation (ObsTypeT): agent's observation of the current environment
            reward (float) : amount of reward returned after previous action
            done (bool): whether the episode has ended, in which case further step() calls will return undefined results
            info (dict): contains auxiliary diagnostic information (helpful for debugging, and sometimes learning)
        """
        raise NotImplementedError

    @abstractmethod
    async def _reset_async(
        self,
        *,
        seed: Optional[int] = None,
        return_info: bool = False,
        options: Optional[Dict[str, object]] = None,
    ) -> Union[ObsTypeT, Tuple[ObsTypeT, Dict[str, object]]]:
        """Resets the environment to an initial state and returns an initial
        observation.

        This method should also reset the environment's random number
        generator(s) if ``seed`` is an integer or if the environment has not
        yet initialized a random number generator. If the environment already
        has a random number generator and `reset` is called with ``seed=None``,
        the RNG should not be reset.

        Moreover, `reset` should (in the typical use case) be called with an
        integer seed right after initialization and then never again.

        Args:
            seed (int or None):
                The seed that is used to initialize the environment's PRNG. If the environment does not already have a PRNG and ``seed=None`` (the default option) is passed, a seed will be chosen from some source of entropy (e.g. timestamp or /dev/urandom).
                However, if the environment already has a PRNG and ``seed=None`` is passed, the PRNG will *not* be reset. If you pass an integer, the PRNG will be reset even if it already exists. Usually, you want to pass an integer *right after the environment has been initialized and then never again*. Please refer to the minimal example above to see this paradigm in action.
            return_info (bool): If true, return additional information along with initial observation. This info should be analogous to the info returned in :meth:`step`
            options (dict or None): Additional information to specify how the environment is reset (optional, depending on the specific environment)

        Returns:
            observation (object): Observation of the initial state. This will be an element of :attr:`observation_space` (usually a numpy array) and is analogous to the observation returned by :meth:`step`.
            info (optional dictionary): This will *only* be returned if ``return_info=True`` is passed. It contains auxiliary information complementing ``observation``. This dictionary should be analogous to the ``info`` returned by :meth:`step`.
        """
        raise NotImplementedError

    @abstractmethod
    async def _close_async(self) -> None:
        """Override close in your subclass to perform any necessary cleanup.

        Environments will automatically close() themselves when
        garbage collected or when the program exits.
        """
        raise NotImplementedError

    @abstractmethod
    async def _seed_async(self, seed: Optional[int] = None) -> List[int]:
        """Sets the seed for this env's random number generator(s).

        Note:
            Some environments use multiple pseudorandom number generators.
            We want to capture all such seeds used in order to ensure that
            there aren't accidental correlations between multiple generators.

        Args:
            seed: if given will re-seed the environment to this seed

        Returns:
            list<bigint>: Returns the list of seeds used in this env's random
              number generators. The first value in the list should be the
              "main" seed, or the value which a reproducer should pass to
              'seed'. Often, the main seed equals the provided 'seed', but
              this won't be true if seed=None, for example.
        """
        raise NotImplementedError

    #
    # Async interface
    #

    async def step_async(
        self, action: ActTypeT
    ) -> Tuple[ObsTypeT, float, bool, Dict[str, Any]]:
        return await self._step_async(action)

    async def reset_async(
        self,
        *,
        seed: Optional[int] = None,
        return_info: bool = False,
        options: Optional[Dict[str, object]] = None,
    ) -> Union[ObsTypeT, Tuple[ObsTypeT, Dict[str, object]]]:
        super().reset(seed=seed, return_info=return_info, options=options)
        return await self._reset_async(
            seed=seed, return_info=return_info, options=options
        )

    async def aclose(self) -> None:
        """Async close"""
        return await self._close_async()

    async def seed_async(self, seed: Optional[int] = None) -> List[int]:
        super().seed(seed)
        return await self._seed_async(seed)

    #
    # Sync interface
    #

    def step(self, action: ActTypeT) -> Tuple[ObsTypeT, float, bool, Dict[str, Any]]:
        return _run_in_eventloop(self.step_async(action))

    # The optional arg prepares us for the next release of gym
    # pylint: disable-next=arguments-differ
    def reset(
        self,
        *,
        seed: Optional[int] = None,
        return_info: bool = False,
        options: Optional[Dict[str, object]] = None,
    ) -> Union[ObsTypeT, Tuple[ObsTypeT, Dict[str, object]]]:
        return _run_in_eventloop(
            self.reset_async(seed=seed, return_info=return_info, options=options)
        )

    def render(self, mode: str = "human") -> None:
        raise NotImplementedError(
            "Factorio learning environments currently don't support rendering."
        )

    def close(self) -> None:
        return _run_in_eventloop(self.aclose())

    def seed(self, seed: Optional[int] = None) -> List[int]:
        return _run_in_eventloop(self.seed_async(seed))


T = TypeVar("T")


def _run_in_eventloop(co: Awaitable[T]) -> T:
    """asyncio has deprecated implicit event loop creation in get_event_loop

    This function restores it by running the given coroutine
    in an existing or new event loop implicitly"""
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    if loop is None:
        loop = asyncio.get_event_loop_policy().get_event_loop()
    return loop.run_until_complete(co)
