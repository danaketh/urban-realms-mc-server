# Modrinth Slug Resolution System

## Overview

The download system now uses a smart, three-tier approach to resolve Modrinth project slugs, minimizing the need for manual mappings.

## How It Works

### Resolution Order

When downloading a mod from Modrinth, the system resolves the project slug in this priority order:

```
1. config.yaml 'slug' field (if present)
   ↓
2. source_mappings.yaml project_mappings (if defined)
   ↓
3. Mod 'name' as-is (fallback)
```

### Examples

#### Case 1: Name matches slug (most common)
```yaml
# config.yaml
- name: "sodium"
  version: "0.6.0-beta.2+mc1.21.1"
  source: "modrinth"
```

**Resolution:** Uses "sodium" directly (no mapping needed)

#### Case 2: Slug differs slightly from name
```yaml
# config.yaml
- name: "AmbientSounds"
  version: "6.1.4"
  source: "modrinth"
  slug: "ambientsounds"
```

**Resolution:** Uses "ambientsounds" from slug field

#### Case 3: Slug completely different
```yaml
# config.yaml
- name: "BetterThirdPerson"
  version: "1.9.0"
  source: "modrinth"

# source_mappings.yaml
project_mappings:
  BetterThirdPerson: "better-third-person"
```

**Resolution:** Uses "better-third-person" from project_mappings

## Benefits

### Before (Old System)
- ❌ All 118 mods required entries in manifest.yaml
- ❌ Duplicated information (name + slug for every mod)
- ❌ Hard to maintain
- ❌ Required updates in two places

### After (New System)
- ✅ Only ~40 special cases need mapping
- ✅ Most mods work with just name
- ✅ Easy to maintain
- ✅ Slug overrides in config.yaml when needed

## When to Use Each Method

### Use mod name as-is (no action needed)
When the Modrinth slug exactly matches your mod name:
- `sodium` → `sodium`
- `lithium` → `lithium`
- `iris` → `iris`
- `indium` → `indium`

### Use slug field in config.yaml
When the slug is a simple variation of the name:
- `AmbientSounds` → `ambientsounds` (case difference)
- `DistantHorizons` → `distanthorizons` (case difference)
- `ImmediatelyFast` → `immediatelyfast` (case difference)
- `CreativeCore` → `creativecore` (case difference)

### Use project_mappings in source_mappings.yaml
When the slug is completely different:
- `BetterThirdPerson` → `better-third-person`
- `BOMD` → `better-block-outline`
- `c2me` → `c2me-fabric`
- `voicechat` → `simple-voice-chat`
- `YetAnotherConfigLib` → `yacl`

## Implementation Details

### Code Flow

```python
def _resolve_modrinth_url(self, mod_name: str, version: str, slug: Optional[str] = None):
    source_config = self.mappings['sources']['modrinth']

    # Resolution priority:
    project_mappings = source_config.get('project_mappings', {})
    project_id = project_mappings.get(mod_name, slug or mod_name)

    # project_id now contains the correct slug to use
    manifest_url = source_config['manifest_url'].format(project_id=project_id)
    # ... continue with download
```

**Logic:**
1. `project_mappings.get(mod_name, ...)` checks for explicit mapping
2. If no mapping found, uses `slug` parameter (from config.yaml)
3. If slug is None, falls back to `mod_name`

### Adding a New Mod

**Simple case (slug matches name):**
```yaml
# config.yaml
mods:
  - name: "fabric-api"
    version: "0.115.0+1.21.1"
    source: "modrinth"
```

**Case variation:**
```yaml
# config.yaml
mods:
  - name: "ModMenu"
    version: "11.0.2"
    source: "modrinth"
    slug: "modmenu"
```

**Complex case:**
```yaml
# config.yaml
mods:
  - name: "EMI"
    version: "1.0.0"
    source: "modrinth"

# source_mappings.yaml (add this)
project_mappings:
  EMI: "emi-loot-tables"  # If slug is completely different
```

## Finding the Correct Slug

