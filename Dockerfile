FROM alpine:latest

## Dependencies
#############################
RUN apk --no-cache update \
    && apk --no-cache upgrade \
    && apk add --no-cache wget \
    openssl \
    bash \
    openjdk17-jre-headless \
    curl

# Create minecraft user
RUN addgroup -S minecraft && adduser -S minecraft -G minecraft
USER minecraft:minecraft

## Copy files to container
#############################
COPY --chown=minecraft:minecraft ./forge /home/minecraft/server
COPY --chown=minecraft:minecraft ./etc /home/minecraft/server
COPY --chown=minecraft:minecraft ./mods /home/minecraft/server/mods
# Agree to EULA and overwrite the original run.sh. I'm overwriting the original here
# so I can always simply extract the latest version of Forge and just modify what changes.
RUN echo "eula=true" > /home/minecraft/server/eula.txt \
    && echo "#!/usr/bin/env sh" > /home/minecraft/server/run.sh \
    && echo "# Forge requires a configured set of both JVM and program arguments." >> /home/minecraft/server/run.sh \
    && echo "# Add custom JVM arguments to the user_jvm_args.txt" >> /home/minecraft/server/run.sh \
    && echo "# Add custom program arguments {such as nogui} to this file in the next line before the ""$@"" or" >> /home/minecraft/server/run.sh \
    && echo "#  pass them to this script directly" >> /home/minecraft/server/run.sh \
    && echo "java @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.1.0/unix_args.txt ""nogui $@""" >> /home/minecraft/server/run.sh \
    && rm /home/minecraft/server/run.bat

COPY ./bin/entrypoint.sh /home/minecraft/server/entrypoint.sh

## Final setup
#############################
WORKDIR /home/minecraft/server
