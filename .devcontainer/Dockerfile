FROM mcr.microsoft.com/vscode/devcontainers/base:bullseye

ENV LANG=C.UTF-8 \
  LC_ALL=C.UTF-8

# A space-separated list of python version in the container.
# We overload this in matrix CI to reduce container size and build time.
ARG PYTHON_VERSIONS="3.8.12 3.10.1"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # pyenv deps
    make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    # clang-format for proto
    clang-format \
    && rm -rf /var/lib/apt/lists/*

# Set vscode as the default user for consistency between vscode and other launch methods
USER vscode

# Install pyenv
RUN curl -sSL https://pyenv.run | bash

COPY .devcontainer/configure-shell-for-pyenv.sh /opt

RUN /opt/configure-shell-for-pyenv.sh

RUN for VERSION in $PYTHON_VERSIONS; do \
    /home/vscode/.pyenv/bin/pyenv install $VERSION; \
    done;

RUN /home/vscode/.pyenv/bin/pyenv global $PYTHON_VERSIONS

# Install Poetry (requires explicit pyenv shims path because docker doesnt get the pyenv shell setup)
RUN curl -sSL https://install.python-poetry.org | $(/home/vscode/.pyenv/bin/pyenv root)/shims/python && \
    /home/vscode/.local/bin/poetry config virtualenvs.create false

# Factorio server install
RUN version="1.1.101"\
    && archive="/tmp/factorio_headless_x64_$version.tar.xz" \
    && curl -sSL "https://www.factorio.com/get-download/$version/headless/linux64" -o "$archive" \
    && tar xf "$archive" --directory /home/vscode \
    && rm "$archive"

CMD ["/bin/bash"]