To find a mod's Modrinth slug:

1. **Visit the mod page:** https://modrinth.com/mod/[slug]
2. **Check the URL:** The slug is the last part of the URL
3. **Example:** For https://modrinth.com/mod/sodium, slug is `sodium`

Alternatively, search on Modrinth and copy the project slug from the URL.

## Current Mappings

As of the latest update, only **40** mods require special mappings (down from 118):

```yaml
project_mappings:
  architectury: "architectury-api"
  BetterThirdPerson: "better-third-person"
  BOMD: "better-block-outline"
  c2me: "c2me-fabric"
  citresewn: "cit-resewn"
  comforts: "comforts-fabric"
  cristellib: "cristel-lib"
  DungeonsArise: "when-dungeons-arise"
  DungeonsAriseSevenSeas: "when-dungeons-arise-seven-seas"
  enhancedblockentities: "ebe"
  Enhanced-Celestials: "enhanced-celestials"
  entity_model_features: "entity-model-features"
  entity_texture_features: "entitytexturefeatures"
  evenmoreinstruments: "even-more-instruments"
  FarmersDelight: "farmers-delight-fabric"
  ferritecore: "ferrite-core"
  friendsandfoes: "friends-and-foes"
  genshinstrument: "genshin-instrument"
  immersive_aircraft: "immersive-aircraft"
  itemscroller: "item-scroller"
  mcw-doors: "macaws-doors"
  mcw-trapdoors: "macaws-trapdoors"
  MouseTweaks: "mouse-tweaks"
  naturallychargedcreepers: "naturally-charged-creepers"
  notenoughanimations: "not-enough-animations"
  nyfsspiders: "nyfs-spiders"
  peepingcreepers: "peeping-creepers"
  physics-mod-pro: "physics-mod"
  refurbished_furniture: "refurbished-furniture"
  RyoamicLights: "ryoamic-lights"
  SereneSeasons: "serene-seasons"
  smallships: "small-ships"
  Sounds: "sound"
  spidersproducewebs: "spiders-produce-webs"
  t_and_t: "towns-and-towers"
  voicechat: "simple-voice-chat"
  wraith-waystones: "fwaystones"
  YetAnotherConfigLib: "yacl"
  YungsApi: "yungs-api"
  YungsBetterDungeons: "yungs-better-dungeons"
  zombieawareness: "zombie-awareness"
```

## Migration Guide

### From Old System

If you have mods in the old format:

**Before (etc/manifest.yaml):**
```yaml
mods:
  - name: "sodium"
    manifest: "https://api.modrinth.com/v2/project/sodium/version"
    file_pattern: "{download_url}"
```

**After (config.yaml):**
```yaml
mods:
  - name: "sodium"
    version: "0.6.0-beta.2+mc1.21.1"
    source: "modrinth"
    # That's it! No manifest needed.
```

### Adding Slugs to Existing Config

Most mods don't need changes. Only add `slug` if:
- The mod name has different casing than the slug
- The slug is a simple variation of the name

Check `source_mappings.yaml` first - if your mod is already mapped there, you don't need to do anything.

## Troubleshooting

### Mod Not Found Error

```
[MyMod] ✗ Failed
```

**Solutions:**
1. Check the Modrinth URL and get the correct slug
2. Add `slug` field to config.yaml
3. Or add mapping to source_mappings.yaml

### Wrong Mod Downloaded

If the wrong mod is downloaded, the slug resolution is incorrect:
1. Verify the mod's Modrinth slug
2. Add explicit `slug` in config.yaml or mapping in source_mappings.yaml
3. Rebuild cache with `--rebuild-cache`

## Best Practices

1. **Default approach:** Use mod name as-is (no slug needed)
2. **Simple variation:** Add `slug` to config.yaml
3. **Complex mapping:** Add to source_mappings.yaml project_mappings
4. **Document unusual cases:** Add comments in config.yaml explaining why a slug is needed
5. **Rebuild cache:** Always use `--rebuild-cache` after changing slugs or mappings
