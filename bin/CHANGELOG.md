# Update Scripts Changelog

## New Features

### Full Compatibility Check (`--full-check`)

A comprehensive update compatibility testing feature that intelligently finds the newest compatible version combination for Minecraft, Fabric loader, and all mods.

#### How It Works

1. **Sequential Testing**: Tests Minecraft versions from newest to oldest
2. **Fabric Compatibility**: For each MC version, checks if Fabric is available
3. **Mod Validation**: Tests ALL configured mods against each MC/Fabric combination
4. **Early Stopping**: Stops at first fully compatible configuration
5. **Failure Handling**: Missing Fabric or incompatible mods = skip to next version

#### Algorithm Flow

```
For each newer Minecraft version (newest first):
  └─ Get available Fabric versions for this MC version
     └─ If no Fabric available: STOP (can't update past this point)
        └─ For each Fabric version (newest first):
           └─ Check ALL mods for compatibility
              └─ If ALL compatible: SUCCESS! Save and exit
              └─ If ANY incompatible: Try next Fabric version
        └─ If no Fabric version worked: STOP (can't update to this MC version)
```

#### Output

Creates a `compatibility_report.json` file with:
- **compatible_update_found**: Boolean indicating success/failure
- **minecraft/fabric**: Current and target versions
- **mods**: All mod versions compatible with target configuration
- **tested_versions**: Statistics on how many versions were tested
- **download_url**: Direct download links for all components

### Changes to `check_updates.py`

#### New Command-Line Arguments

- `--full-check`: Enable comprehensive compatibility testing
- `--compat-output FILENAME`: Specify output file for compatibility report (default: `compatibility_report.json`)

#### New Methods

1. **`check_full_compatibility(mc_version, fabric_version)`**
   - Tests if all mods are compatible with a specific MC/Fabric combo
   - Returns: (all_compatible, mod_details, missing_mods)

2. **`find_compatible_updates()`**
   - Main orchestration function for full compatibility check
   - Iterates through versions following the algorithm above
   - Returns compatible configuration or None

3. **`save_compatibility_report(compat_data, output_file)`**
   - Saves compatibility check results to JSON
   - Handles both successful and failed searches
   - Includes metadata about the search process

#### Modified Behavior

- When `--full-check` is used, only the compatibility check runs
- Standard update checks are skipped in full-check mode
- Clear separation between standard and comprehensive checking modes

### Changes to `apply_updates.py`

#### Enhanced File Format Support

The script now automatically detects and handles both:
1. Standard update files (`updates.json`)
2. Compatibility reports (`compatibility_report.json`)

#### New Features

1. **Format Detection**
   - Automatically identifies file type via `update_type` field
   - Sets `is_compatibility_report` flag for conditional logic

2. **Enhanced Output Display**
   - Shows report type (Standard vs Full Compatibility Check)
   - Displays compatibility status
   - Shows number of versions tested (for compat reports)
   - Early exit if no compatible update found

3. **Dual Format Support in Update Methods**
   - `update_minecraft()`: Handles both formats
   - `update_fabric()`: Handles both formats
   - `update_mods()`: Adapts display based on format type

#### Modified Methods

All update methods now:
- Check `is_compatibility_report` flag
- Extract version info using appropriate field names
- Display appropriate messages for each format type

## File Format Changes

### New Format: Compatibility Report

```json
{
  "timestamp": "ISO-8601 datetime",
  "compatible_update_found": true/false,
  "update_type": "full_compatibility_check",
  "minecraft": {
    "current_version": "x.y.z",
    "target_version": "x.y.z"
  },
  "fabric": {
    "current_version": "x.y.z",
    "target_version": "x.y.z"
  },
  "mods": {
    "ModName": {
      "version": "x.y.z",
      "download_url": "https://...",
      "project_id": "modrinth_id"
    }
  },
  "tested_versions": {
    "mc_versions_tested": 2,
    "fabric_versions_tested": 1
  }
}
```

### Existing Format: Standard Updates

No changes to the existing `updates.json` format. Both formats are fully supported.

## Documentation Updates

### New Files

1. **`bin/README.md`**: Updated with `--full-check` documentation
2. **`bin/EXAMPLES.md`**: Comprehensive usage examples
3. **`bin/CHANGELOG.md`**: This file

### Updated Sections

- Added "Full Compatibility Check" workflow as recommended approach
- Documented output file formats for both types
- Added explanation of how `--full-check` algorithm works
- Updated command-line usage examples

## Usage Examples

### Before (Standard Check)
```bash
python bin/check_updates.py
# Shows available updates, but doesn't verify compatibility
```

### After (Comprehensive Check)
```bash
python bin/check_updates.py --full-check
# Tests versions and finds newest compatible combination
# Guarantees MC + Fabric + ALL mods will work together
```

## Benefits

1. **Safety**: Ensures all components are compatible before updating
2. **Automation**: No manual checking of mod compatibility
3. **Intelligence**: Finds newest working version automatically
4. **Transparency**: Shows which versions were tested
5. **Flexibility**: Can still use standard check for quick queries

## Backward Compatibility

✅ All existing functionality preserved
✅ Standard update checks work exactly as before
✅ `apply_updates.py` handles both old and new file formats
✅ No breaking changes to existing workflows

## Testing Strategy

The implementation includes:
- Proper error handling for API failures
- Network timeout handling
- JSON parsing error handling
- Missing data validation
- Empty result handling
- Console encoding fixes for Windows

## Future Enhancements

Potential improvements:
- Parallel version testing for speed
- Caching of API responses
- Configuration for acceptable version ranges
- Support for other mod loaders (Forge, Quilt)
- Automatic rollback on failed updates
