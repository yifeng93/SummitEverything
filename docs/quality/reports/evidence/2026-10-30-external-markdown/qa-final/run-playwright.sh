#!/bin/zsh
set +e
web/node_modules/.bin/playwright test .local/qa/external-watch-20261030/external-watch.spec.ts --config .local/qa/external-watch-20261030/playwright.config.ts > .local/qa/external-watch-20261030/logs/playwright-final.log 2>&1
code=$?
printf "exit_code=%s\n" "$code" > .local/qa/external-watch-20261030/logs/playwright-final.exit
cat .local/qa/external-watch-20261030/logs/playwright-final.log
exit "$code"
