#!/usr/bin/env python3
"""
Update checker for Minecraft server, Fabric loader, and mods.
Checks for available updates based on configured versions and constraints.
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

# Fix Windows console encoding
if sys.platform == 'win32':
    import os
    os.system('chcp 65001 > nul 2>&1')
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class UpdateChecker:
    """Main update checker class"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.mc_version = self.config.get('minecraft', {}).get('version')
        self.fabric_version = self.config.get('fabric', {}).get('version')
        self.mods = self.config.get('mods', [])

    def _load_config(self, config_path: str) -> dict:
        """Load YAML configuration file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{config_path}' not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}")
            sys.exit(1)

    def _fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[dict]:
        """Fetch JSON data from URL"""
        try:
            req = urllib.request.Request(url)
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)

            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"  Error: HTTP {e.code} when fetching {url}")
            return None
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return None

    def check_minecraft_updates(self) -> Tuple[str, Optional[str], List[str]]:
        """
        Check for Minecraft server updates
        Returns: (current_version, latest_version, newer_versions)
        """
        print("\n" + "="*70)
        print("MINECRAFT SERVER UPDATE CHECK")
        print("="*70)
        print(f"Current version: {self.mc_version}")

        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        manifest = self._fetch_json(manifest_url)

        if not manifest:
            print("  ✗ Failed to fetch Minecraft version manifest")
            return self.mc_version, None, []

        latest_release = manifest.get('latest', {}).get('release')
        latest_snapshot = manifest.get('latest', {}).get('snapshot')

        print(f"Latest release:  {latest_release}")
        print(f"Latest snapshot: {latest_snapshot}")

        # Find newer versions
        versions = manifest.get('versions', [])
        current_found = False
        newer_releases = []

        for v in versions:
            if v['id'] == self.mc_version:
                current_found = True
                break
            if v['type'] == 'release':
                newer_releases.append(v['id'])

        if not current_found:
            print(f"  ⚠ Warning: Current version {self.mc_version} not found in manifest")

        if newer_releases:
            print(f"\n  📦 {len(newer_releases)} newer release(s) available:")
            for ver in newer_releases[:5]:  # Show max 5
                print(f"     • {ver}")
            if len(newer_releases) > 5:
                print(f"     ... and {len(newer_releases) - 5} more")
        else:
            print("\n  ✓ You are running the latest release version!")

        return self.mc_version, latest_release, newer_releases

    def check_fabric_updates(self, target_mc_version: Optional[str] = None) -> Tuple[str, Optional[str], List[str]]:
        """
        Check for Fabric loader updates
        Args:
            target_mc_version: MC version to check Fabric for (defaults to current)
        Returns: (current_version, latest_version, newer_versions)
        """
        mc_ver = target_mc_version or self.mc_version

        print("\n" + "="*70)
        print("FABRIC LOADER UPDATE CHECK")
        print("="*70)
        print(f"Current Fabric version: {self.fabric_version}")
        print(f"Target MC version:      {mc_ver}")

        # Get all Fabric loader versions for this MC version
        loader_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_ver}"
        loader_data = self._fetch_json(loader_url)

        if not loader_data:
            print(f"  ✗ Failed to fetch Fabric versions for Minecraft {mc_ver}")
            return self.fabric_version, None, []

        if not loader_data:
            print(f"  ✗ No Fabric versions available for Minecraft {mc_ver}")
            return self.fabric_version, None, []

        # Extract loader versions
        available_versions = []
        for item in loader_data:
            loader_info = item.get('loader', {})
            version = loader_info.get('version')
            if version:
                available_versions.append(version)

        if not available_versions:
            print("  ✗ No Fabric loader versions found")
            return self.fabric_version, None, []

        latest_version = available_versions[0]  # First is latest
        print(f"Latest Fabric version:  {latest_version}")

        # Find newer versions
        newer_versions = []
        current_found = False

        for ver in available_versions:
            if ver == self.fabric_version:
                current_found = True
                break
            newer_versions.append(ver)

        if not current_found:
            print(f"  ⚠ Warning: Current version {self.fabric_version} not found for MC {mc_ver}")

        if newer_versions:
            print(f"\n  📦 {len(newer_versions)} newer version(s) available:")
            for ver in newer_versions[:5]:
                print(f"     • {ver}")
            if len(newer_versions) > 5:
                print(f"     ... and {len(newer_versions) - 5} more")
        else:
            print(f"\n  ✓ You are running the latest Fabric version for MC {mc_ver}!")

        return self.fabric_version, latest_version, newer_versions

    def _search_modrinth_project(self, mod_name: str) -> Optional[str]:
        """Search for a mod on Modrinth and return project ID"""
        search_url = f"https://api.modrinth.com/v2/search?query={mod_name}&limit=5"
        headers = {"User-Agent": "minecraft-server-update-checker/1.0"}

        results = self._fetch_json(search_url, headers)
        if not results or 'hits' not in results:
            return None

        hits = results['hits']
        if not hits:
            return None

        # Try to find exact match first
        for hit in hits:
            if hit.get('slug', '').lower() == mod_name.lower():
                return hit.get('project_id')
            if hit.get('title', '').lower() == mod_name.lower():
                return hit.get('project_id')

        # Return first result as fallback
        return hits[0].get('project_id')

    def _get_mod_versions(self, project_id: str, mc_version: str, loader: str = "fabric") -> List[dict]:
        """Get available versions for a mod from Modrinth"""
        import urllib.parse

        versions_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
        # Modrinth expects JSON arrays - need to use quote_via for proper encoding
        game_versions_param = urllib.parse.quote(f'["{mc_version}"]')
        loaders_param = urllib.parse.quote(f'["{loader}"]')
        url_with_params = f"{versions_url}?game_versions={game_versions_param}&loaders={loaders_param}"

        headers = {"User-Agent": "minecraft-server-update-checker/1.0"}

        versions = self._fetch_json(url_with_params, headers)
        return versions if versions else []

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings
        Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal
        """
        try:
            # Clean version strings
            v1_clean = v1.split('+')[0].split('-')[0]
            v2_clean = v2.split('+')[0].split('-')[0]

            parts1 = [int(x) if x.isdigit() else x for x in v1_clean.replace('v', '').split('.')]
            parts2 = [int(x) if x.isdigit() else x for x in v2_clean.replace('v', '').split('.')]

            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0

                if isinstance(p1, int) and isinstance(p2, int):
                    if p1 > p2:
                        return 1
                    elif p1 < p2:
                        return -1
                else:
                    if str(p1) > str(p2):
                        return 1
                    elif str(p1) < str(p2):
                        return -1

            return 0
        except:
            # Fallback to string comparison
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
            return 0

    def check_full_compatibility(self, mc_version: str, fabric_version: str) -> Tuple[bool, Dict[str, dict], List[str]]:
        """
        Check if all mods are compatible with a specific MC and Fabric version
        Args:
            mc_version: Minecraft version to check
            fabric_version: Fabric version to check
        Returns: (all_compatible, mod_details, missing_mods)
        """
        mod_details = {}
        missing_mods = []

        for mod in self.mods:
            mod_name = mod.get('name')
            if not mod_name:
                continue

            # Search for mod on Modrinth
            project_id = self._search_modrinth_project(mod_name)
            if not project_id:
                missing_mods.append(mod_name)
                continue

            # Get available versions for this MC version
            versions = self._get_mod_versions(project_id, mc_version)
            if not versions:
                missing_mods.append(mod_name)
                continue

            # Take the first (latest) version
            latest = versions[0]
            latest_version = latest.get('version_number')

            if not latest_version:
                missing_mods.append(mod_name)
                continue

            mod_details[mod_name] = {
                'version': latest_version,
                'url': latest.get('files', [{}])[0].get('url', 'N/A'),
                'project_id': project_id
            }

        all_compatible = len(missing_mods) == 0
        return all_compatible, mod_details, missing_mods

    def find_compatible_updates(self) -> Optional[Dict]:
        """
        Find the newest compatible MC/Fabric/Mods combination
        Tests each newer MC version with available Fabric versions
        Returns: Dict with compatible update info or None if no compatible update found
        """
        print("\n" + "="*70)
        print("COMPREHENSIVE UPDATE COMPATIBILITY CHECK")
        print("="*70)
        print(f"Current configuration:")
        print(f"  Minecraft: {self.mc_version}")
        print(f"  Fabric:    {self.fabric_version}")
        print(f"  Mods:      {len(self.mods)}")

        # Get newer Minecraft versions
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        manifest = self._fetch_json(manifest_url)

        if not manifest:
            print("\n  ✗ Failed to fetch Minecraft version manifest")
            return None

        versions = manifest.get('versions', [])
        current_found = False
        newer_mc_versions = []

        # Find all newer release versions
        for v in versions:
            if v['id'] == self.mc_version:
                current_found = True
                break
            if v['type'] == 'release':
                newer_mc_versions.append(v['id'])

        if not newer_mc_versions:
            print("\n  ✓ Already running the latest Minecraft version")
            return None

        print(f"\nFound {len(newer_mc_versions)} newer MC version(s) to test")
        print("Testing compatibility (MC version → Fabric version → Mods)...\n")

        # Test each MC version
        for mc_ver in newer_mc_versions:
            print(f"{'─'*70}")
            print(f"Testing Minecraft {mc_ver}...")

            # Get available Fabric versions for this MC version
            loader_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_ver}"
            loader_data = self._fetch_json(loader_url)

            if not loader_data:
                print(f"  ✗ No Fabric support available for MC {mc_ver}")
                print(f"  ⚠ Cannot update to MC {mc_ver} - stopping here\n")
                break

            # Extract Fabric versions
            fabric_versions = []
            for item in loader_data:
                loader_info = item.get('loader', {})
                version = loader_info.get('version')
                if version:
                    fabric_versions.append(version)

            if not fabric_versions:
                print(f"  ✗ No Fabric loader versions found for MC {mc_ver}")
                print(f"  ⚠ Cannot update to MC {mc_ver} - stopping here\n")
                break

            print(f"  Found {len(fabric_versions)} Fabric version(s)")

            # Test each Fabric version for this MC version
            for fabric_ver in fabric_versions:
                print(f"    Testing Fabric {fabric_ver}...")

                compatible, mod_details, missing_mods = self.check_full_compatibility(mc_ver, fabric_ver)

                if compatible:
                    print(f"      ✓ All {len(self.mods)} mod(s) compatible!")
                    print(f"\n{'='*70}")
                    print(f"✓ COMPATIBLE UPDATE FOUND!")
                    print(f"{'='*70}")
                    print(f"  Minecraft: {self.mc_version} → {mc_ver}")
                    print(f"  Fabric:    {self.fabric_version} → {fabric_ver}")
                    print(f"  Mods:      {len(mod_details)} updated")

                    # Return the compatible configuration
                    return {
                        'minecraft': {
                            'current_version': self.mc_version,
                            'new_version': mc_ver
                        },
                        'fabric': {
                            'current_version': self.fabric_version,
                            'new_version': fabric_ver
                        },
                        'mods': mod_details,
                        'tested_versions': {
                            'mc_versions_tested': newer_mc_versions.index(mc_ver) + 1,
                            'fabric_versions_tested': fabric_versions.index(fabric_ver) + 1
                        }
                    }
                else:
                    print(f"      ✗ {len(missing_mods)} mod(s) incompatible: {', '.join(missing_mods[:5])}")
                    if len(missing_mods) > 5:
                        print(f"        ... and {len(missing_mods) - 5} more")

            # If we get here, no compatible Fabric version was found for this MC version
            print(f"  ⚠ No compatible Fabric version found for MC {mc_ver}")
            print(f"  ⚠ Cannot update to MC {mc_ver} - stopping here\n")
            break

        print(f"{'='*70}")
        print("✗ NO COMPATIBLE UPDATE FOUND")
        print(f"{'='*70}")
        print("Unable to find a newer version where all components are compatible")

        return None

    def check_mod_updates(self, target_mc_version: Optional[str] = None) -> Dict[str, dict]:
        """
        Check for mod updates
        Args:
            target_mc_version: MC version to check mods for (defaults to current)
        Returns: Dict of mod updates
        """
        mc_ver = target_mc_version or self.mc_version

        print("\n" + "="*70)
        print("MOD UPDATE CHECK")
        print("="*70)
        print(f"Target MC version: {mc_ver}")
        print(f"Checking {len(self.mods)} mods...")

        updates = {}
        up_to_date = 0
        has_updates = 0
        errors = 0

        for mod in self.mods:
            mod_name = mod.get('name')
            current_version = mod.get('version')

            if not mod_name or not current_version:
                continue

            print(f"\n  [{mod_name}]")
            print(f"    Current: {current_version}")

            # Search for mod on Modrinth
            project_id = self._search_modrinth_project(mod_name)
            if not project_id:
                print(f"    ⚠ Not found on Modrinth")
                errors += 1
                continue

            # Get available versions
            versions = self._get_mod_versions(project_id, mc_ver)
            if not versions:
                print(f"    ⚠ No versions available for MC {mc_ver}")
                errors += 1
                continue

            # Find latest version
            latest = versions[0]  # Modrinth returns sorted by newest
            latest_version = latest.get('version_number')

            if not latest_version:
                print(f"    ⚠ Could not determine latest version")
                errors += 1
                continue

            print(f"    Latest:  {latest_version}")

            # Compare versions
            if latest_version == current_version:
                print(f"    ✓ Up to date")
                up_to_date += 1
            else:
                comparison = self._compare_versions(latest_version, current_version)
                if comparison > 0:
                    print(f"    📦 Update available!")
                    has_updates += 1
                    updates[mod_name] = {
                        'current': current_version,
                        'latest': latest_version,
                        'url': latest.get('files', [{}])[0].get('url', 'N/A')
                    }
                elif comparison < 0:
                    print(f"    ⚠ Current version is newer than latest on Modrinth")
                    up_to_date += 1
                else:
                    print(f"    ✓ Up to date (versions match)")
                    up_to_date += 1

        print(f"\n  {'─'*66}")
        print(f"  Summary: {up_to_date} up-to-date | {has_updates} updates available | {errors} errors")

        return updates


