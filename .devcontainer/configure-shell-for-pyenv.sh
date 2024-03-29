#!/bin/bash

# the sed invocation inserts the lines at the start of the file
# after any initial comment lines
sed -Ei -e '/^([^#]|$)/ {a \
export PYENV_ROOT="$HOME/.pyenv"
a \
export PATH="$PYENV_ROOT/bin:$PATH"
a \
' -e ':a' -e '$!{n;ba};}' ~/.bashrc
echo 'eval "$(pyenv init --path)"' >>~/.bashrc

echo 'eval "$(pyenv init -)"' >> ~/.bashrc
