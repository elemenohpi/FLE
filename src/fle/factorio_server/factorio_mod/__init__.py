import importlib.resources
import os
import os.path

from anyio import Path, open_file

MOD_NAME = "factorio-learning-environment-mod"


async def install_mod(target_mods_dir: str) -> None:
    """Installs factorio-learning-environment-mod in to the given mods directory"""
    mod_dir = os.path.join(target_mods_dir, MOD_NAME)
    await Path(mod_dir).mkdir(parents=True, exist_ok=True)
    package_name = __package__ + "." + "mod_data"
    files = importlib.resources.contents(package_name)
    for filename in files:
        # TODO implement recursive copy for child dirs
        if (
            importlib.resources.is_resource(package_name, filename)
            and not filename == "__init__.py"
        ):
            # open_binary won't translate text line endings but this probably is fine for factorio
            with importlib.resources.open_binary(
                package=package_name, resource=filename
            ) as readable:
                # assume files are smallish and read entirety
                contents = readable.read()
            target_path = os.path.join(mod_dir, filename)
            async with await open_file(target_path, "wb") as target:
                await target.write(contents)