def print_summary(mc_result: Tuple, fabric_result: Tuple, mod_updates: Dict):
    """Print final summary of all updates"""
    print("\n" + "="*70)
    print("UPDATE SUMMARY")
    print("="*70)

    mc_current, mc_latest, mc_newer = mc_result
    fabric_current, fabric_latest, fabric_newer = fabric_result

    print("\nMinecraft Server:")
    if mc_newer:
        print(f"  ⚠ {len(mc_newer)} newer version(s) available (latest: {mc_latest})")
    else:
        print(f"  ✓ Up to date ({mc_current})")

    print("\nFabric Loader:")
    if fabric_newer:
        print(f"  ⚠ {len(fabric_newer)} newer version(s) available (latest: {fabric_latest})")
    else:
        print(f"  ✓ Up to date ({fabric_current})")

    print("\nMods:")
    if mod_updates:
        print(f"  ⚠ {len(mod_updates)} mod(s) with updates available")
        for mod_name, info in list(mod_updates.items())[:10]:
            print(f"     • {mod_name}: {info['current']} → {info['latest']}")
        if len(mod_updates) > 10:
            print(f"     ... and {len(mod_updates) - 10} more")
    else:
        print(f"  ✓ All mods up to date")

    print("\n" + "="*70)


def save_updates(mc_result: Tuple, fabric_result: Tuple, mod_updates: Dict, output_file: str):
    """
    Save update information to a JSON file
    Args:
        mc_result: Tuple of (current_version, latest_version, newer_versions)
        fabric_result: Tuple of (current_version, latest_version, newer_versions)
        mod_updates: Dict of mod updates
        output_file: Path to output JSON file
    """
    mc_current, mc_latest, mc_newer = mc_result
    fabric_current, fabric_latest, fabric_newer = fabric_result

    update_data = {
        "timestamp": json.dumps(None),  # Will be replaced with actual timestamp
        "minecraft": {
            "current_version": mc_current,
            "latest_version": mc_latest,
            "has_update": len(mc_newer) > 0,
            "newer_versions": mc_newer
        },
        "fabric": {
            "current_version": fabric_current,
            "latest_version": fabric_latest,
            "has_update": len(fabric_newer) > 0,
            "newer_versions": fabric_newer
        },
        "mods": {}
    }

    # Add mod updates
    for mod_name, info in mod_updates.items():
        update_data["mods"][mod_name] = {
            "current_version": info['current'],
            "latest_version": info['latest'],
            "download_url": info['url']
        }

    # Add timestamp
    import datetime
    update_data["timestamp"] = datetime.datetime.now().isoformat()

    # Save to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(update_data, f, indent=2, ensure_ascii=False)
        print(f"Update information saved to: {output_file}")

        # Print summary of what was saved
        total_updates = (
            (1 if update_data["minecraft"]["has_update"] else 0) +
            (1 if update_data["fabric"]["has_update"] else 0) +
            len(update_data["mods"])
        )
        print(f"Total components with updates: {total_updates}")

    except Exception as e:
        print(f"Error saving update information: {e}")
        sys.exit(1)


