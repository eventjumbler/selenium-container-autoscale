if [ "$#" -ne 2 ]; then
    echo "invalid arguments"
    echo "usage: build_hyper.sh <image_repo> <ip_address>"
    exit 1
fi

IMAGE_REPO=$1
IP_ADDRESS=$2

# remove existing containers
hyper rm -f $(hyper ps --filter ancestor=$IMAGE_REPO -aq)

hyper pull $IMAGE_REPO
hyper run -p 5000:5000 -d --name seleniumproxy -e HYPERSH_ACCESS_KEY=$HYPERSH_ACCESS_KEY -e HYPERSH_SECRET=$HYPERSH_SECRET -e HYPERSH_REGION=$HYPERSH_REGION $IMAGE_REPO
hyper fip attach $IP_ADDRESS $IMAGE_REPO
