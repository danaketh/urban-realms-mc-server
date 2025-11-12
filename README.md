# Minecraft Server

Docker stack for a Minecraft server on which I'm playing with my kids and friends. It contains whatever
I found useful or fun for our gameplay. It's heavily modded, so be prepared for that.

## Requirements

- Docker
- Python 3.7+ (for management scripts)

Software-wise you'll only need `docker-compose` for running the server. The management scripts
require Python 3.7 or newer for downloading and updating mods.

Server is configured to eat a minimum of 2.5GB or memory and a maximum of 4GB. So if you're
going to run it on VPS, 8GB RAM might be a decent amount to have there "just in case".

## Configuration

### Environment Setup

The management scripts support `.env` files for configuration. This is especially useful for API keys.

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your configuration:
   ```bash
   # CurseForge API Key (required for CurseForge mods)
   # Get from: https://console.curseforge.com/
   CURSEFORGE_API_KEY=your_api_key_here
   ```

3. The `.env` file is automatically loaded by all scripts and is gitignored for security.

See `bin/README.md` for detailed script documentation.

## Installation

