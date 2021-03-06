#!/bin/bash
REPO=$1
COMMIT=$2
BRANCH=$3

run_or_fail() {
  local explanation=$1
  shift 1
  "$@"
  if [ $? != 0 ]; then
    echo $explanation 1>&2
    exit 1
  fi
}

run_or_fail "Repository folder not found" pushd "$REPO" 1> /dev/null
run_or_fail "Could not clean repository" git clean -d -f -x
run_or_fail "Could not call git pull" git pull origin $BRANCH
run_or_fail "Could not update to given commit hash" git reset --hard "$COMMIT"
