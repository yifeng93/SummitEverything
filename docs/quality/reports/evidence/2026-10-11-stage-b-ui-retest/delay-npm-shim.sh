#!/bin/zsh
date -u > "/Users/yifengstudio/.codex/worktrees/qa-stage-b-ui-retest/SummitEverything/.local/qa-ui/delay-npm.log"
sleep 5
exec /usr/local/bin/npm "$@"
