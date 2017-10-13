
if [ "$#" -ne 1 ]; then
    echo "invalid arguments"
    echo "usage: build_docker.sh <image_repo>"
    exit 1
fi

REPO_PATH=$1

# get name from repo path , e.g. digiology/seleniumproxy -> seleniumproxy
IFS='/' read -a myarray <<< "$REPO_PATH"
REPO_NAME="${myarray[1]}"


BUILD_STDOUT=$(docker build -t $REPO_NAME:latest --build-arg HYPERSH_ACCESS_KEY=$HYPERSH_ACCESS_KEY --build-arg HYPERSH_SECRET=$HYPERSH_SECRET .)
CONTAINER_ID=${BUILD_STDOUT: -12}
docker commit $CONTAINER_ID serviceproxy_sanic
docker tag serviceproxy_sanic $REPO_PATH
docker push $REPO_PATH
