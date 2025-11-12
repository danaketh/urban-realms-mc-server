FROM alpine:latest

## Build arguments - modify these to customize the build
#############################
ARG MC_USER=minecraft
ARG MC_GROUP=minecraft
ARG MC_SERVER_PATH=/opt/mc-server
ARG MC_MIN_MEMORY=2500M
ARG MC_MAX_MEMORY=4G
ARG JAVA_VERSION=17

## Dependencies
#############################
RUN apk --no-cache update \
    && apk --no-cache upgrade \
    && apk add --no-cache wget \
    openssl \
    bash \
    openjdk${JAVA_VERSION}-jre-headless \
    curl \
    python3 \
    py3-pip \
    py3-yaml

# Create minecraft user
RUN addgroup -S ${MC_GROUP} && adduser -S ${MC_USER} -G ${MC_GROUP}
USER ${MC_USER}:${MC_GROUP}

## Copy files to container
#############################
COPY --chown=${MC_USER}:${MC_GROUP} ./mc/etc ${MC_SERVER_PATH}
WORKDIR ${MC_SERVER_PATH}

# Copy config and download script
COPY --chown=${MC_USER}:${MC_GROUP} ./config.yaml ${MC_SERVER_PATH}/config.yaml
COPY --chown=${MC_USER}:${MC_GROUP} ./etc/manifest.yaml ${MC_SERVER_PATH}/etc/manifest.yaml
COPY --chown=${MC_USER}:${MC_GROUP} ./bin/download_server.py ${MC_SERVER_PATH}/download_server.py

# Download and install Minecraft server with Fabric
RUN python3 ${MC_SERVER_PATH}/download_server.py

# Copy mods
COPY --chown=${MC_USER}:${MC_GROUP} ./mc/mods ${MC_SERVER_PATH}/mods

# Agree to EULA and set up JVM arguments
RUN echo "eula=true" > ${MC_SERVER_PATH}/eula.txt \
    && echo "-Xms${MC_MIN_MEMORY}" > ${MC_SERVER_PATH}/user_jvm_args.txt \
    && echo "-Xmx${MC_MAX_MEMORY}" >> ${MC_SERVER_PATH}/user_jvm_args.txt \
    && echo "-Dterminal.jline=false" >> ${MC_SERVER_PATH}/user_jvm_args.txt

COPY --chown=${MC_USER}:${MC_GROUP} ./bin/entrypoint.sh ${MC_SERVER_PATH}/entrypoint.sh

## Final setup
#############################
WORKDIR ${MC_SERVER_PATH}
ENTRYPOINT [ "/bin/sh", "-c", "${MC_SERVER_PATH}/entrypoint.sh" ]