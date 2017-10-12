
if [ "$#" -ne 1 ]; then
    echo "invalid arguments"
    echo "usage: build_docker.sh <image_repo>"
    exit 1
fi

REPO_NAME=$1

BUILD_STDOUT=$(docker build -t serviceproxy_sanic_async:latest --build-arg HYPERSH_ACCESS_KEY=$HYPERSH_ACCESS_KEY --build-arg HYPERSH_SECRET=$HYPERSH_SECRET .)
CONTAINER_ID=${BUILD_STDOUT: -12}
docker commit $CONTAINER_ID serviceproxy_sanic
docker tag serviceproxy_sanic $REPO_NAME
docker push $REPO_NAME
