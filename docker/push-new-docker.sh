#!/bin/sh
# Authenticate 
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $(cat ECR_LINK)

# Build:
docker build --no-cache -t awsbatch/iams .

# Tag:
docker tag awsbatch/iams:latest $(cat ECR_LINK)/awsbatch/iams:latest

# Push:
docker push $(cat ECR_LINK)/awsbatch/iams:latest
