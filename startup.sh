#!/bin/bash
# -------- Selenium ---------
SELENIUM_DIR=/opt/selenium
SELENIUM_CONF=$SELENIUM_DIR/config.json

/opt/bin/generate_config >$SELENIUM_CONF

echo "starting selenium hub with configuration:"
cat $SELENIUM_CONF

if [ ! -z "$SE_OPTS" ]; then
  echo "appending selenium options: ${SE_OPTS}"
fi

function shutdown {
    echo "shutting down hub.."
    kill -s SIGTERM $NODE_PID
    wait $NODE_PID
    echo "shutdown complete"
}

exec java ${JAVA_OPTS} -jar $SELENIUM_DIR/selenium-server-standalone.jar \
  -role hub \
  -hubConfig $SELENIUM_CONF \
  ${SE_OPTS} &
NODE_PID=$!

trap shutdown SIGTERM SIGINT &
wait $NODE_PID &

# -------- 
hyper config --accesskey $HYPERSH_ACCESS_KEY --secretkey $HYPERSH_SECRET --default-region $HYPERSH_REGION
supervisord -c $SUPERVISOR_CFG &
jumbler