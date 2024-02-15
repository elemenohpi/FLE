# Dev Container for factorio-learning-environment

This container can be used:

- As a VSCode devcontainer
- As a github codespace
- Directly via docker commands
- As an environment for github actions

## VSCode Devcontainer

Using the [Remote Containers plugin](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) run the vscode command `Remote-Containers: Reopen in contaner`.

## github codespace

Untested: See https://github.com/features/codespaces

## Directly via docker commands

Build (from root of repo)

```bash
docker build -t factorio_learning_environment:latest . -f ./.devcontainer/Dockerfile --no-cache
```

Get a shell (from root of repo)

- Mac/Linux

  ```bash
  docker run -it --rm -v "$(pwd):/workspaces/factorio-learning-environment" -w /workspaces/factorio-learning-environment  factorio_learning_environment /bin/bash
  ```

- Windows Powershell

  ```powershell
  docker run -it --rm -v "$(Get-Location):/workspaces/factorio-learning-environment" -w /workspaces/factorio-learning-environment factorio_learning_environment /bin/bash
  ```

- Windows Batch

  ```batch
  docker run -it --rm -v "%cd%:/workspaces/factorio-learning-environment" -w /workspaces/factorio-learning-environment factorio_learning_environment /bin/bash
  ```

Cleanup, if desired

```bash
docker rmi -f factorio_learning_environment:latest
```
