# Update Script Examples

This document provides examples of how to use the update scripts.

## Example 1: Full Compatibility Check

This is the recommended approach for finding safe updates.

```bash
# Run the full compatibility check
$ python bin/check_updates.py --full-check

======================================================================
COMPREHENSIVE UPDATE COMPATIBILITY CHECK
======================================================================
Current configuration:
  Minecraft: 1.20.1
  Fabric:    0.15.0
  Mods:      25

Found 3 newer MC version(s) to test
Testing compatibility (MC version → Fabric version → Mods)...

──────────────────────────────────────────────────────────────────────
Testing Minecraft 1.21.2...
  Found 15 Fabric version(s)
    Testing Fabric 0.16.5...
      ✗ 3 mod(s) incompatible: WorldEdit, Terralith, Structory
    Testing Fabric 0.16.4...
      ✗ 2 mod(s) incompatible: WorldEdit, Terralith
  ⚠ No compatible Fabric version found for MC 1.21.2
  ⚠ Cannot update to MC 1.21.2 - stopping here

──────────────────────────────────────────────────────────────────────
Testing Minecraft 1.21.1...
  Found 12 Fabric version(s)
    Testing Fabric 0.16.0...
      ✓ All 25 mod(s) compatible!

======================================================================
✓ COMPATIBLE UPDATE FOUND!
======================================================================
  Minecraft: 1.20.1 → 1.21.1
  Fabric:    0.15.0 → 0.16.0
  Mods:      25 updated

======================================================================
✓ Compatibility report saved to: compatibility_report.json
  This file can be used with apply_updates.py to perform the update
======================================================================
```

## Example 2: Applying the Compatible Update

```bash
# Preview the update first
$ python bin/apply_updates.py --input compatibility_report.json --dry-run

======================================================================
MINECRAFT SERVER UPDATE APPLIER
======================================================================

⚠ DRY RUN MODE - No changes will be made

Update file: compatibility_report.json
Generated:   2025-11-08T14:30:00.000000
Report type: Full Compatibility Check
Status:      Compatible update found
Tested:      2 MC versions, 1 Fabric versions

----------------------------------------------------------------------
MINECRAFT SERVER
----------------------------------------------------------------------

  Minecraft server update:
    Current: 1.20.1
    Target:  1.21.1

  [DRY RUN] Would update Minecraft server

----------------------------------------------------------------------
FABRIC LOADER
----------------------------------------------------------------------

  Fabric loader update:
    Current: 0.15.0
    Target:  0.16.0

  [DRY RUN] Would update Fabric loader

----------------------------------------------------------------------
MODS
----------------------------------------------------------------------

  Found 25 mod update(s)

  [WorldEdit]
    Version: 7.3.0
    [DRY RUN] Would download from https://cdn.modrinth.com/...

  [Terralith]
    Version: 2.5.0
    [DRY RUN] Would download from https://cdn.modrinth.com/...

  ... (23 more mods)

  Summary: 25 successful, 0 failed

======================================================================

⚠ This was a dry run. Run without --dry-run to apply updates.
```

## Example 3: Standard Update Check

For individual component updates without comprehensive testing:

```bash
# Check all components
$ python bin/check_updates.py

======================================================================
MINECRAFT SERVER UPDATE CHECK
======================================================================
Current version: 1.20.1
Latest release:  1.21.2
Latest snapshot: 24w45a

  📦 3 newer release(s) available:
     • 1.21.2
     • 1.21.1
     • 1.21

======================================================================
FABRIC LOADER UPDATE CHECK
======================================================================
Current Fabric version: 0.15.0
Target MC version:      1.20.1
Latest Fabric version:  0.16.5

  📦 5 newer version(s) available:
     • 0.16.5
     • 0.16.4
     • 0.16.3
     • 0.16.2
     • 0.16.1

======================================================================
MOD UPDATE CHECK
======================================================================
Target MC version: 1.20.1
Checking 25 mods...

  [WorldEdit]
    Current: 7.2.15
    Latest:  7.3.0
    📦 Update available!

  [Terralith]
    Current: 2.4.4
    Latest:  2.5.0
    📦 Update available!

  ... (more mods)

  ──────────────────────────────────────────────────────────────────
  Summary: 20 up-to-date | 5 updates available | 0 errors

======================================================================
UPDATE SUMMARY
======================================================================

Minecraft Server:
  ⚠ 3 newer version(s) available (latest: 1.21.2)

Fabric Loader:
  ⚠ 5 newer version(s) available (latest: 0.16.5)

Mods:
  ⚠ 5 mod(s) with updates available
     • WorldEdit: 7.2.15 → 7.3.0
     • Terralith: 2.4.4 → 2.5.0
     ... and 3 more

======================================================================

Update information saved to: updates.json
Total components with updates: 7
```

## Example 4: Check Specific MC Version Compatibility

Test if you can upgrade to a specific Minecraft version:

```bash
$ python bin/check_updates.py --mc-version 1.21.1 --fabric --mods

======================================================================
FABRIC LOADER UPDATE CHECK
======================================================================
Current Fabric version: 0.15.0
Target MC version:      1.21.1
Latest Fabric version:  0.16.0

  📦 5 newer version(s) available:
     • 0.16.0
     • 0.15.11
     ... and 3 more

======================================================================
MOD UPDATE CHECK
======================================================================
Target MC version: 1.21.1
Checking 25 mods...

  [WorldEdit]
    Current: 7.2.15
    Latest:  7.3.0
    📦 Update available!

  ... (shows which mods are compatible with MC 1.21.1)
```

## Example 5: Update Only Mods

If you just want to update mods for your current MC/Fabric version:

```bash
# Check for mod updates
$ python bin/check_updates.py --mods

# Apply only mod updates
$ python bin/apply_updates.py --mods

----------------------------------------------------------------------
MODS
----------------------------------------------------------------------

  Found 5 mod update(s)

  [WorldEdit]
    7.2.15 → 7.3.0
  Downloading from https://cdn.modrinth.com/data/.../worldedit-mod-7.3.0.jar...
  ✓ Downloaded to mods/worldedit-mod-7.3.0.jar

  ... (more mods)

  Summary: 5 successful, 0 failed
```

## Key Differences

### Standard Check (`check_updates.py`)
- Shows what updates are available
- Doesn't verify compatibility
- Faster, less network intensive
- Good for checking if updates exist

### Full Check (`check_updates.py --full-check`)
- Tests actual compatibility
- Finds the newest working combination
- Takes longer (tests multiple versions)
- **Recommended before major updates**
- Guarantees all components work together

## Best Practices

1. **Before major updates:** Use `--full-check` to ensure compatibility
2. **Regular maintenance:** Use standard check for individual component updates
3. **Always backup:** Run `./bin/backup.sh` before applying updates
4. **Use dry-run:** Test with `--dry-run` before actual updates
5. **Update config.yaml manually:** For MC/Fabric version changes
