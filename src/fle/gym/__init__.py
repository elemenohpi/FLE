from ..environments.logistics_belt_placement_problem import gym as lbpp_gym

_HAS_REGISTERED = False


def register_fle_with_gym():
    global _HAS_REGISTERED
    if _HAS_REGISTERED:
        return
    _HAS_REGISTERED = True
    lbpp_gym.register()