def save_compatibility_report(compat_data: Optional[Dict], output_file: str):
    """
    Save compatibility check results to a JSON file
    Args:
        compat_data: Dict with compatibility information or None if no compatible update
        output_file: Path to output JSON file
    """
    import datetime

    if compat_data is None:
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "compatible_update_found": False,
            "message": "No compatible update configuration found"
        }
    else:
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "compatible_update_found": True,
            "update_type": "full_compatibility_check",
            "minecraft": {
                "current_version": compat_data['minecraft']['current_version'],
                "target_version": compat_data['minecraft']['new_version']
            },
            "fabric": {
                "current_version": compat_data['fabric']['current_version'],
                "target_version": compat_data['fabric']['new_version']
            },
            "mods": {},
            "tested_versions": compat_data['tested_versions']
        }

        # Add mod details
        for mod_name, mod_info in compat_data['mods'].items():
            report["mods"][mod_name] = {
                "version": mod_info['version'],
                "download_url": mod_info['url'],
                "project_id": mod_info['project_id']
            }

    # Save to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        if compat_data:
            print(f"✓ Compatibility report saved to: {output_file}")
            print(f"  This file can be used with apply_updates.py to perform the update")
        else:
            print(f"✗ Report saved to: {output_file}")
            print(f"  No compatible update is available at this time")
        print(f"{'='*70}")

    except Exception as e:
        print(f"Error saving compatibility report: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Check for updates to Minecraft server, Fabric loader, and mods'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Check all components (default)'
    )
    parser.add_argument(
        '--mc',
        action='store_true',
        help='Check only Minecraft server updates'
    )
    parser.add_argument(
        '--fabric',
        action='store_true',
        help='Check only Fabric loader updates'
    )
    parser.add_argument(
        '--mods',
        action='store_true',
        help='Check only mod updates'
    )
    parser.add_argument(
        '--mc-version',
        type=str,
        help='Check Fabric/mod updates for a specific MC version (e.g., 1.21.2)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='updates.json',
        help='Output file for update information (default: updates.json)'
    )
    parser.add_argument(
        '--full-check',
        action='store_true',
        help='Perform comprehensive compatibility check across MC/Fabric/Mods versions'
    )
    parser.add_argument(
        '--compat-output',
        type=str,
        default='compatibility_report.json',
        help='Output file for compatibility report (default: compatibility_report.json)'
    )

    args = parser.parse_args()

    checker = UpdateChecker()

    # Handle full compatibility check
    if args.full_check:
        compat_data = checker.find_compatible_updates()
        save_compatibility_report(compat_data, args.compat_output)
        print()
        return

    # If no specific flag is set, check all
    check_all = args.all or not (args.mc or args.fabric or args.mods)

    mc_result = (checker.mc_version, None, [])
    fabric_result = (checker.fabric_version, None, [])
    mod_updates = {}

    target_mc_version = args.mc_version

    # Check Minecraft updates
    if check_all or args.mc:
        mc_result = checker.check_minecraft_updates()

    # Check Fabric updates
    if check_all or args.fabric:
        fabric_result = checker.check_fabric_updates(target_mc_version)

        # If checking for new MC version, also check mod compatibility
        if target_mc_version and target_mc_version != checker.mc_version:
            print(f"\n  ℹ Checking mod compatibility with MC {target_mc_version}...")

    # Check mod updates
    if check_all or args.mods or (args.fabric and target_mc_version):
        mod_updates = checker.check_mod_updates(target_mc_version)

    # Print summary
    if check_all:
        print_summary(mc_result, fabric_result, mod_updates)

    # Save updates to file
    save_updates(mc_result, fabric_result, mod_updates, args.output)

    print()


if __name__ == '__main__':
    main()
