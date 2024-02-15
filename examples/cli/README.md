# cli example

*Doing your AI development in bash? We have just the thing.*

If you're not using the grpc tooling to get an interface from your chosen language,
the `fle` python package also provides a command line interface for interacting with its own server.

First install the `factorio-learning-environment` package using:
```bash
pip install factorio-learning-environment
```
Ensure `factorio-learning-environment` can find your factorio server by setting the environment variable `FACTORIO_PATH` or ensuring Factorio is available at the default location of `~/factorio`.

**See [`./cli-example.sh`](./cli-example.sh) for an end-to-end example of using the `fle` command-line interface**

In general to get command line help run:

```bash
fle --help
```

## Server

Start up the server and let it run for the entire duration you want to create and manipulate Factorio Learning Environments.
```bash
fle server
```

## Commands

```
$ fle call --help
Usage: fle call [OPTIONS] COMMAND [ARGS]...

  Call a remote method in the factorio-learning-environment server

Options:
  --hostname TEXT  What hostname the server is running at  [default:
                   127.0.0.1]
  --port INTEGER   What port the server is running on  [default: 64192]
  --help           Show this message and exit.

Commands:
  create-evaluator   Start an evaluator for a problem.
  create-world       Create a world and receive an initial observation
  destroy-evaluator  Shut down an evaluator
  evaluate-fitness   Evaluate the fitness of a solution.
```

## Shelling out

Note: When shelling out, depending on how your system / language is locating the progams to run,
you may have more success explicitly invoking `python -m fle ...` than the direct `fle` command.

These are some common ways people run other programs from the following languages:

- [Java](https://docs.oracle.com/javase/7/docs/api/java/lang/Runtime.html#exec(java.lang.String[]))
- [C/C++](https://man7.org/linux/man-pages/man3/system.3.html)
- [R](https://github.com/r-lib/processx)
