- Miscellaneous TODO comments
- Figure out matrix addressing / rowmajor stuff
  In essence, I believe if we want the code to say to say `[x][y]` then the printed matrix will not match what we see in factorio.
  Maybe with some rigorous coordinate transform layer at the factorio api we can have our cake and eat it. This is probably not worth.
  We could just write `mat[y][x]` everywhere?
- Document concepts in library
- Create grpc example (java / c++?)
- Dig deeper in to the issue where tox doesn't seem to respect addition of dependencies to the production dist between runs.
- Review lack of async when using importlib.resources
- Consider making a command line command to install our mod in to your own standard graphical Factorio install.
- Explore "rendering" of runs, either make getting replays easy, or have a live connected client or something.
- Switch away from https://github.com/efokschaner/python-betterproto to their official 2.0 release once it's out.
- More sophisticated Docs approach / gh-pages?
- Make benchmarks
- Make factorio server shutdown failsafe. Maybe an internal heartbeat inside the mod? Maybe orphan detection on launch? Maybe a small wrapper process to watch parent and kill factorio if gone.
- Encoding generalisation(?)

# Adapt / delete Leftover steps from generator

### Building and releasing your package

Building a new version of the application contains steps:

- Bump the version of your package `poetry version <version>`. You can pass the new version explicitly, or a rule such as `major`, `minor`, or `patch`. For more details, refer to the [Semantic Versions](https://semver.org/) standard.
- Make a commit to `GitHub`.
- Create a `GitHub release`.
- And... publish 🙂 `poetry publish --build`

### Deployment features

- `GitHub` integration: issue and pr templates.
- `Github Actions` with predefined [build workflow](https://github.com/DrKenReid/factorio-learning-environment/blob/master/.github/workflows/build.yml) as the default CI/CD.
- Everything is already set up for security checks, codestyle checks, code formatting, testing, linting, docker builds, etc with [`Makefile`](https://github.com/DrKenReid/factorio-learning-environment/blob/master/Makefile#L89). More details in [makefile-usage](#makefile-usage).
- [Dockerfile](https://github.com/DrKenReid/factorio-learning-environment/blob/master/.devcontainer/Dockerfile) for your package.
- Always up-to-date dependencies with [`@dependabot`](https://dependabot.com/). You will only [enable it](https://docs.github.com/en/github/administering-a-repository/enabling-and-disabling-version-updates#enabling-github-dependabot-version-updates).

### Open source community features

- Ready-to-use [Pull Requests templates](https://github.com/DrKenReid/factorio-learning-environment/blob/master/.github/PULL_REQUEST_TEMPLATE.md) and several [Issue templates](https://github.com/DrKenReid/factorio-learning-environment/tree/master/.github/ISSUE_TEMPLATE).
- Files such as: `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` are generated automatically.
- [`Stale bot`](https://github.com/apps/stale) that closes abandoned issues after a period of inactivity. (You will only [need to setup free plan](https://github.com/marketplace/stale)). Configuration is [here](https://github.com/DrKenReid/factorio-learning-environment/blob/master/.github/.stale.yml).
- [Semantic Versions](https://semver.org/) specification with [`Release Drafter`](https://github.com/marketplace/actions/release-drafter).


## 📈 Releases

You can see the list of available releases on the [GitHub Releases](https://github.com/DrKenReid/factorio-learning-environment/releases) page.

We follow [Semantic Versions](https://semver.org/) specification.
