#!/usr/bin/env python3
"""
Config validation script for config.yaml
Validates format and checks if specified versions exist on their sources.
Auto-updates config with latest compatible versions when version not found.
"""
import os
import sys
import json
import yaml
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Add bin directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_loader import load_dotenv, get_env

# Load .env file if it exists
load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class ConfigValidator:
    """Validates config.yaml structure and version availability"""

    def __init__(self, config_file: str = "config.yaml",
                 mappings_file: str = "source_mappings.yaml",
                 auto_fix: bool = False):
        self.config_file = config_file
        self.mappings_file = mappings_file
        self.auto_fix = auto_fix
        self.errors = []
        self.warnings = []
        self.config = None
        self.mappings = None
        self.minecraft_version = None
        self.updates_made = []
        self.config_modified = False
        self.curseforge_api_key = os.environ.get('CURSEFORGE_API_KEY')

    def _load_yaml(self, file_path: str) -> Optional[dict]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.errors.append(f"File not found: {file_path}")
            return None
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error in {file_path}: {e}")
            return None

    def _save_yaml(self):
        """Save modified config back to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"\n✓ Config file updated: {self.config_file}")
            return True
        except Exception as e:
            print(f"\n✗ Failed to save config file: {e}")
            return False

    def _fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None,
                    debug: bool = False) -> Optional[dict]:
        """Fetch JSON data from URL"""
        try:
            req = urllib.request.Request(url)
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)

            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
                if debug:
                    print(f"  DEBUG: HTTP {response.status} - Response length: {len(data)} bytes")
                return json.loads(data)
        except urllib.error.HTTPError as e:
            if debug:
                print(f"  DEBUG: HTTP Error {e.code}: {e.reason}")
                try:
                    error_body = e.read().decode('utf-8')
                    print(f"  DEBUG: Error response: {error_body[:500]}")
                except:
                    pass
            if e.code == 404:
                return None
            return None
        except Exception as e:
            if debug:
                print(f"  DEBUG: Exception: {type(e).__name__}: {e}")
            return None

    def validate_structure(self) -> bool:
        """Validate basic YAML structure"""
        print("\n" + "="*70)
        print("VALIDATING CONFIG STRUCTURE")
        print("="*70)

        # Load config file
        self.config = self._load_yaml(self.config_file)
        if not self.config:
            return False

        # Load mappings file
        self.mappings = self._load_yaml(self.mappings_file)
        if not self.mappings:
            return False

        # Validate minecraft section
        if 'minecraft' not in self.config:
            self.errors.append("Missing required section: 'minecraft'")
        else:
            minecraft = self.config['minecraft']
            if not isinstance(minecraft, dict):
                self.errors.append("'minecraft' must be a dictionary")
            else:
                if 'version' not in minecraft:
                    self.errors.append("'minecraft' section missing required field: 'version'")
                elif not isinstance(minecraft['version'], str):
                    self.errors.append("'minecraft.version' must be a string")
                else:
                    self.minecraft_version = minecraft['version']
                    print(f"✓ Minecraft version: {self.minecraft_version}")

                if 'source' not in minecraft:
                    self.warnings.append("'minecraft' section missing 'source' field (will default to 'mojang')")
                elif minecraft['source'] not in self.mappings.get('sources', {}):
                    self.errors.append(f"Invalid source '{minecraft['source']}' for minecraft")

        # Validate fabric section
        if 'fabric' not in self.config:
            self.errors.append("Missing required section: 'fabric'")
        else:
            fabric = self.config['fabric']
            if not isinstance(fabric, dict):
                self.errors.append("'fabric' must be a dictionary")
            else:
                if 'version' not in fabric:
                    self.errors.append("'fabric' section missing required field: 'version'")
                elif not isinstance(fabric['version'], str):
                    self.errors.append("'fabric.version' must be a string")
                else:
                    print(f"✓ Fabric version: {fabric['version']}")

                if 'source' not in fabric:
                    self.warnings.append("'fabric' section missing 'source' field (will default to 'fabric')")
                elif fabric['source'] not in self.mappings.get('sources', {}):
                    self.errors.append(f"Invalid source '{fabric['source']}' for fabric")

        # Validate mods section
        if 'mods' not in self.config:
            self.warnings.append("No 'mods' section found")
        else:
            mods = self.config['mods']
            if not isinstance(mods, list):
                self.errors.append("'mods' must be a list")
            else:
                print(f"✓ Found {len(mods)} mods to validate")
                for i, mod in enumerate(mods):
                    if not isinstance(mod, dict):
                        self.errors.append(f"Mod at index {i} is not a dictionary")
                        continue

                    # Check required fields
                    if 'name' not in mod:
                        self.errors.append(f"Mod at index {i} missing required field: 'name'")
                    elif not isinstance(mod['name'], str):
                        self.errors.append(f"Mod at index {i}: 'name' must be a string")

                    # Version is now optional - will be resolved automatically
                    if 'version' in mod and not isinstance(mod['version'], str):
                        self.errors.append(f"Mod '{mod.get('name', f'at index {i}')}': 'version' must be a string")

                    if 'source' not in mod:
                        self.warnings.append(f"Mod '{mod.get('name', f'at index {i}')}' missing 'source' field (will default to 'modrinth')")
                    elif mod['source'] not in self.mappings.get('sources', {}):
                        self.errors.append(f"Mod '{mod.get('name', f'at index {i}')}' has invalid source: '{mod['source']}'")

                    # Validate custom source has download_url
                    if mod.get('source') == 'custom' and 'download_url' not in mod:
                        self.errors.append(f"Mod '{mod.get('name', f'at index {i}')}' with source 'custom' missing required field: 'download_url'")

                    # Validate slug if present
                    if 'slug' in mod and not isinstance(mod['slug'], str):
                        self.errors.append(f"Mod '{mod.get('name', f'at index {i}')}': 'slug' must be a string")

        if self.errors:
            print("\n✗ STRUCTURE VALIDATION FAILED")
            for error in self.errors:
                print(f"  ERROR: {error}")
        else:
            print("\n✓ STRUCTURE VALIDATION PASSED")

        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        return len(self.errors) == 0

    def validate_minecraft_version(self) -> bool:
        """Validate that Minecraft version exists"""
        if not self.minecraft_version:
            return False

        print(f"\nValidating Minecraft version {self.minecraft_version}...")

        source_config = self.mappings['sources']['mojang']
        manifest_url = source_config['manifest_url']

        manifest = self._fetch_json(manifest_url)
        if not manifest:
            self.errors.append("Failed to fetch Minecraft version manifest")
            return False

        # Check if version exists
        for v in manifest.get('versions', []):
            if v['id'] == self.minecraft_version:
                print(f"  ✓ Minecraft {self.minecraft_version} found")
                return True

        self.errors.append(f"Minecraft version '{self.minecraft_version}' not found on Mojang servers")
        print(f"  ✗ Minecraft {self.minecraft_version} NOT FOUND")
        return False

    def validate_fabric_version(self) -> bool:
        """Validate that Fabric version exists for the Minecraft version"""
        if not self.config or 'fabric' not in self.config:
            return False

        fabric = self.config['fabric']
        fabric_version = fabric.get('version')
        if not fabric_version:
            return False

        print(f"\nValidating Fabric version {fabric_version} for MC {self.minecraft_version}...")

        # Try to access the Fabric loader URL
        source_config = self.mappings['sources']['fabric']
        url = source_config['manifest_url'].format(
            minecraft_version=self.minecraft_version,
            version=fabric_version
        )

        # Make a HEAD request to check if it exists
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    print(f"  ✓ Fabric {fabric_version} found for MC {self.minecraft_version}")
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.errors.append(f"Fabric version '{fabric_version}' not found for Minecraft {self.minecraft_version}")
                print(f"  ✗ Fabric {fabric_version} NOT FOUND")
                return False
        except Exception as e:
            self.warnings.append(f"Could not verify Fabric version: {e}")
            print(f"  ⚠ Could not verify Fabric version: {e}")
            return True  # Don't fail validation if we can't check

        return False

    def _find_latest_modrinth_version(self, mod_name: str, project_id: str) -> Optional[Tuple[str, str]]:
        """
        Find the latest compatible version for a Modrinth mod
        Returns: (version_number, environment) or None
        """
        source_config = self.mappings['sources']['modrinth']
        manifest_url = source_config['manifest_url'].format(project_id=project_id)
        headers = {'User-Agent': source_config.get('user_agent', 'minecraft-server-manager/1.0')}

        versions = self._fetch_json(manifest_url, headers)
        if not versions:
            return None

        # Find the latest version that matches our criteria
        for ver_info in versions:
            loaders = ver_info.get('loaders', []) or []
            game_versions = ver_info.get('game_versions', []) or []

            if 'fabric' in loaders and self.minecraft_version in game_versions:
                version_number = ver_info.get('version_number')
                # Get project info to determine environment (client/server/both)
                project_info = self._fetch_json(
                    f"{source_config['api_base']}/project/{project_id}",
                    headers
                )
                environment = 'both'  # default
                if project_info:
                    client_side = project_info.get('client_side', 'required')
                    server_side = project_info.get('server_side', 'required')

                    if client_side in ['required', 'optional'] and server_side in ['required', 'optional']:
                        environment = 'both'
                    elif client_side in ['required', 'optional'] and server_side == 'unsupported':
                        environment = 'client'
                    elif server_side in ['required', 'optional'] and client_side == 'unsupported':
                        environment = 'server'

                return (version_number, environment)

        return None

    def _auto_resolve_modrinth_version(self, mod: dict, mod_index: int, mod_name: str,
                                       slug: Optional[str] = None) -> bool:
        """Auto-resolve and set latest Modrinth version when version field is missing"""
        source_config = self.mappings['sources']['modrinth']

        # Determine project ID/slug
        project_mappings = source_config.get('project_mappings', {}) or {}
        project_id = project_mappings.get(mod_name, slug or mod_name)

        # Try to find latest version
        result = self._find_latest_modrinth_version(mod_name, project_id)
        if result:
            latest_version, environment = result
            env_display = f" [{environment}]" if environment != 'both' else ""
            print(f"  [{mod_name}] → Resolved to latest version: {latest_version}{env_display}")

            # Update config
            self.config['mods'][mod_index]['version'] = latest_version
            self.config['mods'][mod_index]['environment'] = environment
            self.updates_made.append(f"{mod_name}: resolved to latest version {latest_version} (environment={environment})")
            self.config_modified = True
            return True
        else:
            self.errors.append(f"Mod '{mod_name}' (project: {project_id}) not found or no compatible version available on Modrinth")
            print(f"  [{mod_name}] ✗ Could not find compatible version")
            return False

    def _auto_resolve_curseforge_version(self, mod: dict, mod_index: int, mod_name: str,
                                         project_id: int) -> bool:
        """Auto-resolve and set latest CurseForge version when version field is missing"""
        if not self.curseforge_api_key:
            self.errors.append(f"Mod '{mod_name}': CurseForge API key not set. Set CURSEFORGE_API_KEY environment variable.")
            print(f"  [{mod_name}] ✗ CurseForge API key not set")
            return False

        # Try to find latest version
        result = self._find_latest_curseforge_version(mod_name, project_id)
        if result:
            latest_version, environment, file_id = result
            env_display = f" [{environment}]" if environment != 'both' else ""
            print(f"  [{mod_name}] → Resolved to latest version: {latest_version}{env_display}")

            # Update config
            self.config['mods'][mod_index]['version'] = latest_version
            self.config['mods'][mod_index]['file_id'] = file_id
            self.config['mods'][mod_index]['environment'] = environment
            self.updates_made.append(f"{mod_name}: resolved to latest version {latest_version} (file_id={file_id}, environment={environment})")
            self.config_modified = True
            return True
        else:
            self.errors.append(f"Mod '{mod_name}' (project_id: {project_id}) not found or no compatible version available on CurseForge")
            print(f"  [{mod_name}] ✗ Could not find compatible version")
            return False

    def validate_mod_version(self, mod: dict, mod_index: int) -> bool:
        """Validate that a specific mod version exists"""
        mod_name = mod.get('name', 'unknown')
        version = mod.get('version')
        source = mod.get('source', 'modrinth')
        slug = mod.get('slug')

        if source == 'custom':
            # For custom sources, just check if download_url is present
            if 'download_url' in mod:
                print(f"  [{mod_name}] ✓ Custom URL provided")
                return True
            else:
                print(f"  [{mod_name}] ✗ Missing download_url")
                self.errors.append(f"Mod '{mod_name}' with source 'custom' missing download_url")
                return False

        # If version is missing, try to auto-resolve latest version
        if not version:
            print(f"  [{mod_name}] ⚠ No version specified, finding latest...")
            if source == 'modrinth':
                return self._auto_resolve_modrinth_version(mod, mod_index, mod_name, slug)
            elif source == 'curseforge':
                project_id = mod.get('project_id')
                if not project_id:
                    self.errors.append(f"Mod '{mod_name}' with source 'curseforge' missing required field: 'project_id'")
                    print(f"  [{mod_name}] ✗ Missing project_id")
                    return False
                return self._auto_resolve_curseforge_version(mod, mod_index, mod_name, project_id)
            else:
                self.errors.append(f"Mod '{mod_name}': version required for source '{source}'")
                print(f"  [{mod_name}] ✗ Version required for source '{source}'")
                return False

        if source == 'modrinth':
            return self._validate_modrinth_mod(mod, mod_index, mod_name, version, slug)

        if source == 'curseforge':
            project_id = mod.get('project_id')
            if not project_id:
                self.errors.append(f"Mod '{mod_name}' with source 'curseforge' missing required field: 'project_id'")
                print(f"  [{mod_name}] ✗ Missing project_id")
                return False
            return self._validate_curseforge_mod(mod, mod_index, mod_name, version, project_id)

        # Other sources not implemented yet
        self.warnings.append(f"Validation not implemented for source '{source}' (mod: {mod_name})")
        print(f"  [{mod_name}] ⚠ Validation not implemented for source '{source}'")
        return True  # Don't fail validation

    def _validate_modrinth_mod(self, mod: dict, mod_index: int, mod_name: str,
                               version: str, slug: Optional[str] = None) -> bool:
        """Validate a Modrinth mod version"""
        source_config = self.mappings['sources']['modrinth']

        # Determine project ID/slug
        project_mappings = source_config.get('project_mappings', {}) or {}
        project_id = project_mappings.get(mod_name, slug or mod_name)

        # Fetch version list
        manifest_url = source_config['manifest_url'].format(project_id=project_id)
        headers = {'User-Agent': source_config.get('user_agent', 'minecraft-server-manager/1.0')}

        versions = self._fetch_json(manifest_url, headers)
        if not versions:
            self.errors.append(f"Mod '{mod_name}' (project: {project_id}) not found on Modrinth")
            print(f"  [{mod_name}] ✗ PROJECT NOT FOUND on Modrinth")
            return False

        # Get project info to determine environment
        project_info = self._fetch_json(
            f"{source_config['api_base']}/project/{project_id}",
            headers
        )
        environment = 'both'  # default
        if project_info:
            client_side = project_info.get('client_side', 'required')
            server_side = project_info.get('server_side', 'required')

            if client_side in ['required', 'optional'] and server_side in ['required', 'optional']:
                environment = 'both'
            elif client_side in ['required', 'optional'] and server_side == 'unsupported':
                environment = 'client'
            elif server_side in ['required', 'optional'] and client_side == 'unsupported':
                environment = 'server'

        # Find matching version
        found_version = False
        correct_loader = False
        correct_mc_version = False

        for ver_info in versions:
            if ver_info.get('version_number') == version:
                found_version = True
                loaders = ver_info.get('loaders', []) or []
                game_versions = ver_info.get('game_versions', []) or []

                if 'fabric' in loaders:
                    correct_loader = True

                if self.minecraft_version in game_versions:
                    correct_mc_version = True

                if correct_loader and correct_mc_version:
                    # Update environment if missing
                    if 'environment' not in mod:
                        self.config['mods'][mod_index]['environment'] = environment
                        self.updates_made.append(f"{mod_name}: added environment={environment}")
                        self.config_modified = True

                    env_display = f" [{environment}]" if environment != 'both' else ""
                    print(f"  [{mod_name}] ✓ Version {version} found{env_display}")
                    return True

        # Handle different error cases
        if not found_version:
            print(f"  [{mod_name}] ✗ VERSION NOT FOUND: {version}")

            if self.auto_fix:
                # Try to find latest compatible version
                result = self._find_latest_modrinth_version(mod_name, project_id)
                if result:
                    latest_version, latest_env = result
                    env_display = f" [{latest_env}]" if latest_env != 'both' else ""
                    print(f"  [{mod_name}] → Auto-fixing to latest version: {latest_version}{env_display}")
                    self.config['mods'][mod_index]['version'] = latest_version
                    self.config['mods'][mod_index]['environment'] = latest_env
                    self.updates_made.append(f"{mod_name}: {version} → {latest_version} (environment={latest_env})")
                    self.config_modified = True
                    return True
                else:
                    self.errors.append(f"Mod '{mod_name}': version '{version}' not found and no compatible version available")
                    print(f"  [{mod_name}] ✗ No compatible version found for MC {self.minecraft_version} + Fabric")
                    return False
            else:
                self.errors.append(f"Mod '{mod_name}': version '{version}' not found on Modrinth")
                return False

        elif not correct_loader:
            print(f"  [{mod_name}] ✗ VERSION FOUND but not for Fabric loader")

            if self.auto_fix:
                result = self._find_latest_modrinth_version(mod_name, project_id)
                if result:
                    latest_version, latest_env = result
                    env_display = f" [{latest_env}]" if latest_env != 'both' else ""
                    print(f"  [{mod_name}] → Auto-fixing to latest Fabric version: {latest_version}{env_display}")
                    self.config['mods'][mod_index]['version'] = latest_version
                    self.config['mods'][mod_index]['environment'] = latest_env
                    self.updates_made.append(f"{mod_name}: {version} → {latest_version} (Fabric, environment={latest_env})")
                    self.config_modified = True
                    return True
                else:
                    self.errors.append(f"Mod '{mod_name}': version '{version}' not available for Fabric loader")
                    return False
            else:
                self.errors.append(f"Mod '{mod_name}' version '{version}' not available for Fabric loader")
                return False

        elif not correct_mc_version:
            print(f"  [{mod_name}] ✗ VERSION FOUND but not for MC {self.minecraft_version}")

            if self.auto_fix:
                result = self._find_latest_modrinth_version(mod_name, project_id)
                if result:
                    latest_version, latest_env = result
                    env_display = f" [{latest_env}]" if latest_env != 'both' else ""
                    print(f"  [{mod_name}] → Auto-fixing to version for MC {self.minecraft_version}: {latest_version}{env_display}")
                    self.config['mods'][mod_index]['version'] = latest_version
                    self.config['mods'][mod_index]['environment'] = latest_env
                    self.updates_made.append(f"{mod_name}: {version} → {latest_version} (MC {self.minecraft_version}, environment={latest_env})")
                    self.config_modified = True
                    return True
                else:
                    self.errors.append(f"Mod '{mod_name}': version '{version}' not available for Minecraft {self.minecraft_version}")
                    return False
            else:
                self.errors.append(f"Mod '{mod_name}' version '{version}' not available for Minecraft {self.minecraft_version}")
                return False

        return False

    def _find_latest_curseforge_version(self, mod_name: str, project_id: int) -> Optional[Tuple[str, str, int]]:
        """
        Find the latest compatible version for a CurseForge mod
        Returns: (version_display_name, environment, file_id) or None
        """
        if not self.curseforge_api_key:
            return None

        source_config = self.mappings['sources']['curseforge']
        files_url = source_config['files_url'].format(project_id=project_id)
        headers = {
            'Accept': 'application/json',
            'x-api-key': self.curseforge_api_key
        }

        # Get mod info for environment
        mod_info_url = source_config['mod_info_url'].format(project_id=project_id)
        print(f"  DEBUG: Fetching mod info from {mod_info_url}")
        mod_info = self._fetch_json(mod_info_url, headers, debug=True)

        environment = 'both'  # default
        if mod_info and 'data' in mod_info:
            mod_data = mod_info['data']
            # CurseForge doesn't have explicit client/server side info like Modrinth
            # We'll default to 'both' for now
            environment = 'both'

        # Get files list with pagination parameters
        files_url_with_params = f"{files_url}?gameVersion={self.minecraft_version}"
        print(f"  DEBUG: Fetching files from {files_url_with_params}")
        files_response = self._fetch_json(files_url_with_params, headers, debug=True)
        if not files_response or 'data' not in files_response:
            print(f"  DEBUG: No files response or missing 'data' field")
            if files_response:
                print(f"  DEBUG: Response keys: {list(files_response.keys())}")
            return None

        files = files_response['data']
        print(f"  DEBUG: Found {len(files)} files for latest version search")

        # Find the latest version that matches our criteria
        # Filter for Fabric loader (modLoaderId = 4 for Fabric)
        for file_info in files:
            game_versions = file_info.get('gameVersions', []) or []

            # Check if it's for the right MC version and Fabric
            has_fabric = any('Fabric' in gv for gv in game_versions)
            has_mc_version = self.minecraft_version in game_versions

            if has_fabric and has_mc_version:
                version_display = file_info.get('displayName', '')
                file_id = file_info.get('id')
                if file_id:
                    return (version_display, environment, file_id)

        return None

    def _validate_curseforge_mod(self, mod: dict, mod_index: int, mod_name: str,
                                 version: str, project_id: int) -> bool:
        """Validate a CurseForge mod version"""
        if not self.curseforge_api_key:
            self.errors.append(f"Mod '{mod_name}': CurseForge API key not set. Set CURSEFORGE_API_KEY environment variable.")
            print(f"  [{mod_name}] ✗ CurseForge API key not set")
            return False

        source_config = self.mappings['sources']['curseforge']

        # Get mod info for environment
        mod_info_url = source_config['mod_info_url'].format(project_id=project_id)
        headers = {
            'Accept': 'application/json',
            'x-api-key': self.curseforge_api_key
        }

        print(f"  [{mod_name}] DEBUG: Fetching from {mod_info_url}")
        mod_info = self._fetch_json(mod_info_url, headers, debug=True)

        if not mod_info:
            self.errors.append(f"Mod '{mod_name}' (project_id: {project_id}) - API returned no response")
            print(f"  [{mod_name}] ✗ API RETURNED NO RESPONSE")
            print(f"  [{mod_name}] DEBUG: URL was {mod_info_url}")
            return False

        if 'data' not in mod_info:
            self.errors.append(f"Mod '{mod_name}' (project_id: {project_id}) not found on CurseForge")
            print(f"  [{mod_name}] ✗ PROJECT NOT FOUND on CurseForge")
            print(f"  [{mod_name}] DEBUG: Response structure: {list(mod_info.keys())}")
            if 'error' in mod_info or 'message' in mod_info:
                print(f"  [{mod_name}] DEBUG: Error message: {mod_info.get('error') or mod_info.get('message')}")
            return False

        environment = 'both'  # CurseForge doesn't provide explicit environment info

        # Get files list
        files_url = source_config['files_url'].format(project_id=project_id)
        print(f"  [{mod_name}] DEBUG: Fetching files from {files_url}")
        files_response = self._fetch_json(files_url, headers, debug=True)

        if not files_response or 'data' not in files_response:
            self.errors.append(f"Mod '{mod_name}': Failed to fetch files from CurseForge")
            print(f"  [{mod_name}] ✗ Failed to fetch files")
            if files_response:
                print(f"  [{mod_name}] DEBUG: Files response structure: {list(files_response.keys())}")
            return False

        files = files_response['data']
        print(f"  [{mod_name}] DEBUG: Found {len(files)} files")

        # Find matching version (can be file ID or display name)
        found_version = False
        correct_loader = False
        correct_mc_version = False
        matched_file_id = None

        for file_info in files:
            file_id_str = str(file_info.get('id', ''))
            display_name = file_info.get('displayName', '')

            # Check if version matches file ID or display name
            if version == file_id_str or version in display_name:
                found_version = True
                game_versions = file_info.get('gameVersions', []) or []

                # Check for Fabric loader
                if any('Fabric' in gv for gv in game_versions):
                    correct_loader = True

                # Check for MC version
                if self.minecraft_version in game_versions:
                    correct_mc_version = True

                if correct_loader and correct_mc_version:
                    matched_file_id = file_info.get('id')
                    # Update environment if missing
                    if 'environment' not in mod:
                        self.config['mods'][mod_index]['environment'] = environment
                        self.updates_made.append(f"{mod_name}: added environment={environment}")
                        self.config_modified = True

                    # Store file_id if not present
                    if 'file_id' not in mod and matched_file_id:
                        self.config['mods'][mod_index]['file_id'] = matched_file_id
                        self.updates_made.append(f"{mod_name}: added file_id={matched_file_id}")
                        self.config_modified = True

                    env_display = f" [{environment}]" if environment != 'both' else ""
                    print(f"  [{mod_name}] ✓ Version {version} found{env_display}")
                    return True

        # Handle different error cases
        if not found_version:
            print(f"  [{mod_name}] ✗ VERSION NOT FOUND: {version}")

            if self.auto_fix:
                result = self._find_latest_curseforge_version(mod_name, project_id)
                if result:
                    latest_version, latest_env, latest_file_id = result
                    env_display = f" [{latest_env}]" if latest_env != 'both' else ""
                    print(f"  [{mod_name}] → Auto-fixing to latest version: {latest_version}{env_display}")
                    self.config['mods'][mod_index]['version'] = latest_version
                    self.config['mods'][mod_index]['file_id'] = latest_file_id
                    self.config['mods'][mod_index]['environment'] = latest_env
                    self.updates_made.append(f"{mod_name}: {version} → {latest_version} (file_id={latest_file_id}, environment={latest_env})")
                    self.config_modified = True
                    return True
                else:
                    self.errors.append(f"Mod '{mod_name}': version '{version}' not found and no compatible version available")
                    print(f"  [{mod_name}] ✗ No compatible version found for MC {self.minecraft_version} + Fabric")
                    return False
            else:
                self.errors.append(f"Mod '{mod_name}': version '{version}' not found on CurseForge")
                return False

        elif not correct_loader:
            print(f"  [{mod_name}] ✗ VERSION FOUND but not for Fabric loader")
            if self.auto_fix:
                result = self._find_latest_curseforge_version(mod_name, project_id)
                if result:
                    latest_version, latest_env, latest_file_id = result
                    env_display = f" [{latest_env}]" if latest_env != 'both' else ""
                    print(f"  [{mod_name}] → Auto-fixing to latest Fabric version: {latest_version}{env_display}")
                    self.config['mods'][mod_index]['version'] = latest_version
                    self.config['mods'][mod_index]['file_id'] = latest_file_id
                    self.config['mods'][mod_index]['environment'] = latest_env
                    self.updates_made.append(f"{mod_name}: {version} → {latest_version} (Fabric, file_id={latest_file_id}, environment={latest_env})")
                    self.config_modified = True
                    return True
                else:
                    self.errors.append(f"Mod '{mod_name}': version '{version}' not available for Fabric loader")
                    return False
            else:
                self.errors.append(f"Mod '{mod_name}' version '{version}' not available for Fabric loader")
                return False

        elif not correct_mc_version:
            print(f"  [{mod_name}] ✗ VERSION FOUND but not for MC {self.minecraft_version}")
            if self.auto_fix:
                result = self._find_latest_curseforge_version(mod_name, project_id)
                if result:
                    latest_version, latest_env, latest_file_id = result
                    env_display = f" [{latest_env}]" if latest_env != 'both' else ""
                    print(f"  [{mod_name}] → Auto-fixing to version for MC {self.minecraft_version}: {latest_version}{env_display}")
                    self.config['mods'][mod_index]['version'] = latest_version
                    self.config['mods'][mod_index]['file_id'] = latest_file_id
                    self.config['mods'][mod_index]['environment'] = latest_env
                    self.updates_made.append(f"{mod_name}: {version} → {latest_version} (MC {self.minecraft_version}, file_id={latest_file_id}, environment={latest_env})")
                    self.config_modified = True
                    return True
                else:
                    self.errors.append(f"Mod '{mod_name}': version '{version}' not available for Minecraft {self.minecraft_version}")
                    return False
            else:
                self.errors.append(f"Mod '{mod_name}' version '{version}' not available for Minecraft {self.minecraft_version}")
                return False

        return False

    def validate_mod_versions(self) -> bool:
        """Validate all mod versions"""
        if not self.config or 'mods' not in self.config:
            return True

        mods = self.config['mods']
        if not isinstance(mods, list):
            return False

        print(f"\nValidating {len(mods)} mod versions...")
        if self.auto_fix:
            print("(Auto-fix mode enabled - will update config with latest compatible versions)")

        all_valid = True
        for i, mod in enumerate(mods):
            if isinstance(mod, dict) and 'name' in mod:
                if not self.validate_mod_version(mod, i):
                    all_valid = False

        return all_valid

    def validate(self) -> bool:
        """Run all validation checks"""
        print("="*70)
        print("CONFIG VALIDATION")
        print("="*70)
        print(f"Config file: {self.config_file}")
        print(f"Mappings file: {self.mappings_file}")
        if self.auto_fix:
            print(f"Auto-fix mode: ENABLED")

        # Step 1: Validate structure
        if not self.validate_structure():
            return False

        # Step 2: Validate Minecraft version
        minecraft_valid = self.validate_minecraft_version()

        # Step 3: Validate Fabric version
        fabric_valid = self.validate_fabric_version()

        # Step 4: Validate mod versions
        mods_valid = self.validate_mod_versions()

        # Save config if modifications were made
        if self.config_modified:
            print("\n" + "="*70)
            if self.auto_fix:
                print("AUTO-FIX SUMMARY")
            else:
                print("CONFIG UPDATE SUMMARY")
            print("="*70)
            print(f"\n{len(self.updates_made)} modification(s) made:\n")
            for update in self.updates_made:
                print(f"  • {update}")

            self._save_yaml()

        # Final report
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)

        if self.errors:
            print(f"\n✗ VALIDATION FAILED - {len(self.errors)} error(s) found:\n")
            for error in self.errors:
                print(f"  ✗ {error}")
        else:
            print("\n✓ VALIDATION PASSED - All checks successful!")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        print("="*70)

        return len(self.errors) == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate config.yaml structure and version availability'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--mappings',
        type=str,
        default='source_mappings.yaml',
        help='Path to source mappings file (default: source_mappings.yaml)'
    )
    parser.add_argument(
        '--auto-fix',
        action='store_true',
        help='Automatically update config with latest compatible versions when version not found'
    )

    args = parser.parse_args()

    validator = ConfigValidator(
        config_file=args.config,
        mappings_file=args.mappings,
        auto_fix=args.auto_fix
    )

    success = validator.validate()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
