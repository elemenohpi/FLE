# factorio-learning-environment

<div align="center">

[![Build status](https://github.com/DrKenReid/factorio-learning-environment/workflows/build/badge.svg?branch=master&event=push)](https://github.com/DrKenReid/factorio-learning-environment/actions?query=workflow%3Abuild)
[![Python Version](https://img.shields.io/pypi/pyversions/factorio-learning-environment.svg)](https://pypi.org/project/factorio-learning-environment/)
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/DrKenReid/factorio-learning-environment/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/DrKenReid/factorio-learning-environment/blob/master/.pre-commit-config.yaml)
[![Semantic Versions](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--versions-e10079.svg)](https://github.com/DrKenReid/factorio-learning-environment/releases)
[![License](https://img.shields.io/github/license/DrKenReid/factorio-learning-environment)](https://github.com/DrKenReid/factorio-learning-environment/blob/master/LICENSE)
![Coverage Report](assets/images/coverage.svg)

`factorio-learning-environment` is a toolkit for evaluating machine learning and optimization algorithms on tasks within the world of Factorio https://www.factorio.com/

</div>

## Quick Start

`factorio-learning-environment` can be used as a python module, or as a standalone [gRPC](https://grpc.io/) server from other languages.

_Whichever method you use, it is necessary to provide your own copy of the Factorio headless server, as it is not distributed within this python package._

By default, `factorio-learning-environment` looks for the factorio server at `~/factorio`. You can customize this by setting the environment variable `FACTORIO_PATH`.

The version of Factorio headless server which this package is developed against is 1.1.50, which is freely downloadable from https://www.factorio.com/get-download/1.1.50/headless/linux64 subject to [its licence agreement](https://www.factorio.com/terms-of-service).

As the headless Factorio server is only available on linux, `factorio-learning-environment` only supports linux.

### Examples

This is a very brief intro to using the package. For more complete examples of using Python and other languages see the [`./examples`](./examples) subdirectory.

### Install (requires `python>=3.8`)

```bash
pip install factorio-learning-environment
```

### Python: direct api

```python
import asyncio
import numpy as np
import fle.environments.logistics_belt_placement_problem as lbpp

async def run():
    # Choose one of the problem classes from STATIC / DYNAMIC
    problem_class = lbpp.PROBLEMS.STATIC.SIZE_3x3
    async with lbpp.Evaluator(problem_class, deterministic=False) as evaluator:
        # Construct the problem inside the Factorio simulation
        await evaluator.create_world()

        # Get an observation of the environment encoded as a matrix
        obs = await evaluator.get_observation()
        # Decide action, we'll just do something random
        dim = problem_class.get_dimension()
        solution = np.random.randint(0, 5, (dim, dim))
        
        # This commented solution happens to be a good solution
        # to lbpp.PROBLEMS.STATIC.SIZE_3x3
        # solution = np.array([[4, 0, 0], [4, 0, 0], [4, 0, 0]])

        # Score our solution
        fitness = await evaluator.evaluate_fitness(solution)
        print(fitness)

asyncio.run(run())
```

### Python: OpenAI Gym api

An entirely standard [OpenAI Gym interface](https://gym.openai.com/).

```python
import gym

from fle.gym import register_fle_with_gym

register_fle_with_gym()
# Corresponds to fle.environments.logistics_belt_placement_problem.PROBLEMS.STATIC.SIZE_3x3
with gym.make(
    "factorio-learning-environment/LogisticsBeltPlacementProblem-Static-3x3-Nondeterministic-v0"
) as env:
    for episode in range(3):
        # Construct the problem inside the Factorio simulation
        observation = env.reset()
        # Normally you would loop around env.step here
        # This specific problem as a "one-shot" environment with only one step

        # Decide action, we'll just do something random
        action = env.action_space.sample()
        # This commented action happens to be a good solution
        # to LogisticsBeltPlacementProblem-Static-3x3-Nondeterministic-v0
        # action = [4, 0, 0, 4, 0, 0, 4, 0, 0]
        observation, reward, done, _ = env.step(action)
        print(reward)

```

### Other languages (gRPC server)

*TODO*

## About

Factorio is a computer game about automation and logistics which emulates a myriad of real-world problems in a sci-fi setting, such as:

- Electrical network management
- Solid goods transport networks
- Fluid resource transport networks
- Production planning
- Cost reduction
- Pollution / production relationship
- Defence
- Research with pre-requisites
- Many-objective optimization
- Bin-packing
- Decision making

`factorio-learning-environment` (FLE) is a toolkit for evaluating machine learning and optimization algorithms on tasks within the world of Factorio https://www.factorio.com/

FLE provides an assortment of Environments -- interactive situations with a method of scoring success -- that challenge agents / algorithms to tackle a problem simulated in Factorio, as well as building blocks for creating and sharing them.

FLE is an expansion of the initial work from the paper [The Factory Must Grow: Automation in Factorio](https://arxiv.org/abs/2102.04871) and is also inspired by the [NetHack Learning Environment](https://github.com/facebookresearch/nle).

FLE differs from the NetHack Learning Environment and other [openai gym](https://gym.openai.com/) environments in a few ways:

- It is less focused on reinforcement learning specifically, and intends to be equally favourable for evaluation of other algorithms such as linear programming or evolutionary algorithms.
- It can provide observation and action API's that are different to the standard open AI gym environment interface which allows:
    - More flexibility around where in the system things like feature detection and dimensionality reduction happen. _Note: This element should be taken in to account when using the environments to compare algorithms._
    - `asyncio`-friendly interfaces to be more favourable towards concurrency.
- FLE also aims to provide more first class support for use from non-python languages via the exposure of a [gRPC](https://grpc.io/) interface.

## Concepts

Environment: an interactive situation with a method of scoring success. Note that environments may modify the rules of stock Factorio to make problems more tractable or more focused. For example, every current environment disables all the hostile enemies that exist in the stock game.

*TODO More concept docs* 

## Inspecting environments with a graphical version of Factorio

1. Download a non-headless version of Factorio which matches the version of the headless server used in FLE.
2. Install `fle` (`pip install factorio-learning-environment`) on the machine you are using.
3. Install the factorio mod bundled in `fle` to the Factorio "data directory" (eg. using `python -m fle install-mod .\Factorio_1.1.50`)

Now your Factorio installation should be compatible with save-files and / or connections to the fle headless environments.
If you are loading a save file, note that the game speed may be significantly different to the default. You can reset and unpause the game with the following console commands:
```
/c game.speed = 1.0
/c game.tick_paused = false
```
You currently _must_ adjust the speed and pause setting if you want to then use a tool for screenshots such as [Mapshot](https://github.com/Palats/mapshot).

If you want to connect to a currently running server being managed by fle, the game port number is available in the 
`Evaluator.server.port` variable, or via the `get-connection-info` CLI call.
```
fle call get-connection-info $evaluator
```

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## 🛡 License

[![License](https://img.shields.io/github/license/DrKenReid/factorio-learning-environment)](https://github.com/DrKenReid/factorio-learning-environment/blob/master/LICENSE)

This project is licensed under the terms of the `MIT` license. See [LICENSE](https://github.com/DrKenReid/factorio-learning-environment/blob/master/LICENSE) for more details.

## 📃 Citation

```bibtex
@misc{factorio-learning-environment,
  author = { Kenneth Reid, Iliya Miralavy, Stephen Kelly, Edmund Fokschaner, Wolfgang Banzhaf },
  title = {`factorio-learning-environment` is a toolkit for evaluating machine learning and optimization algorithms on tasks within the world of Factorio https://www.factorio.com/},
  year = {2021},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/DrKenReid/factorio-learning-environment}}
}
```

## Acknowledgments

Thanks to Wube Software Ltd, the developers of Factorio, for developing a deeply enjoyable game.

This project was generated with [`python-package-template`](https://github.com/TezRomacH/python-package-template).

This project is inspired by other similar projects such as [the NetHack Learning Environment](https://github.com/facebookresearch/nle) and [the StarCraft II Learning Environment](https://github.com/deepmind/pysc2).
