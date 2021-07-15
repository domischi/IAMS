#!/bin/sh

# Assert that the git repo and all it's submodules are clean
if [ -z "$(git status --untracked-files=no --porcelain)" ]; then
    true # Equivalent of python's pass
else
    echo "Uncommitted changes, please first commit all changes, then run this script again... "
    exit
fi

# Update submodules
git submodule update --recursive --remote

# Assert that the submodules are included as well
if [ -z "$(git status --untracked-files=no --porcelain)" ]; then
    true # Equivalent of python's pass
else
    echo "There have been changes in the submodules, add them to the IAMS repo, then run this script again..."
    exit
fi

# Update remote version of IAMS (which is used to generate the docker container)
git push

# Authenticate 
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $(cat ECR_LINK)

# Build:
docker build --no-cache -t awsbatch/iams .

# Tag:
docker tag awsbatch/iams:latest $(cat ECR_LINK)/awsbatch/iams:latest

# Push:
docker push $(cat ECR_LINK)/awsbatch/iams:latest
