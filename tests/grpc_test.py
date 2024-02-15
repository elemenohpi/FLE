import asyncio.base_events
import logging
from contextlib import closing

import pytest

from fle.grpc.client import CommandLineClient
from fle.grpc.server import create_server

from .environments.logistics_belt_placement_problem_test import EXPECTED_STATIC_3X3_OBS


def get_listening_port(server: asyncio.base_events.Server) -> int:
    """Gets the port of an already running server"""
    sockets = server.sockets
    assert sockets is not None
    socket = sockets[0]
    sockname = socket.getsockname()
    port = sockname[1]
    assert isinstance(port, int)
    return port


async def test_grpc(caplog: pytest.LogCaptureFixture) -> None:
    """Tests the grpc API using the CLI-adapted Client"""
    # Reduce log level for hpack, its very noisy
    caplog.set_level(logging.INFO, logger="hpack")

    address = "127.0.0.1"
    async with create_server(address, 0) as server:
        with closing(server):
            # pylint: disable-next=protected-access
            tcp_server = server._server
            assert isinstance(tcp_server, asyncio.base_events.Server)
            port = get_listening_port(tcp_server)
            client = CommandLineClient(address, port)
            evaluator = await client.create_evaluator(
                "STATIC", "SIZE_3X3", deterministic=False
            )
            try:
                (
                    observation_matrix_shape,
                    observation_matrix_data,
                ) = await client.create_world(evaluator)
                expected_obs = EXPECTED_STATIC_3X3_OBS
                expected_obs_shape = f"{len(expected_obs)},{len(expected_obs[0])}"
                assert observation_matrix_shape == expected_obs_shape
                observation_matrix_data_parsed = [
                    int(s) for s in observation_matrix_data.split()
                ]
                expected_obs_flattened = [item for row in expected_obs for item in row]
                assert observation_matrix_data_parsed == expected_obs_flattened
                fitness = await client.evaluate_fitness(
                    evaluator, "3,3", "4 0 0 4 0 0 4 0 0"
                )
                assert fitness == 2352

            finally:
                await client.destroy_evaluator(evaluator)
