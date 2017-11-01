#!/bin/bash
# -------- Selenium ---------
/opt/bin/entry_point.sh &
# -------- Server -----------
hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region $HYPERSH_REGION
supervisord -c $SUPERVISOR_CFG &
jumbler