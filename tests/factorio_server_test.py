from typing import Optional

import asyncio
import importlib.resources
import os
import tempfile

import pytest

import fle.factorio_server
import fle.factorio_server.world
from fle.factorio_server import rcon
from fle.factorio_server.world import Returns


async def launch_and_tick_server() -> float:
    """Returns the result of lua math.random() after launching and ticking the server"""
    with importlib.resources.open_binary(
        "fle.environments.shared_maps", "128_sandbox.zip"
    ) as save:
        server_config = fle.factorio_server.FactorioServerConfig(save)
        server = await fle.factorio_server.create_server(server_config)
    try:
        # Confirm time starts at 0
        assert server.world.get_current_tick() == 0

        # Confirm the game is paused (bypass server class because it doesn't refresh time in get_current_tick)
        time_one: str = await server.rcon.send_command(
            "/silent-command rcon.print(game.tick)"
        )
        await asyncio.sleep(0.1)
        time_two: str = await server.rcon.send_command(
            "/silent-command rcon.print(game.tick)"
        )
        assert time_one == time_two
        # Now confirm stepping time works
        ticks_to_run = 600
        await server.world.step(ticks_to_run)
        time_three: str = await server.rcon.send_command(
            "/silent-command rcon.print(game.tick)"
        )
        assert int(time_two) + ticks_to_run == int(time_three)
        assert server.world.get_current_tick() == ticks_to_run
        rand: str = await server.rcon.send_command(
            "/silent-command rcon.print(math.random())"
        )
        return float(rand)
    except Exception:
        server.debug_print_server_log()
        raise
    finally:
        await server.aclose()


async def test_factorio_server():
    """Basic server test"""
    first_rand = await launch_and_tick_server()
    second_rand = await launch_and_tick_server()
    # Random number should be the same, given the same starting point and sequence of events
    assert first_rand == second_rand


async def test_saving_world():
    with importlib.resources.open_binary(
        "fle.environments.shared_maps", "128_sandbox.zip"
    ) as save:
        server_config = fle.factorio_server.FactorioServerConfig(save)
        server = await fle.factorio_server.create_server(server_config)
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".zip")
        try:
            os.close(fd)
            await server.save_world(temp_path)
            stat_result = os.stat(temp_path)
            assert stat_result.st_size > 0
        finally:
            os.unlink(temp_path)
    except Exception:
        server.debug_print_server_log()
        raise
    finally:
        await server.aclose()


async def test_mod_rpc():
    with importlib.resources.open_binary(
        "fle.environments.shared_maps", "128_sandbox.zip"
    ) as save:
        server_config = fle.factorio_server.FactorioServerConfig(save)
        server = await fle.factorio_server.create_server(server_config)
    try:
        # Confirm mod calls work
        echo_result = await server.world.call_mod(str, "test_echo", ["foo"])
        assert echo_result == "foo"

        # Confirm mod test_error works with None result type
        with pytest.raises(fle.factorio_server.world.RpcException):
            await server.world.call_mod(None, "test_error")

        # Confirm mod test_error works with non-None result type
        with pytest.raises(fle.factorio_server.world.RpcException):
            await server.world.call_mod(str, "test_error")

        # Confirm nil response works
        none = await server.world.call_mod(None, "test_nil")
        assert none is None

        # Confirm nil with type(None)
        none = await server.world.call_mod(type(None), "test_nil")
        assert none is None

        # Confirm nil with Optional[str]
        none = await server.world.call_mod(Returns[Optional[str]], "test_nil")
        assert none is None

        # Confirm error for nil with str
        with pytest.raises(fle.factorio_server.world.RpcException):
            await server.world.call_mod(str, "test_nil")
    except Exception:
        server.debug_print_server_log()
        raise
    finally:
        await server.aclose()


async def test_rcon_invalid_auth():
    with importlib.resources.open_binary(
        "fle.environments.shared_maps", "128_sandbox.zip"
    ) as save:
        server_config = fle.factorio_server.FactorioServerConfig(save)
        server = await fle.factorio_server.create_server(server_config)
    try:
        # make a second client and connect with incorrect pw
        async with rcon.RCONClient(
            server.rcon.hostname, server.rcon.port, "wrongpassword"
        ) as client:
            with pytest.raises(rcon.RCONAuthFailure):
                await client.connect()
    except Exception:
        server.debug_print_server_log()
        raise
    finally:
        await server.aclose()
