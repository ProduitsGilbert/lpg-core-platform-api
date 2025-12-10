#!/bin/bash

# LPG Core Platform API Deployment Script
# This script handles deployment to production server

set -e  # Exit on any error

# Configuration - Update these variables for your environment
DOCKER_REGISTRY="${DOCKER_REGISTRY:-your-registry}"
IMAGE_NAME="${IMAGE_NAME:-lpg-core-platform-api}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/lpg-core-platform-api}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."

    # Check if docker is available
    if ! command_exists docker; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check if docker-compose is available
    if ! command_exists docker-compose; then
        log_error "docker-compose is not installed or not in PATH"
        exit 1
    fi

    # Check if .env.prod exists
    if [ ! -f ".env.prod" ]; then
        log_error ".env.prod file not found. Please create it from .env.example"
        exit 1
    fi

    log_info "Pre-deployment checks passed"
}

# Deploy function
deploy() {
    local image_tag="${1:-latest}"

    log_info "Starting deployment of ${IMAGE_NAME}:${image_tag}"

    # Pull the latest image
    log_info "Pulling Docker image..."
    docker pull "${DOCKER_REGISTRY}/${IMAGE_NAME}:${image_tag}"

    # Tag as latest if deploying a specific version
    if [ "$image_tag" != "latest" ]; then
        docker tag "${DOCKER_REGISTRY}/${IMAGE_NAME}:${image_tag}" "${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
    fi

    # Navigate to deployment directory (if running remotely)
    if [ -n "$DEPLOY_DIR" ] && [ "$DEPLOY_DIR" != "$(pwd)" ]; then
        log_info "Changing to deployment directory: $DEPLOY_DIR"
        cd "$DEPLOY_DIR" || {
            log_error "Failed to change to deployment directory: $DEPLOY_DIR"
            exit 1
        }
    fi

    # Stop existing containers gracefully
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" down --timeout 30 || {
        log_warn "Graceful shutdown failed, forcing shutdown..."
        docker-compose -f "$COMPOSE_FILE" down --timeout 10 --remove-orphans || {
            log_error "Failed to stop containers"
            exit 1
        }
    }

    # Start new containers
    log_info "Starting new containers..."
    docker-compose -f "$COMPOSE_FILE" up -d

    # Wait for health check
    log_info "Waiting for application to be healthy..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:7003/healthz >/dev/null 2>&1; then
            log_info "Application is healthy!"
            break
        fi

        log_info "Waiting for health check... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Application failed to become healthy within expected time"
        log_error "Check logs: docker-compose -f $COMPOSE_FILE logs"
        exit 1
    fi

    # Clean up old images
    log_info "Cleaning up old Docker images..."
    docker image prune -f

    log_info "Deployment completed successfully!"
}

# Rollback function
rollback() {
    local target_image="${1:-previous}"

    log_info "Starting rollback..."

    if [ "$target_image" = "previous" ]; then
        # Try to find the previous image
        local previous_image
        previous_image=$(docker images "${DOCKER_REGISTRY}/${IMAGE_NAME}" --format "{{.Repository}}:{{.Tag}}" | sed -n '2p')

        if [ -z "$previous_image" ]; then
            log_error "No previous image found for rollback"
            exit 1
        fi

        log_info "Rolling back to: $previous_image"
        docker tag "$previous_image" "${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
    else
        # Rollback to specific image
        log_info "Rolling back to: ${DOCKER_REGISTRY}/${IMAGE_NAME}:${target_image}"
        docker tag "${DOCKER_REGISTRY}/${IMAGE_NAME}:${target_image}" "${DOCKER_REGISTRY}/${IMAGE_NAME}:latest"
    fi

    # Restart with rolled back image
    log_info "Restarting with rolled back image..."
    docker-compose -f "$COMPOSE_FILE" down
    docker-compose -f "$COMPOSE_FILE" up -d

    log_info "Rollback completed"
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS] COMMAND"
    echo ""
    echo "Commands:"
    echo "  deploy [IMAGE_TAG]    Deploy application (default: latest)"
    echo "  rollback [IMAGE_TAG]  Rollback to previous or specific image"
    echo "  status                Show deployment status"
    echo "  logs                  Show application logs"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -r, --registry REG   Docker registry (default: $DOCKER_REGISTRY)"
    echo "  -i, --image NAME     Image name (default: $IMAGE_NAME)"
    echo "  -d, --dir DIR        Deployment directory (default: $DEPLOY_DIR)"
    echo "  -f, --file FILE      Compose file (default: $COMPOSE_FILE)"
    echo ""
    echo "Examples:"
    echo "  $0 deploy"
    echo "  $0 deploy v1.2.3"
    echo "  $0 rollback"
    echo "  $0 rollback v1.1.0"
    echo "  $0 -r myregistry -i myapp deploy"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -r|--registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -d|--dir)
            DEPLOY_DIR="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        deploy|rollback|status|logs)
            COMMAND="$1"
            shift
            break
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
case "${COMMAND:-deploy}" in
    deploy)
        pre_deployment_checks
        deploy "${1:-latest}"
        ;;
    rollback)
        rollback "${1:-previous}"
        ;;
    status)
        log_info "Deployment Status:"
        docker-compose -f "$COMPOSE_FILE" ps
        echo ""
        log_info "Container Health:"
        curl -s http://localhost:7003/healthz || echo "Health check failed"
        ;;
    logs)
        log_info "Application Logs:"
        docker-compose -f "$COMPOSE_FILE" logs -f --tail=100
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
