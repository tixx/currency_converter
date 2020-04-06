#!/bin/bash
imageName=xx:currency_converter
containerName=cc

docker build -t $imageName -f Dockerfile  .

echo Delete old container...
docker rm -f $containerName

echo Run new container...
docker run -d -p 8080:8080 --name $containerName $imageName
