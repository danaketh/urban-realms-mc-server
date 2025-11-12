# Download System Documentation

## Overview

The new download system provides a flexible, cached approach to downloading Minecraft server components. It separates configuration from implementation and supports multiple download sources.

## Files

### config.yaml
Main configuration file that specifies:
- Minecraft version and source
- Fabric version and source
- Mods with their versions and sources

Each component includes a `source` field that references a source defined in `source_mappings.yaml`.

### source_mappings.yaml
Defines download sources and their configurations:
- **mojang**: Official Minecraft server downloads
- **fabric**: Fabric mod loader
- **modrinth**: Modrinth mod platform (primary)
- **curseforge**: CurseForge mod platform (future)
- **custom**: Direct download URLs

Each source specifies:
- Manifest URL patterns
- Target directories
- Filename patterns
- API requirements
- Project ID mappings (for special cases only)

**Modrinth Slug Resolution:**
The system resolves Modrinth project slugs in this order:
1. Check if a `slug` field is defined in the mod's config.yaml entry
2. Check if there's a mapping in `project_mappings` (for special cases)
3. Fall back to using the mod `name` as-is

This means you only need to add mappings for mods where the slug is completely different from the name.

### .download_cache.json
Automatically generated cache file containing:
- Minecraft version
- Resolved download URLs for all components
- Filenames and destinations
- Metadata for each download

This file allows fast re-downloads without re-resolving URLs from manifests.

## Usage

### First Time / Rebuild Cache

```bash
# Build download list and download everything
python bin/download.py --rebuild-cache

# This will:
# 1. Read config.yaml
# 2. Resolve all URLs from manifests
# 3. Download files
# 4. Save cache to .download_cache.json
```

### Using Cache

```bash
# Use existing cache (fast)
python bin/download.py

# This will:
# 1. Load .download_cache.json
# 2. Download files using cached URLs
# 3. Skip API calls to manifests
```

### Custom Paths

```bash
# Use custom file paths
python bin/download.py \
  --config my-config.yaml \
  --mappings my-mappings.yaml \
  --cache-file my-cache.json
```

## How It Works

### Workflow

```
┌─────────────┐
│ config.yaml │ ──┐
└─────────────┘   │
                  ├──> DownloadManager
┌──────────────────────┐   │
│ source_mappings.yaml │ ──┘
└──────────────────────┘
         │
         ▼
   Resolve URLs & Slugs
         │
         ▼
┌────────────────────┐
│ .download_cache.json│ <── Cache for future runs
└────────────────────┘
         │
         ▼
  Remove Old Versions
  (mods with same slug)
         │
         ▼
    Download Files
         │
         ▼
┌─────────────────┐
│ Local Files     │
│ - minecraft_server.jar
│ - fabric-server-launch.jar
│ - mods/sodium.jar    (slug-based naming)
│ - mods/lithium.jar
│ - mods/iris.jar
└─────────────────┘
```

### Mod File Naming

Mods are now downloaded using **slug-based filenames** for easier version management:
- Old system: `sodium-0.6.0-beta.2+mc1.21.1.jar` (version in filename)
- New system: `sodium.jar` (slug only, no version)

**Benefits:**
- Same filename across versions
- Automatic cleanup of old versions
- No accumulation of old mod files
- Easier to identify which mod is which

### URL Resolution

#### Minecraft (Mojang)
1. Fetch version manifest from Mojang
2. Find specific version entry
3. Fetch version-specific manifest
4. Extract server download URL

#### Fabric
1. Construct direct download URL using pattern:
   `https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{fabric_version}/server/jar`

#### Modrinth Mods
1. Determine project slug:
   - Use `slug` field from config.yaml if present
   - Otherwise check `project_mappings` for override
   - Fall back to mod `name` if no mapping exists
2. Fetch version list from Modrinth API using the slug
3. Filter by:
   - Exact version match
   - Fabric loader compatibility
   - Minecraft version compatibility
4. Extract download URL from matching version

