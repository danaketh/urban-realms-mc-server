#!/bin/bash

# Name of the container running the Minecraft server
CONTAINER_NAME="minecraft"

# Path to the docker-compose file
COMPOSE_FILE="./docker-compose.yml"

# Step 1: Send a message to users
docker exec -i $CONTAINER_NAME rcon-cli say "Server will shut down in 10 seconds for maintenance."

# Step 2: Wait for 10 seconds
sleep 10

# Step 3: Save the world
docker exec -i $CONTAINER_NAME rcon-cli save-all

# Step 4: Stop the server (this will also kick all players)
docker exec -i $CONTAINER_NAME rcon-cli stop

# Step 5: Wait for the server to stop (waiting for an additional 10 seconds to make sure)
sleep 10

# Step 6: Stop the stack
docker-compose -f $COMPOSE_FILE down

echo "Minecraft server has been safely shut down."
