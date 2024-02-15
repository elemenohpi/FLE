# How to contribute

`factorio-learning-environment` only runs on linux because it uses the Factorio headless server. Therefore development is also only supported on linux for simplicity. The entire developer setup is dockerized and shared between development and ci.

1. Get a shell inside the dev container by following the instructions in [.devcontainer/README.md](.devcontainer/README.md).

1. Setup for development
    
    Installs dependencies and `pre-commit` hooks
    ```bash
    make develop
    ```

1. Confirm that everything works before you change anything:
    ```bash
    make test
    ```

1. TODO, how to run the system
1. Add any changes you want
1. Add tests for the new changes
1. Consider whether there are any documentation changes which should go with your changes
1. Run `make codestyle` to format your changes.
1. Run `make test` to ensure that types, security and docstrings are okay.

## Some conventions / things to be aware of

Using [VSCode](https://code.visualstudio.com/) with our [`./.devcontainer`](./.devcontainer) is highly encouraged but not required, and no crucial development tasks should depend on it.

The library makes liberal use of [`attrs`](https://www.attrs.org/en/stable/index.html) for our dataclass-y needs. Use it!

The library is primarily async (cooperatively concurrent), in order to host the functionality behind a grpc service interface without the use of explicit threading, and therefore uses `asyncio` augmented with [`anyio`](https://anyio.readthedocs.io/en/stable/index.html). Feel free to use `anyio` wherever you like, especially when dealing with I/O.

### Configuring Developer Tooling

When possible, prefer to configure tools which are used in the repo via ambient configuration files such as `pyproject.toml` or other tool-specific `.rc`, `.ini` files.
This is so that the tools are correctly and consistently configured regardless of who is doing the invocation (eg. the Makefile, editor extensions, indirectly via other tools such as tox running pytest). If different contexts require different behaviours then of course some context-specific configuration passing is justified.

### Python / Lua tradeoffs

The library has 2 main ways to inspect and manipulate the Factorio game simulation: stringly-typed [RCON commands](https://wiki.factorio.com/Console), and the higher level strongly-typed [`World.call_mod()` API](./fle/src/factorio_server/world.py) which can make RPCs with structured requests and responses to lua functions implemented in a factorio mod [`./fle/src/factorio_server/factorio_mod`](./fle/src/factorio_server/factorio_mod).

This also means there are 2 distinct codebases / languages where functionality we need can live. When considering which side of the Lua/Python divide to implement features and which communication interface to use, consider the following principles (which may sometimes be in conflict).

- Prefer complexity in Python over complexity in Lua. The tooling, testing, and debuggability of our Python is far better than that of the Lua component.
- RCON is fine for simple interaction passing simple kinds of data in and out. If you find yourself assembling sizeable strings of complex Lua code for evaluation over RCON, or doing a bunch of ad hoc string parsing on responses, you should probably switch to structured interaction via the `World.call_mod()` API.
- Consider the Python - Lua round-trip overhead. It may be more appropriate to execute a compound operation entirely on the Lua side than to make several round trips between the processes. With that said, don't overthink it until we've actually invested in more tooling to know what's a bottleneck and what isn't.

One more important thing to know about Lua. In Lua there is only 1 type of compound object, the "table". Arrays are tables, Objects are tables.
This means an empty Lua object is indistinguishable from an empty Lua array. Yes, that does wreck serialized comms with Python.
As a result, if you are planning to return an object / dictionary from lua to the python and there's a chance the object is empty, just chuck in a redundant, non-nil key. Search for `_preserve_table` and you'll see examples.

## Common tasks

### Add a dependency
```bash
poetry add somelib
```
After adding a dependency (or a dev-dependency) VSCode's language server does not pick it up immediately.
You can force a re-fresh of its understanding via *Reload Window* from Command Palette.

### Add a dependency needed only in the developer setup
```bash
poetry add --dev somelib
```
If the dev dependency is needed during test runs by tox, you may also need to add it to `tox.ini`

### Recreate the tox environments if you get missing module errors after a dependency change
```bash
poetry run tox --recreate
```

### Regenerate the code generated with protoc
```bash
make proto
```

## Other Makefile Commands

### Installable Eggs
Builds the sdist and wheel files for publishing
```bash
make dist
```

### Codestyle

Automatic formatting uses `pyupgrade`, `isort` and `black`.

```bash
make codestyle
```

Codestyle checks only, without rewriting files:

```bash
make check-codestyle
```

> Note: `check-codestyle` uses `isort`, `black` and `darglint` library

### Update all dev libraries to the latest version using one comand

```bash
make update-dev-deps
```

### Code security

```bash
make check-safety
```
This command launches `Poetry` integrity checks as well as identifies security issues with `Safety` and `Bandit`.

### Type checks

Run `mypy` static type checker

```bash
make mypy
```

### Tests with coverage badges

Run `pytest`

```bash
make pytest
```
Check out coverage report in [./htmlcov/index.html](./htmlcov/index.html)

Run a specific test https://docs.pytest.org/en/latest/how-to/usage.html

```bash
pytest -k test_something
```

### Installable Eggs
Builds the sdist and wheel files for publishing
```bash
make dist
```

### All static and dynamic analysis / tests

```bash
make test
```
