#!/bin/sh

docker run \
	-p 8080:8080 \
	-v "$(pwd)/onchan.db:/app/onchan.db:rw" \
	-v "$(pwd)/onchan.log:/app/onchan.log:rw" \
	onchan:latest

