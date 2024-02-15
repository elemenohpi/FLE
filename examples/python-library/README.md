# python-library examples

In the pursuit of flexibility, Factorio Learning Environments may have 1 or 2 different interfaces:
- A direct interface, un-constrained by the OpenAI Gym interface format.
- A standardized OpenAI Gym interface.

The Logistics Belt Placement Problem is an example of an environment with both interfaces.

- See [`./direct_api_example.py`](./direct_api_example.py) for how to use the direct interface.
- See [`./gym_api_example.py`](./gym_api_example.py) for how to use the OpenAI Gym interface.

Before running either example, first install the `factorio-learning-environment` package using:
```bash
pip install factorio-learning-environment
```
Ensure `factorio-learning-environment` can find your factorio server by setting the environment variable `FACTORIO_PATH` or ensuring Factorio is available at the default location of `~/factorio`.

Finally:
```
python direct_api_example.py
```
or
```
python gym_api_example.py
```
