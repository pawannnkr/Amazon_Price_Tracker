#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Source configuration
if [ -f .dockerregistry ]; then
    source .dockerregistry
else
    echo -e "${RED}Error: .dockerregistry file not found${NC}"
    exit 1
fi

# Default values
REGISTRY=${1:-docker-hub}
BUILD_ONLY=${2:-false}

echo -e "${YELLOW}=== Docker Image Build & Push Script ===${NC}\n"

# Function to build image
build_image() {
    local image_name=$1
    echo -e "${YELLOW}Building image: $image_name${NC}"
    docker build -t "$image_name" .
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Build successful${NC}\n"
        return 0
    else
        echo -e "${RED}✗ Build failed${NC}\n"
        return 1
    fi
}

# Function to push image
push_image() {
    local image_name=$1
    local registry_name=$2
    
    echo -e "${YELLOW}Pushing image to $registry_name: $image_name${NC}"
    docker push "$image_name"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Push successful${NC}\n"
        return 0
    else
        echo -e "${RED}✗ Push failed${NC}\n"
        return 1
    fi
}

# Build based on registry
case "$REGISTRY" in
    docker-hub|hub)
        IMAGE_NAME="${DOCKER_USERNAME}/${DOCKER_IMAGE_NAME}:${DOCKER_IMAGE_TAG}"
        echo -e "${YELLOW}Target: Docker Hub${NC}"
        echo -e "Username: $DOCKER_USERNAME"
        echo -e "Image: $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG\n"
        
        build_image "$IMAGE_NAME"
        
        if [ "$BUILD_ONLY" != "true" ]; then
            echo -e "${YELLOW}Logging in to Docker Hub...${NC}"
            docker login -u "$DOCKER_USERNAME"
            push_image "$IMAGE_NAME" "Docker Hub"
        fi
        ;;
        
    gcr|gcp)
        IMAGE_NAME="gcr.io/${GCR_PROJECT_ID}/${GCR_IMAGE_NAME}:${GCR_IMAGE_TAG}"
        echo -e "${YELLOW}Target: Google Container Registry (GCR)${NC}"
        echo -e "Project: $GCR_PROJECT_ID"
        echo -e "Region: $GCR_REGION"
        echo -e "Image: $GCR_IMAGE_NAME:$GCR_IMAGE_TAG\n"
        
        build_image "$IMAGE_NAME"
        
        if [ "$BUILD_ONLY" != "true" ]; then
            echo -e "${YELLOW}Configuring gcloud...${NC}"
            gcloud config set project "$GCR_PROJECT_ID"
            gcloud auth configure-docker
            push_image "$IMAGE_NAME" "GCR"
        fi
        ;;
        
    ghcr|github)
        IMAGE_NAME="ghcr.io/${GHCR_USERNAME}/${GHCR_IMAGE_NAME}:${GHCR_IMAGE_TAG}"
        echo -e "${YELLOW}Target: GitHub Container Registry (GHCR)${NC}"
        echo -e "Username: $GHCR_USERNAME"
        echo -e "Image: $GHCR_IMAGE_NAME:$GHCR_IMAGE_TAG\n"
        
        build_image "$IMAGE_NAME"
        
        if [ "$BUILD_ONLY" != "true" ]; then
            echo -e "${YELLOW}Login to GHCR...${NC}"
            echo "Use your GitHub Personal Access Token (with read:packages scope)"
            docker login ghcr.io -u "$GHCR_USERNAME"
            push_image "$IMAGE_NAME" "GHCR"
        fi
        ;;
        
    artifactory|art)
        IMAGE_NAME="${ARTIFACTORY_REGISTRY}/${ARTIFACTORY_REPO}/${ARTIFACTORY_IMAGE_NAME}:${ARTIFACTORY_IMAGE_TAG}"
        echo -e "${YELLOW}Target: Artifactory${NC}"
        echo -e "Registry: $ARTIFACTORY_REGISTRY"
        echo -e "Repo: $ARTIFACTORY_REPO"
        echo -e "Image: $ARTIFACTORY_IMAGE_NAME:$ARTIFACTORY_IMAGE_TAG\n"
        
        build_image "$IMAGE_NAME"
        
        if [ "$BUILD_ONLY" != "true" ]; then
            push_image "$IMAGE_NAME" "Artifactory"
        fi
        ;;
        
    *)
        echo -e "${RED}Unknown registry: $REGISTRY${NC}"
        echo -e "\n${YELLOW}Usage:${NC}"
        echo "  ./build-and-push.sh <registry> [build-only]"
        echo ""
        echo -e "${YELLOW}Available registries:${NC}"
        echo "  - docker-hub   : Docker Hub"
        echo "  - gcr, gcp     : Google Container Registry"
        echo "  - ghcr, github : GitHub Container Registry"
        echo "  - artifactory  : Artifactory"
        echo ""
        echo -e "${YELLOW}Options:${NC}"
        echo "  build-only : Set to 'true' to only build without pushing"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo "  ./build-and-push.sh docker-hub                    # Build & push to Docker Hub"
        echo "  ./build-and-push.sh gcr                           # Build & push to GCR"
        echo "  ./build-and-push.sh docker-hub true               # Build only for Docker Hub"
        exit 1
        ;;
esac

echo -e "${GREEN}=== Done ===${NC}"
