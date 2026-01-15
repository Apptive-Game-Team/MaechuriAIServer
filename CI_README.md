# CI/CD Configuration

This repository uses GitHub Actions for Continuous Integration (CI) to automatically build and push Docker images to GitHub Container Registry (GHCR).

## Overview

The CI workflow automatically:
- Builds a Docker image of the FastAPI application
- Pushes the image to GitHub Container Registry (ghcr.io)
- Tags images with branch names, commit SHAs, and `latest` for the default branch

## Setup Required

### 1. Configure GitHub Secrets

The CI workflow requires two secrets to be configured in your GitHub repository:

1. **GHCR_USER**: Your GitHub username
2. **GHCR_TOKEN**: A GitHub Personal Access Token (PAT) with `write:packages` permission

#### How to create a GitHub Personal Access Token:

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "GHCR CI Token")
4. Select the following scopes:
   - `write:packages` (to push images)
   - `read:packages` (to pull images)
   - `delete:packages` (optional, to delete old images)
5. Click "Generate token"
6. Copy the token (you won't be able to see it again!)

#### How to add secrets to your repository:

1. Go to your repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add `GHCR_USER` with your GitHub username
5. Add `GHCR_TOKEN` with the personal access token you created

### 2. Workflow Triggers

The CI workflow runs automatically when:
- Code is pushed to `main` or `develop` branches
- A pull request is opened targeting `main` or `develop` branches

## Docker Image

The Docker image is built using:
- **Base image**: `python:3.12-slim`
- **Application**: FastAPI app running on port 8000
- **Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Image Tags

Images are tagged with:
- Branch name (e.g., `ghcr.io/apptive-game-team/maechuriaiserver:main`)
- Branch and commit SHA (e.g., `ghcr.io/apptive-game-team/maechuriaiserver:main-abc1234`)
- `latest` tag for the default branch

### Pulling the Image

Once the workflow runs successfully, you can pull the image:

```bash
# Login to GHCR
echo $GHCR_TOKEN | docker login ghcr.io -u $GHCR_USER --password-stdin

# Pull the image
docker pull ghcr.io/apptive-game-team/maechuriaiserver:latest

# Run the container
docker run -d -p 8000:8000 --env-file .env ghcr.io/apptive-game-team/maechuriaiserver:latest
```

## Files

- **Dockerfile**: Defines how to build the Docker image
- **.dockerignore**: Specifies files to exclude from the Docker build context
- **.github/workflows/ci.yml**: GitHub Actions workflow configuration

## Continuous Deployment (CD)

The CI workflow only builds and pushes Docker images. For deployment, the server can pull the latest image using:

```bash
docker pull ghcr.io/apptive-game-team/maechuriaiserver:latest
docker-compose up -d
```

This follows the pull-based deployment model mentioned in the issue.
