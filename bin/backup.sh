#!/bin/bash

# Default values
METHOD="archive"
BACKUP_PATH="./"
CONTAINER_NAME="minecraft-server-minecraft-1"  # Change this to your container name
CONTAINER_PATH="/home/minecraft/server"  # Change this to the data directory in your container

# Parse arguments
if [ -n "$1" ]; then
  METHOD="$1"
fi
if [ -n "$2" ]; then
  BACKUP_PATH="$2"
fi

# Temporary directory for holding files
TEMP_DIR=$(mktemp -d)

# Function to download and copy files to a temporary directory
download_files() {
  docker cp "${CONTAINER_NAME}:${CONTAINER_PATH}" "$TEMP_DIR"
  if [ $? -eq 0 ]; then
    echo "Files downloaded to $TEMP_DIR"
  else
    echo "Failed to download files"
    exit 1
  fi
}

# Function to create an archive
create_archive() {
  tar -cJf "${BACKUP_PATH}/$(date +%Y%m%d%H%M%S).tar.xz" -C "$TEMP_DIR" .
}

# Function to commit files to Git LFS
commit_to_git_lfs() {
  cp -R "$TEMP_DIR/." "$BACKUP_PATH"
  cd "$BACKUP_PATH"
  git lfs track "*.*"
  git add .
  git commit -m "Automated server backup"
  git push origin master
}

# Function to backup with Restic
backup_with_restic() {
  restic -r "$BACKUP_PATH" backup "$TEMP_DIR"
}

# Function to backup with Rsync
backup_with_rsync() {
  rsync -av "$TEMP_DIR/" "$BACKUP_PATH"
}

# Function to backup with Rdiff-backup
backup_with_rdiff_backup() {
  rdiff-backup "$TEMP_DIR/" "$BACKUP_PATH"
}

# Download the files
download_files

# Backup according to the method
case "$METHOD" in
  archive)
    create_archive
    ;;
  git-lfs)
    commit_to_git_lfs
    ;;
  restic)
    backup_with_restic
    ;;
  rsync)
    backup_with_rsync
    ;;
  rdiff-backup)
    backup_with_rdiff_backup
    ;;
  *)
    echo "Invalid method. Supported methods are: archive, git-lfs, restic, rsync, rdiff-backup."
    exit 1
    ;;
esac

# Cleanup: Remove temporary directory
rm -rf "$TEMP_DIR"
