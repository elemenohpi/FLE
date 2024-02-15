#! /bin/bash

set -euo pipefail

# Temp dir for our save files we will export for demo/testing purposes
DEBUG_SAVES_DIR=$(mktemp -d)

function cleanup {
  # Kill the fle server we're launching on exit
  # https://stackoverflow.com/questions/360201/how-do-i-kill-background-processes-jobs-when-my-shell-script-exits
  kill $(jobs -pr)
  # Delete the debug saves on exit
  rm -rf "$DEBUG_SAVES_DIR"
}

trap cleanup SIGINT SIGTERM EXIT

# Start server in background
fle server &

# Sleep 2s to allow server to start
sleep 2

evaluator=$(fle call create-evaluator STATIC SIZE_3X3 --no-deterministic)

for i in {1..3}
do
  observation_shape=$(fle call create-world $evaluator observation_data.txt)
  echo "observation_shape=$observation_shape"
  echo "observation_data.txt"
  cat observation_data.txt
  printf "\n"
  fle call get-connection-info $evaluator
  fle call save-world $evaluator "$DEBUG_SAVES_DIR/pre_evaluate_$i.zip"
  solution_shape="3,3"
  echo "4 0 0 4 0 0 4 0 0" > solution.txt
  fitness=$(fle call evaluate-fitness $evaluator $solution_shape solution.txt)
  echo "fitness=$fitness"
  fle call save-world $evaluator "$DEBUG_SAVES_DIR/post_evaluate_$i.zip"
done

fle call destroy-evaluator $evaluator