#### Custom URLs
1. Use direct URL from config.yaml
2. Extract filename from URL

## Adding New Sources

### Example: Adding CurseForge Support

1. **Update source_mappings.yaml:**
```yaml
sources:
  curseforge:
    name: "CurseForge"
    api_base: "https://api.curseforge.com/v1"
    manifest_url: "https://api.curseforge.com/v1/mods/{project_id}/files"
    manifest_type: "curseforge"
    target_dir: "mods"
    requires_api_key: true
```

2. **Add resolver method in download.py:**
```python
def _resolve_curseforge_url(self, mod_name: str, version: str) -> Optional[Tuple[str, str]]:
    # Implementation here
    pass
```

3. **Update build_download_list() method:**
```python
elif source == 'curseforge':
    result = self._resolve_curseforge_url(mod_name, version)
```

4. **Update config.yaml for mods:**
```yaml
- name: "some-mod"
  version: "1.0.0"
  source: "curseforge"
  project_id: "12345"
```

## Cache Management

### When to Rebuild Cache

Rebuild the cache when:
- ✅ Minecraft version changes
- ✅ Mod versions change
- ✅ Adding/removing mods
- ✅ Cache file is corrupted
- ✅ Download URLs have expired

Keep using cache when:
- ✅ Re-downloading same version
- ✅ Recovering from failed downloads
- ✅ Setting up multiple servers with same config

### Cache Format

```json
{
  "minecraft_version": "1.21.1",
  "downloads": {
    "minecraft": {
      "type": "minecraft",
      "name": "Minecraft Server",
      "version": "1.21.1",
      "url": "https://...",
      "filename": "minecraft_server.jar",
      "target_dir": ".",
      "destination": "./minecraft_server.jar"
    },
    "fabric": {
      "type": "fabric",
      "name": "Fabric Loader",
      "version": "0.17.3",
      "url": "https://...",
      "filename": "fabric-server-launch.jar",
      "target_dir": ".",
      "destination": "./fabric-server-launch.jar"
    },
    "mod_ModName": {
      "type": "mod",
      "name": "ModName",
      "version": "1.0.0",
      "url": "https://...",
      "filename": "modname-1.0.0.jar",
      "target_dir": "mods",
      "destination": "mods/modname-1.0.0.jar"
    }
  }
}
```

## Error Handling

The download system handles:
- **Missing manifests**: Skips component with error message
- **404 errors**: Reports and continues
- **Network timeouts**: Reports and continues
- **Corrupted cache**: Falls back to rebuilding
- **Existing files**: Skips download (reports file size)
- **Failed downloads**: Removes partial files, reports failure

## Benefits Over Old System

### Old System (manifest.yaml)
- ❌ Hardcoded project IDs in separate file
- ❌ No caching - always resolves URLs
- ❌ Manual manifest maintenance
- ❌ Difficult to add new sources
- ❌ No version mismatch detection
- ❌ Version numbers in filenames (clutter)
- ❌ Old mod files accumulate

### New System
- ✅ Source information in config
- ✅ Fast cached downloads
- ✅ Automatic URL resolution
- ✅ Easy to extend with new sources
- ✅ Detects version mismatches
- ✅ Flexible mapping system
- ✅ Better error handling
- ✅ Slug-based filenames (clean)
- ✅ Auto-removes old versions

## Config Examples

### Using Slugs in config.yaml

Most mods can use their name directly:
```yaml
mods:
  - name: "sodium"
    version: "0.6.0-beta.2+mc1.21.1"
    source: "modrinth"
    # No slug needed - "sodium" works as-is
```

For mods where the slug differs from the name, add a `slug` field:
```yaml
mods:
  - name: "AmbientSounds"
    version: "6.1.4"
    source: "modrinth"
    slug: "ambientsounds"  # Modrinth slug is lowercase
```

For mods with completely different slugs, they're already mapped in `source_mappings.yaml`:
```yaml
mods:
  - name: "BetterThirdPerson"
    version: "1.9.0"
    source: "modrinth"
    # No slug needed - mapped to "better-third-person" in source_mappings.yaml
```

