if [ "$#" -ne 1 ]; then
    echo "invalid arguments"
    echo "usage: build_docker.sh <image_repo>"
    exit 1
fi

if [ -z "$HYPERSH_ACCESS_KEY" ] || [ -z "$HYPERSH_SECRET" ] || [ -z "$HYPERSH_REGION" ]
then
      echo "Environment variables missing. HYPERSH_ACCESS_KEY, HYPERSH_SECRET, and HYPERSH_REGION all need to be set"
      exit 1
fi

REPO_PATH=$1

# get name from repo path , e.g. digiology/seleniumproxy -> seleniumproxy
IFS='/' read -a myarray <<< "$REPO_PATH"
REPO_NAME="${myarray[1]}"

echo 'building image'
BUILD_STDOUT=$(docker build -t $REPO_NAME:latest .)
echo 'finished building image'

IMAGE_ID=${BUILD_STDOUT: -12}
CONTAINER_ID=$(docker create $IMAGE_ID)
docker commit $CONTAINER_ID $REPO_NAME
docker tag $REPO_NAME $REPO_PATH
echo 'pushing to docker repo'
docker push $REPO_PATH
