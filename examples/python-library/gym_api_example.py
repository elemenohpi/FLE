import logging
import sys

import gym

from fle.gym import register_fle_with_gym

LOG = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=logging.INFO,
    )
    register_fle_with_gym()
    # Corresponds to fle.environments.logistics_belt_placement_problem.PROBLEMS.STATIC.SIZE_3x3
    with gym.make(
        "factorio-learning-environment/LogisticsBeltPlacementProblem-Static-3x3-Nondeterministic-v0"
    ) as env:
        for episode in range(3):
            LOG.info("Episode: %s", episode)
            # Construct the problem inside the Factorio simulation
            observation = env.reset()
            # Normally you would loop around env.step here
            # This specific problem as a "one-shot" environment with only one step
            LOG.info("Observation:\n%s", observation)
            # You see a 1D version of this:
            # [[ 5  5 13  5  5  5  5]
            #  [ 5  5 10  5  5  5  5]
            #  [ 5  5  0  0  5  5  5]
            #  [ 5  5  0  0  0  5  5]
            #  [13  9  0  5  0  5  5]
            #  [ 5  5  5  5  5  5  5]
            #  [ 5  5  5  5  5  5  5]]

            # Decide action, we'll just do something random
            # Action space for LogisticsBeltPlacementProblem-Static-3x3-Nondeterministic-v0
            # is MultiDiscrete([5] * 9) where:
            # 0 => Nothing
            # 1,2,3,4 => a Logistics Belt (north, east, south, west respectively)
            # Theres a 2.5% chance this solution is good
            action = env.action_space.sample()
            # This commented action happens to be a good solution
            # to LogisticsBeltPlacementProblem-Static-3x3-Nondeterministic-v0
            # action = [4, 0, 0, 4, 0, 0, 4, 0, 0]
            LOG.info("Action:\n%s", action)
            observation, reward, done, _ = env.step(action)
            LOG.info("Reward: %s", reward)
            assert done
            # Reward is based on the amount of the input chest drained and the amount of
            # the output chest filled.
            # 6 is the score you get just for having 1 logistics belt next to the input
            # if we do any better than that, we've made progress.
            # This is where a real algorithm would learn from the attempt
            if reward > 6:
                LOG.info("We achieved something!! Quit while we're ahead.")
                break


if __name__ == "__main__":
    sys.exit(main())
