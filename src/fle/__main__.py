""" The CLI entry point for fle.

In general all other code should assume library usage.
This module can act like an application,
setting up logging, interfacing with a user,
creating event loops, setting exit codes etc.
"""

from typing import Awaitable, TypeVar

import asyncio
import logging
import os
from enum import Enum

import typer

from . import version
from .factorio_server import factorio_mod
from .grpc import client as grpc_client
from .grpc import server as grpc_server

DEFAULT_GRPC_PORT = 64192

app = typer.Typer(
    name="factorio-learning-environment",
    help="factorio-learning-environment is a toolkit for evaluating machine learning "
    "and optimization algorithms on tasks within the world of Factorio",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def app_callback(
    print_version: bool = typer.Option(
        False,
        "--version",
        help="Print the version of the factorio-learning-environment package and exit.",
    )
) -> None:
    if print_version:
        typer.echo(f"factorio-learning-environment version: {version}")
        raise typer.Exit()


@app.command()
def server(
    bind_address: str = typer.Option("127.0.0.1", help="What address to listen on"),
    port: int = typer.Option(
        DEFAULT_GRPC_PORT,
        help="The port the server should listen on.",
        envvar="FLE_PORT",  # Add an env-var override we can use during parallel tox testing
        show_envvar=False,
    ),
) -> None:
    """Run the factorio-learning-environment server"""
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        level=logging.INFO,
    )
    asyncio.run(grpc_server.run(bind_address, port))


call_app = typer.Typer(
    help="Call a remote method in the factorio-learning-environment server",
    no_args_is_help=True,
)
app.add_typer(call_app, name="call")

client = grpc_client.CommandLineClient()


@call_app.callback()
def call_app_callback(
    hostname: str = typer.Option(
        "127.0.0.1", help="What hostname the server is running at"
    ),
    port: int = typer.Option(
        DEFAULT_GRPC_PORT,
        help="What port the server is running on",
        envvar="FLE_PORT",  # Add an env-var override we can use during parallel tox testing
        show_envvar=False,
    ),
) -> None:
    client.host = hostname
    client.port = port


# These enums needed because typer doesnt support Int enums


class ProblemCategory(str, Enum):
    STATIC = "STATIC"
    DYNAMIC = "DYNAMIC"


class ProblemSize(str, Enum):
    SIZE_3X3 = "SIZE_3X3"
    SIZE_6X6 = "SIZE_6X6"
    SIZE_12X12 = "SIZE_12X12"


@call_app.command()
def create_evaluator(
    problem_category: ProblemCategory,
    problem_size: ProblemSize,
    deterministic: bool = typer.Option(
        False,
        help="If set, fully reloads the world between trials, thus runs slower",
    ),
) -> None:
    """Start an evaluator for a problem. Evaluators handle problems, worlds, and fitness calculation."""
    result = _run_request(
        client.create_evaluator(problem_category, problem_size, deterministic)
    )
    print(result)


@call_app.command()
def destroy_evaluator(evaluator_id: str) -> None:
    """Shut down an evaluator"""
    _run_request(client.destroy_evaluator(evaluator_id))
    typer.echo(typer.style("Destroyed evaluator", typer.colors.GREEN))


@call_app.command()
def create_world(
    evaluator_id: str, observation_matrix_data_file: typer.FileTextWrite
) -> None:
    """Create a world and receive an initial observation"""
    observation_matrix_shape, observation_matrix_data = _run_request(
        client.create_world(evaluator_id)
    )
    observation_matrix_data_file.write(observation_matrix_data)
    print(observation_matrix_shape)


@call_app.command()
def save_world(evaluator_id: str, save_file_path: str) -> None:
    """Save the current world being run by the given evaluator"""
    _run_request(client.save_world(evaluator_id, save_file_path))
    typer.echo(typer.style(f"Saved world to {save_file_path}", typer.colors.GREEN))


@call_app.command()
def evaluate_fitness(
    evaluator_id: str,
    solution_matrix_shape: str,
    solution_matrix_data_file: typer.FileText,
) -> None:
    """Evaluate the fitness of a solution."""
    result = _run_request(
        client.evaluate_fitness(
            evaluator_id, solution_matrix_shape, solution_matrix_data_file.read()
        )
    )
    print(result)


@call_app.command()
def get_connection_info(
    evaluator_id: str,
) -> None:
    """Get the connection info for a running factorio evaluator."""
    result = _run_request(client.get_connection_info(evaluator_id))
    print(result)


@app.command()
def install_mod(factorio_data_dir: str) -> None:
    """Install the fle mod in to a given factorio data directory"""
    mod_dir = os.path.join(factorio_data_dir, "mods")
    return asyncio.run(factorio_mod.install_mod(mod_dir))


T = TypeVar("T")


def _run_request(awaitable: Awaitable[T]) -> T:
    """Call a command on the running factorio-learning-environment server"""
    try:
        return asyncio.run(awaitable)
    except ConnectionRefusedError as e:
        typer.echo(typer.style(e.strerror, typer.colors.RED))
        typer.echo(
            typer.style(
                "Ensure the fle server is running on the given address and port. Run: `fle server`",
                typer.colors.YELLOW,
            )
        )
        raise typer.Exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
