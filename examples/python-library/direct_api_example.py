import asyncio
import logging
import sys

import numpy as np

import fle.environments.logistics_belt_placement_problem as lbpp

LOG = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=logging.INFO,
    )
    # Choose one of the problem classes
    problem_class = lbpp.PROBLEMS.STATIC.SIZE_3x3
    async with lbpp.Evaluator(problem_class, deterministic=False) as evaluator:
        for attempt in range(3):
            LOG.info("Attempt: %s", attempt)

            # Construct the problem inside the Factorio simulation
            await evaluator.create_world()

            # Get an observation of the environment encoded as a matrix
            obs = await evaluator.get_observation()
            LOG.info("Observation:\n%s", obs)
            # You see something like this:
            # [[ 5  5 13  5  5  5  5]
            #  [ 5  5 10  5  5  5  5]
            #  [ 5  5  0  0  5  5  5]
            #  [ 5  5  0  0  0  5  5]
            #  [13  9  0  5  0  5  5]
            #  [ 5  5  5  5  5  5  5]
            #  [ 5  5  5  5  5  5  5]]

            # Decide action, we'll just do something random
            # Valid input for lbpp.PROBLEMS.STATIC.SIZE_3x3 is a
            # 3x3 matrix of integers between 0 and 5
            # 0 => Nothing
            # 1,2,3,4 => a Logistics Belt (north, east, south, west respectively)
            # Theres a 2.5% chance this solution is good
            dim = problem_class.get_dimension()
            solution = np.random.randint(0, 5, (dim, dim))
            LOG.info("Solution:\n%s", solution)

            # This commented solution happens to be a good solution
            # to lbpp.PROBLEMS.STATIC.SIZE_3x3
            # solution = np.array([[4, 0, 0], [4, 0, 0], [4, 0, 0]])

            # Score our solution
            fitness = await evaluator.evaluate_fitness(solution)
            LOG.info("Fitness: %s", fitness)
            # Fitness is based on the amount of the input chest drained and the amount of
            # the output chest filled.
            # 6 is the score you get just for having 1 logistics belt next to the input
            # if we do any better than that, we've made progress.
            # This is where a real algorithm would learn from the attempt
            if fitness > 6:
                LOG.info("We achieved something!! Quit while we're ahead.")
                break


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
