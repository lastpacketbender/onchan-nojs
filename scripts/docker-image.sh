#!/bin/sh

docker build --tag onchan .
docker tag onchan:latest onchan:v1.0.0