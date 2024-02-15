"""
Management of Factorio Server instances
Deals with the non-simulation stuff like process management, temp folders, mod-injection, network ports etc.
"""
from typing import BinaryIO, Optional

import importlib
import importlib.resources
import logging
import os
import os.path
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import anyio
import anyio.abc
from attr import define

from . import factorio_mod, ports, rcon
from .world import World

LOG = logging.getLogger(__name__)

SERVER_SETTINGS_JSON = importlib.resources.read_text(
    __package__, "server-settings.json"
)


def get_factorio_path() -> Path:
    if "FACTORIO_PATH" in os.environ:
        return Path(os.environ["FACTORIO_PATH"])
    return Path.home().joinpath("factorio")


@define
class FactorioServerConfig:
    save_file_to_load: BinaryIO
    factorio_install_folder: Optional[str] = None


def get_server_log_path(tmpdir: str) -> str:
    return os.path.join(tmpdir, "factorio-current.log")


def debug_print_server_log(tmpdir: str) -> None:
    """Prints the server's logs to our logs
    Use just for debugging
    """
    with open(get_server_log_path(tmpdir), encoding="utf-8") as log:
        for line in log:
            LOG.debug(">>> %s", line)


async def copy_file_async(src: str, dst: str) -> None:
    await anyio.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    await anyio.to_thread.run_sync(shutil.copyfile, src, dst)


@define
class FactorioServer(anyio.abc.AsyncResource):
    tmpdir: str
    process: anyio.abc.Process
    port: int
    rcon: rcon.RCONClient
    world: World
    # Whether to clean up the tmpdir.
    # Set False if you want to inspect some files after the server shuts down
    delete_tmpdir = True

    async def aclose(self):
        """Performs server shutdown + file cleanup"""
        try:
            await self.rcon.aclose()
        finally:
            try:
                self.process.kill()
            except ProcessLookupError:
                # The raise that happens in here is what actually preserves the dir,
                # but may as well keep the data meaningful
                self.delete_tmpdir = False
                LOG.error(
                    "Process id %s was unexpectedly gone. Preserving %s for debugging",
                    self.process.pid,
                    self.tmpdir,
                )
                raise

        await self.process.wait()
        if "PYTEST_CURRENT_TEST" in os.environ:
            # When this fails in tests, print the server log to assist debugging
            debug_print_server_log(self.tmpdir)
        if self.delete_tmpdir:
            shutil.rmtree(self.tmpdir)

    def debug_print_server_log(self):
        """Prints the server's logs to our logs
        Use just for debugging
        """
        debug_print_server_log(self.tmpdir)

    async def save_world(self, target_file: str) -> None:
        """Save the game to the target_file
        target_file is relative to the cwd, if not absolute.
        It is recommended to suffix target_file with ".zip"
        """
        temp_name = str(uuid.uuid4()) + ".zip"
        # Saving is asynchronous, in order to know it's complete we will tail the logfile during the save
        # Seek end of log file before we issue our instruction
        async with await anyio.Path(get_server_log_path(self.tmpdir)).open(
            "rt"
        ) as logfile:
            await logfile.seek(0, os.SEEK_END)
            await self.rcon.send_command(f"/sc game.server_save('{temp_name}')")
            expected_out_path = anyio.Path(self.tmpdir, "saves", temp_name)
            # Allow 10 seconds for this
            deadline = time.time() + 10
            while time.time() < deadline:
                where = await logfile.tell()
                line = await logfile.readline()
                if not line or not line.endswith("\n"):
                    # we reached eof, reset to prior location to get a complete log line
                    await logfile.seek(where)
                    await anyio.sleep(0.1)
                elif "Saving finished" in line:
                    break
            else:
                raise Exception(
                    f"Timed out waiting for confirmation of saving finished for: {expected_out_path}"
                )
        # Use copy and delete strat to avoid "OSError: [Errno 18] Invalid cross-device link"
        await copy_file_async(str(expected_out_path), target_file)
        await expected_out_path.unlink()


