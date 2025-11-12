# Slug-Based File Naming for Mods

## Overview

Mods are now downloaded using **slug-based filenames** instead of version-specific filenames. This provides automatic version management and cleanup.

## File Naming

### Old System
```
mods/
├── sodium-0.6.0-beta.2+mc1.21.1.jar
├── lithium-0.13.0.jar
├── iris-1.8.0-beta.4+mc1.21.1.jar
└── ... (accumulates old versions)
```

After updating versions:
```
mods/
├── sodium-0.6.0-beta.2+mc1.21.1.jar  ← OLD VERSION REMAINS
├── sodium-0.6.0-beta.3+mc1.21.1.jar  ← NEW VERSION
├── lithium-0.13.0.jar
├── lithium-0.13.1.jar                ← DUPLICATE
└── ... (cluttered with old files)
```

### New System
```
mods/
├── sodium.jar        (always latest configured version)
├── lithium.jar       (always latest configured version)
├── iris.jar          (always latest configured version)
└── ... (clean, no duplicates)
```

After updating versions:
```
mods/
├── sodium.jar        ← AUTOMATICALLY REPLACED
├── lithium.jar       ← AUTOMATICALLY REPLACED
├── iris.jar
└── ... (old versions removed automatically)
```

## How It Works

### Download Process

1. **Resolve slug** using the three-tier system:
   - config.yaml `slug` field
   - source_mappings.yaml `project_mappings`
   - mod `name` as fallback

2. **Generate filename**: `{slug}.jar`
   - Example: `sodium` → `sodium.jar`
   - Example: `better-third-person` → `better-third-person.jar`

3. **Check for existing file**:
   - If `mods/{slug}.jar` exists → **Remove old version**
   - Then download new version

4. **Download**: Save to `mods/{slug}.jar`

### Code Implementation

```python
# Resolve slug
project_id = project_mappings.get(mod_name, slug or mod_name)

# Generate filename
filename = f"{project_id}.jar"

# Check and remove old version
if os.path.exists(f"mods/{filename}"):
    print(f"Removing old version: mods/{filename}")
    os.remove(f"mods/{filename}")

# Download new version
download(url, f"mods/{filename}")
```

## Benefits

### Version Management
✅ **No manual cleanup needed** - old versions automatically removed
✅ **Same filename across versions** - easier to track
✅ **No file accumulation** - mods directory stays clean
✅ **Clear version state** - config.yaml is source of truth

### Clarity
✅ **Easy to identify mods** - filename matches slug
✅ **No version confusion** - only one version exists
✅ **Consistent naming** - all mods follow same pattern

### Automation
✅ **Automatic updates** - just change version in config
✅ **Clean upgrades** - old file removed automatically
✅ **Rollback support** - change version back in config

## Examples

### Example 1: Simple Slug
```yaml
# config.yaml
- name: "sodium"
  version: "0.6.0-beta.2+mc1.21.1"
  source: "modrinth"
```

**Result:** `mods/sodium.jar`

### Example 2: Slug Override
```yaml
# config.yaml
- name: "AmbientSounds"
  version: "6.1.4"
  source: "modrinth"
  slug: "ambientsounds"
```

**Result:** `mods/ambientsounds.jar`

### Example 3: Mapped Slug
```yaml
# config.yaml
- name: "BetterThirdPerson"
  version: "1.9.0"
  source: "modrinth"

# source_mappings.yaml
project_mappings:
  BetterThirdPerson: "better-third-person"
```

**Result:** `mods/better-third-person.jar`

### Example 4: Custom Download
```yaml
# config.yaml
- name: "preview_OptiFine"
  version: "1.21_HD_U_J1_pre9"
  source: "custom"
  download_url: "https://optifine.net/downloadx?f=preview_OptiFine_1.21_HD_U_J1_pre9.jar"
```

**Result:** `mods/preview_OptiFine_1.21_HD_U_J1_pre9.jar` (uses filename from URL for custom sources)

## Upgrading Mods

### Workflow

1. **Update version in config.yaml:**
   ```yaml
   - name: "sodium"
     version: "0.6.0-beta.3+mc1.21.1"  # Changed from beta.2
     source: "modrinth"
   ```

2. **Rebuild cache and download:**
   ```bash
   python bin/download.py --rebuild-cache
   ```

3. **Output:**
   ```
   [sodium 0.6.0-beta.3+mc1.21.1]
     ℹ Removing old version: mods/sodium.jar (823,456 bytes)
     Downloading: https://cdn.modrinth.com/...
     ✓ Downloaded: mods/sodium.jar (825,123 bytes)
   ```

### Before/After

**Before upgrade:**
```
mods/
└── sodium.jar  (version 0.6.0-beta.2, 823,456 bytes)
```

**After upgrade:**
```
mods/
└── sodium.jar  (version 0.6.0-beta.3, 825,123 bytes)  ← REPLACED
```

## Cache Behavior

The cache stores the resolved slug for each mod:

```json
{
  "downloads": {
    "mod_sodium": {
      "type": "mod",
      "name": "sodium",
      "version": "0.6.0-beta.2+mc1.21.1",
      "url": "https://cdn.modrinth.com/...",
      "filename": "sodium.jar",
      "destination": "mods/sodium.jar",
      "slug": "sodium"
    }
  }
}
```

When using cached downloads, the same slug-based filename is used.

## Special Cases

### Custom Sources

Custom sources (non-Modrinth) extract filename from the download URL:

```yaml
- name: "CustomMod"
  source: "custom"
  download_url: "https://example.com/custommod-1.0.0.jar"
```

**Result:** `mods/custommod-1.0.0.jar` (filename from URL)

Custom sources don't use slug-based naming since they might not have consistent slugs.

### Minecraft & Fabric

Minecraft server and Fabric loader use fixed filenames:
- `minecraft_server.jar` (always)
- `fabric-server-launch.jar` (always)

These files are **not** automatically replaced when they exist. To update:
1. Delete the existing file manually, or
2. The download system will skip if file exists

## Troubleshooting

### Old Mod Files Not Removed

**Cause:** Filename doesn't match slug pattern

**Solution:**
```bash
# Manually remove old versioned files
rm mods/*-*.jar

# Then download with new system
python bin/download.py --rebuild-cache
```

### Wrong File Removed

**Cause:** Slug resolution is incorrect

**Solution:**
1. Verify the slug in source_mappings.yaml or config.yaml
2. Check the resolved filename in build output
3. Correct the slug if needed
4. Rebuild: `python bin/download.py --rebuild-cache`

### File Permission Error

**Cause:** Cannot delete existing file

**Solution:**
1. Check file permissions
2. Close any programs using the mod file
3. Manually delete the file if needed

## Migration from Old System

If you have old version-specific filenames:

### Step 1: Backup
```bash
cp -r mods mods.backup
```

### Step 2: Clean Old Files
```bash
# Remove all versioned mod files
rm mods/*-*.jar
```

### Step 3: Download with New System
```bash
python bin/download.py --rebuild-cache
```

### Step 4: Verify
```bash
ls mods/
# Should show:
# sodium.jar
# lithium.jar
# iris.jar
# ... (slug-based names only)
```

## Best Practices

1. **Use slug-based naming for all Modrinth mods** (automatic)
2. **Keep config.yaml as version source of truth**
3. **Rebuild cache after version changes**: `--rebuild-cache`
4. **Clean mods directory periodically** to remove any stray files
5. **Backup before major upgrades** (optional but recommended)

## Future Enhancements

Potential improvements:
- Archive old versions before deletion
- Version comparison and rollback commands
- Mod compatibility verification before upgrade
- Batch update all mods to latest versions
