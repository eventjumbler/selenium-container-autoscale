#!/bin/bash
# -------- Selenium ---------
/opt/bin/entry_point.sh &
# -------- Server -----------
hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region $HYPERSH_REGION
supervisord -c $SUPERVISOR_CFG &
mode=[[ -z "$PROXY_MODE" ]] && mode="" || mode="-m $PROXY_MODE"
endpoint=[[ -z "$PROXY_SELENIUM_ENDPOINT" ]] && endpoint="" || endpoint="-ep $PROXY_SELENIUM_ENDPOINT"
debug=[[ "true" = "$PROXY_DEBUG" ]] && debug="" || debug="--debug"
cmd="jumbler $mode $endpoint $debug"
eval $cmd