async def _open_rcon(address: str, port: int, password: str) -> rcon.RCONClient:
    client = rcon.RCONClient(address, port, password)
    now = time.time()
    # Under continuous load, I have observed extremely rarely (1/1000 runs) the readiness of rcon taking over 15 seconds
    deadline = now + 20
    last_exception: Optional[Exception] = None
    while time.time() < deadline:
        try:
            await client.connect(2)
            last_exception = None
            break
        except ConnectionRefusedError as ex:
            last_exception = ex
        except TimeoutError as ex:
            last_exception = ex
    if last_exception is not None:
        raise last_exception
    return client


async def _try_create_server(config: FactorioServerConfig) -> FactorioServer:
    tmpdir = tempfile.mkdtemp()
    try:
        # write save file
        savefile_dir = anyio.Path(tmpdir, "saves")
        await savefile_dir.mkdir(parents=True, exist_ok=True)
        savefile_path = savefile_dir / "save.zip"
        async with await savefile_path.open("wb") as savefile:
            # TODO asyncio reads
            # Seek 0 because we may have read the file already in the case of a retry
            config.save_file_to_load.seek(0)
            for chunk in iter(lambda: config.save_file_to_load.read(16384), b""):
                await savefile.write(chunk)
        # write config ini, currently just to modify write-data dir
        config_ini_path = os.path.join(tmpdir, "config.ini")
        with open(config_ini_path, "wt", encoding="utf-8") as config_file:
            config_file.write(
                f"""\
[path]
read-data=__PATH__executable__/../../data
write-data={tmpdir}
            """
            )
        # write server-settings.json
        server_settings_json_path = os.path.join(tmpdir, "server-settings.json")
        with open(server_settings_json_path, "wt", encoding="utf-8") as ssjf:
            ssjf.write(SERVER_SETTINGS_JSON)
        mod_dir = os.path.join(tmpdir, "mods")
        await factorio_mod.install_mod(mod_dir)
        # Use the tmpdir name as the rconpw, this will catch the small (<1/1000) but non-zero chance
        # that the port from get_available_tcp_port() collides with another server and this client
        # attempts to connect to the wrong server.
        rconpw = os.path.basename(tmpdir)
        factorio_dir = config.factorio_install_folder or get_factorio_path()
        factorio_bin = os.path.join(factorio_dir, "bin", "x64", "factorio")
        port = ports.get_available_udp_port()
        rcon_port = ports.get_available_tcp_port()
        factorio_cmd = [
            factorio_bin,
            "--config",
            config_ini_path,
            "--mod-directory",
            mod_dir,
            "--bind",
            "127.0.0.1",
            "--port",
            str(port),
            "--rcon-bind",
            f"127.0.0.1:{rcon_port}",
            "--rcon-password",
            rconpw,
            "--server-settings",
            server_settings_json_path,
            "--start-server",
            str(savefile_path),
        ]
        LOG.debug("Launching server: %s", " ".join(factorio_cmd))
        process = await anyio.open_process(
            factorio_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=tmpdir,
        )
        try:
            rcon_client = await _open_rcon("127.0.0.1", rcon_port, rconpw)
            cur_tick_str: str = await rcon_client.send_command(
                "/silent-command rcon.print(game.tick)"
            )
            return FactorioServer(
                tmpdir=tmpdir,
                process=process,
                port=port,
                rcon=rcon_client,
                world=World(rcon_client, initial_tick=int(cur_tick_str)),
            )
        except:  # pylint: disable=bare-except
            try:
                process.kill()
                await process.wait()
            except ProcessLookupError:
                pass
            finally:
                raise
    except:  # pylint: disable=bare-except
        try:
            if "PYTEST_CURRENT_TEST" in os.environ:
                # When this fails in tests, print the server log to assist debugging
                debug_print_server_log(tmpdir)
        finally:
            shutil.rmtree(tmpdir)
            raise


async def create_server(config: FactorioServerConfig) -> FactorioServer:
    for _ in range(2):
        try:
            return await _try_create_server(config)
        except rcon.RCONAuthFailure as e:
            # Specifically in the case of RCONAuthFailure we will re-try
            # This error happens when the port allocation by OS gives us
            # the same port twice which is rare but has been observed in
            # soak tests
            LOG.warning("Retrying in response to %s", e)
    raise Exception("Ran out of server launch attemps, this is bizarrely unlikely")
