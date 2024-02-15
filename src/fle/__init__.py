"""`factorio-learning-environment` is a toolkit for evaluating machine learning
and optimization algorithms on tasks within the world of Factorio https://www.factorio.com/"""

import logging
from importlib import metadata as importlib_metadata

# Hide our log output unless the application actually registers a handler, as per
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__package__).addHandler(logging.NullHandler())


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


version: str = get_version()