For custom download URLs:
```yaml
mods:
  - name: "preview_OptiFine"
    version: "1.21_HD_U_J1_pre9"
    source: "custom"
    download_url: "https://optifine.net/downloadx?f=preview_OptiFine_1.21_HD_U_J1_pre9.jar&x=8e5b3e3c"
```

## Usage Examples

### Standard Download
```bash
$ python bin/download.py --rebuild-cache

======================================================================
MINECRAFT SERVER DOWNLOAD MANAGER
======================================================================
No cache file found at .download_cache.json

Mode: Building new download list

======================================================================
BUILDING DOWNLOAD LIST
======================================================================

Resolving Minecraft 1.21.1...
  ✓ Found: minecraft_server.jar

Resolving Fabric 0.17.3...
  ✓ Found: fabric-server-launch.jar

Resolving 118 mods...
  [adorabuild-structures] ✓ adorabuild-structures.jar
  [aether] ✓ aether.jar
  [sodium] ✓ sodium.jar
  [lithium] ✓ lithium.jar
  ...

──────────────────────────────────────────────────────────────────
Total items resolved: 120

======================================================================
DOWNLOADING FILES
======================================================================

[Minecraft Server 1.21.1]
  Downloading: https://piston-data.mojang.com/...
  ✓ Downloaded: ./minecraft_server.jar (52,384,875 bytes)

[Fabric Loader 0.17.3]
  Downloading: https://meta.fabricmc.net/...
  ✓ Downloaded: ./fabric-server-launch.jar (1,234,567 bytes)

[sodium 0.6.0-beta.2+mc1.21.1]
  Downloading: https://cdn.modrinth.com/...
  ✓ Downloaded: mods/sodium.jar (823,456 bytes)

...

✓ Cache saved to: .download_cache.json

======================================================================
Download Summary: 120 successful, 0 failed
======================================================================
```

### Using Cache
```bash
$ python bin/download.py

======================================================================
MINECRAFT SERVER DOWNLOAD MANAGER
======================================================================
Loaded cache file: .download_cache.json

Mode: Using cached download list

======================================================================
USING CACHED DOWNLOAD LIST
======================================================================
Cached MC version: 1.21.1
Current MC version: 1.21.1
Total items: 120

======================================================================
DOWNLOADING FILES
======================================================================

[Minecraft Server 1.21.1]
  ℹ File exists: ./minecraft_server.jar (52,384,875 bytes)
  Skipping download

[sodium 0.6.0-beta.2+mc1.21.1]
  ℹ File exists: mods/sodium.jar (823,456 bytes)
  Skipping download

...

======================================================================
Download Summary: 120 successful, 0 failed
======================================================================
```

### Version Upgrade (Auto-cleanup)
```bash
# After updating sodium version in config.yaml from 0.6.0-beta.2 to 0.6.0-beta.3
$ python bin/download.py --rebuild-cache

======================================================================
BUILDING DOWNLOAD LIST
======================================================================
...
  [sodium] ✓ sodium.jar
...

======================================================================
DOWNLOADING FILES
======================================================================
...

[sodium 0.6.0-beta.3+mc1.21.1]
  ℹ Removing old version: mods/sodium.jar (823,456 bytes)
  Downloading: https://cdn.modrinth.com/...
  ✓ Downloaded: mods/sodium.jar (825,123 bytes)

...
======================================================================
```

**Note:** The old version is automatically removed and replaced with the new version, keeping the same filename.

## Migration from Old System

If you have the old `etc/manifest.yaml` system:

1. Keep your existing `config.yaml` mod list
2. Add `source: "modrinth"` to each mod (or use the updated config.yaml provided)
3. Use the new `source_mappings.yaml` (project mappings already included)
4. Run `python bin/download.py --rebuild-cache`
5. The old `etc/manifest.yaml` can be deleted

The new system automatically handles all the project ID mappings that were previously in manifest.yaml.
