#!/usr/bin/env python3
"""
Universal downloader for Minecraft server, Fabric, and mods with caching support.
Downloads based on config.yaml and source_mappings.yaml
"""
import os
import sys
import json
import yaml
import urllib.request
import urllib.error
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


class DownloadManager:
    """Manages downloads with caching support"""

    def __init__(self, config_file: str = "config.yaml",
                 mappings_file: str = "source_mappings.yaml",
                 cache_file: str = ".download_cache.json"):
        self.config = self._load_yaml(config_file)
        self.mappings = self._load_yaml(mappings_file)
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.minecraft_version = self.config.get('minecraft', {}).get('version')
        self.curseforge_api_key = os.environ.get('CURSEFORGE_API_KEY')

    def _load_yaml(self, file_path: str) -> dict:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}")
            sys.exit(1)

    def _load_cache(self) -> dict:
        """Load download cache from JSON file"""
        if not os.path.exists(self.cache_file):
            print(f"No cache file found at {self.cache_file}")
            return {}

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                print(f"Loaded cache file: {self.cache_file}")
                return cache
        except json.JSONDecodeError as e:
            print(f"Warning: Cache file is corrupted: {e}")
            return {}

    def _save_cache(self):
        """Save download cache to JSON file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Cache saved to: {self.cache_file}")
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def _fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[dict]:
        """Fetch JSON data from URL"""
        try:
            req = urllib.request.Request(url)
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)

            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            print(f"  Error: HTTP {e.code} when fetching {url}")
            return None
        except Exception as e:
            print(f"  Error fetching {url}: {e}")
            return None

    def _download_file(self, url: str, destination: str) -> bool:
        """Download a file from URL to destination"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination) if os.path.dirname(destination) else '.', exist_ok=True)

            print(f"  Downloading: {url}")
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'minecraft-server-manager/1.0')

            with urllib.request.urlopen(req, timeout=60) as response:
                with open(destination, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)

            file_size = os.path.getsize(destination)
            print(f"  ✓ Downloaded: {destination} ({file_size:,} bytes)")
            return True

        except Exception as e:
            print(f"  ✗ Error downloading: {e}")
            if os.path.exists(destination):
                os.remove(destination)
            return False

    def _resolve_minecraft_url(self, version: str) -> Optional[Tuple[str, str]]:
        """Resolve Minecraft server download URL"""
        source_config = self.mappings['sources']['mojang']
        manifest_url = source_config['manifest_url']

        manifest = self._fetch_json(manifest_url)
        if not manifest:
            return None

        # Find the requested version
        for v in manifest.get('versions', []):
            if v['id'] == version:
                # Get version-specific details
                version_info = self._fetch_json(v['url'])
                if version_info:
                    server_url = version_info.get('downloads', {}).get('server', {}).get('url')
                    if server_url:
                        filename = source_config['filename_pattern']
                        return (server_url, filename)

        return None

    def _resolve_fabric_url(self, minecraft_version: str, fabric_version: str) -> Optional[Tuple[str, str]]:
        """Resolve Fabric loader download URL"""
        source_config = self.mappings['sources']['fabric']
        url = source_config['manifest_url'].format(
            minecraft_version=minecraft_version,
            version=fabric_version
        )
        filename = source_config['filename_pattern']
        return (url, filename)

    def _resolve_modrinth_url(self, mod_name: str, version: str, slug: Optional[str] = None) -> Optional[Tuple[str, str, str]]:
        """
        Resolve Modrinth mod download URL
        Returns: (download_url, filename, resolved_slug)
        """
        source_config = self.mappings['sources']['modrinth']

        # Determine project ID/slug to use:
        # 1. Check if there's an explicit mapping (for special cases)
        # 2. Use provided slug from config
        # 3. Fall back to mod_name as slug
        project_mappings = source_config.get('project_mappings', {})
        project_id = project_mappings.get(mod_name, slug or mod_name)

        # Fetch version list
        manifest_url = source_config['manifest_url'].format(project_id=project_id)
        headers = {'User-Agent': source_config.get('user_agent', 'minecraft-server-manager/1.0')}

        versions = self._fetch_json(manifest_url, headers)
        if not versions:
            return None

        # Find matching version with Fabric loader and current MC version
        for ver_info in versions:
            if ver_info.get('version_number') == version:
                # Check if it's for the right loader and MC version
                loaders = ver_info.get('loaders', [])
                game_versions = ver_info.get('game_versions', [])

                if 'fabric' in loaders and self.minecraft_version in game_versions:
                    files = ver_info.get('files', [])
                    if files:
                        primary_file = files[0]
                        download_url = primary_file.get('url')
                        # Use slug-based filename for version management
                        filename = f"{project_id}.jar"
                        if download_url:
                            return (download_url, filename, project_id)

        return None

    def _resolve_custom_url(self, mod_config: dict) -> Optional[Tuple[str, str]]:
        """Resolve custom direct download URL"""
        download_url = mod_config.get('download_url')
        if not download_url:
            return None

        # Try to extract filename from URL
        filename = download_url.split('/')[-1].split('?')[0]
        if not filename.endswith('.jar'):
            filename = f"{mod_config.get('name', 'mod')}.jar"

        return (download_url, filename)

    def _resolve_curseforge_url(self, mod_name: str, version: str, project_id: int,
                                file_id: Optional[int] = None) -> Optional[Tuple[str, str]]:
        """
        Resolve CurseForge mod download URL
        Returns: (download_url, filename)
        """
        if not self.curseforge_api_key:
            print(f"  Error: CurseForge API key not set")
            return None

        source_config = self.mappings['sources']['curseforge']
        headers = {
            'Accept': 'application/json',
            'x-api-key': self.curseforge_api_key
        }

        # If file_id is provided, fetch that specific file
        if file_id:
            file_url = f"{source_config['api_base']}/mods/{project_id}/files/{file_id}"
            file_info = self._fetch_json(file_url, headers)

            if file_info and 'data' in file_info:
                file_data = file_info['data']
                download_url = file_data.get('downloadUrl')
                filename = file_data.get('fileName', f"{mod_name}.jar")
                if download_url:
                    return (download_url, filename)

        # Otherwise, search for version in files list
        files_url = source_config['files_url'].format(project_id=project_id)
        files_response = self._fetch_json(files_url, headers)

        if not files_response or 'data' not in files_response:
            return None

        files = files_response['data']

        # Find matching version
        for file_info in files:
            file_id_str = str(file_info.get('id', ''))
            display_name = file_info.get('displayName', '')

            if version == file_id_str or version in display_name:
                game_versions = file_info.get('gameVersions', []) or []

                # Check for Fabric and MC version
                has_fabric = any('Fabric' in gv for gv in game_versions)
                has_mc_version = self.minecraft_version in game_versions

                if has_fabric and has_mc_version:
                    download_url = file_info.get('downloadUrl')
                    filename = file_info.get('fileName', f"{mod_name}.jar")
                    if download_url:
                        return (download_url, filename)

        return None

    def build_download_list(self) -> Dict[str, dict]:
        """Build list of files to download by resolving URLs"""
        print("\n" + "="*70)
        print("BUILDING DOWNLOAD LIST")
        print("="*70)

        downloads = {}

        # Minecraft server
        minecraft_config = self.config.get('minecraft', {})
        if minecraft_config:
            version = minecraft_config.get('version')
            source = minecraft_config.get('source', 'mojang')

            print(f"\nResolving Minecraft {version}...")
            result = self._resolve_minecraft_url(version)
            if result:
                url, filename = result
                target_dir = self.mappings['sources'][source]['target_dir']
                downloads['minecraft'] = {
                    'type': 'minecraft',
                    'name': 'Minecraft Server',
                    'version': version,
                    'url': url,
                    'filename': filename,
                    'target_dir': target_dir,
                    'destination': os.path.join(target_dir, filename)
                }
                print(f"  ✓ Found: {filename}")
            else:
                print(f"  ✗ Failed to resolve Minecraft {version}")

        # Fabric loader
        fabric_config = self.config.get('fabric', {})
        if fabric_config:
            version = fabric_config.get('version')
            source = fabric_config.get('source', 'fabric')

            print(f"\nResolving Fabric {version}...")
            result = self._resolve_fabric_url(self.minecraft_version, version)
            if result:
                url, filename = result
                target_dir = self.mappings['sources'][source]['target_dir']
                downloads['fabric'] = {
                    'type': 'fabric',
                    'name': 'Fabric Loader',
                    'version': version,
                    'url': url,
                    'filename': filename,
                    'target_dir': target_dir,
                    'destination': os.path.join(target_dir, filename)
                }
                print(f"  ✓ Found: {filename}")
            else:
                print(f"  ✗ Failed to resolve Fabric {version}")

        # Mods
        mods_config = self.config.get('mods', [])
        if mods_config:
            print(f"\nResolving {len(mods_config)} mods...")

            for mod in mods_config:
                mod_name = mod.get('name')
                version = mod.get('version')
                source = mod.get('source', 'modrinth')
                slug = mod.get('slug')  # Optional slug override
                environment = mod.get('environment', 'both')  # client, server, or both

                print(f"  [{mod_name}] ", end='')

                # Check if version is missing
                if not version:
                    print(f"✗ Missing version (run validation script first)")
                    continue

                result = None
                resolved_slug = None

                if source == 'modrinth':
                    modrinth_result = self._resolve_modrinth_url(mod_name, version, slug)
                    if modrinth_result:
                        url, filename, resolved_slug = modrinth_result
                        result = (url, filename)
                elif source == 'curseforge':
                    project_id = mod.get('project_id')
                    file_id = mod.get('file_id')
                    if project_id:
                        curseforge_result = self._resolve_curseforge_url(mod_name, version, project_id, file_id)
                        if curseforge_result:
                            url, filename = curseforge_result
                            result = (url, filename)
                            resolved_slug = f"cf_{project_id}"  # Use project_id as slug for CurseForge
                    else:
                        print(f"✗ Missing project_id")
                        continue
                elif source == 'custom':
                    result = self._resolve_custom_url(mod)

                if result:
                    url, filename = result
                    base_target_dir = self.mappings['sources'][source]['target_dir']

                    # Determine destinations based on environment
                    destinations = []
                    if environment in ['server', 'both']:
                        destinations.append(os.path.join(base_target_dir, filename))
                    if environment in ['client', 'both']:
                        client_dir = os.path.join(base_target_dir, 'client')
                        destinations.append(os.path.join(client_dir, filename))

                    downloads[f'mod_{mod_name}'] = {
                        'type': 'mod',
                        'name': mod_name,
                        'version': version,
                        'url': url,
                        'filename': filename,
                        'target_dir': base_target_dir,
                        'environment': environment,
                        'destinations': destinations,  # Multiple destinations for 'both'
                        'slug': resolved_slug  # Store for reference
                    }
                    env_info = f" [{environment}]" if environment != 'both' else ""
                    print(f"✓ {filename}{env_info}")
                else:
                    print(f"✗ Failed")

        print(f"\n{'─'*70}")
        print(f"Total items resolved: {len(downloads)}")
        return downloads

    def download_all(self, download_list: Optional[Dict[str, dict]] = None):
        """Download all files from the download list"""
        if download_list is None:
            download_list = self.build_download_list()

        if not download_list:
            print("\n✗ No items to download")
            return

        print("\n" + "="*70)
        print("DOWNLOADING FILES")
        print("="*70)

        success_count = 0
        fail_count = 0

        for key, item in download_list.items():
            env_info = f" [{item.get('environment', 'both')}]" if item.get('environment') != 'both' else ""
            print(f"\n[{item['name']} {item['version']}]{env_info}")

            # Handle mods with multiple destinations (client/server/both)
            if item.get('type') == 'mod' and 'destinations' in item:
                destinations = item['destinations']
                slug = item.get('slug')

                # Remove old versions from all destination directories
                if slug:
                    for dest in destinations:
                        if os.path.exists(dest):
                            old_size = os.path.getsize(dest)
                            print(f"  ℹ Removing old version: {dest} ({old_size:,} bytes)")
                            try:
                                os.remove(dest)
                            except Exception as e:
                                print(f"  ⚠ Warning: Could not remove old file: {e}")

                # Download to first destination
                first_dest = destinations[0]
                if self._download_file(item['url'], first_dest):
                    # Copy to additional destinations if needed
                    for dest in destinations[1:]:
                        try:
                            print(f"  ℹ Copying to: {dest}")
                            shutil.copy2(first_dest, dest)
                        except Exception as e:
                            print(f"  ⚠ Warning: Could not copy to {dest}: {e}")
                    success_count += 1
                else:
                    fail_count += 1

            # Handle non-mods with single destination
            else:
                destination = item.get('destination')
                if not destination:
                    print(f"  ✗ No destination specified")
                    fail_count += 1
                    continue

                # Check if file already exists
                if os.path.exists(destination):
                    file_size = os.path.getsize(destination)
                    print(f"  ℹ File exists: {destination} ({file_size:,} bytes)")
                    print(f"  Skipping download")
                    success_count += 1
                    continue

                # Download the file
                if self._download_file(item['url'], destination):
                    success_count += 1
                else:
                    fail_count += 1

        # Save the download list as cache
        self.cache = {
            'minecraft_version': self.minecraft_version,
            'downloads': download_list
        }
        self._save_cache()

        print("\n" + "="*70)
        print(f"Download Summary: {success_count} successful, {fail_count} failed")
        print("="*70)

    def download_from_cache(self):
        """Download files using cached download list"""
        if not self.cache or 'downloads' not in self.cache:
            print("\n✗ No valid cache found. Building download list...")
            self.download_all()
            return

        download_list = self.cache['downloads']
        cached_mc_version = self.cache.get('minecraft_version')

        print("\n" + "="*70)
        print("USING CACHED DOWNLOAD LIST")
        print("="*70)
        print(f"Cached MC version: {cached_mc_version}")
        print(f"Current MC version: {self.minecraft_version}")
        print(f"Total items: {len(download_list)}")

        if cached_mc_version != self.minecraft_version:
            print(f"\n⚠ Warning: Minecraft version mismatch!")
            print(f"  Cache may be outdated. Consider rebuilding.")

        self.download_all(download_list)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Download Minecraft server, Fabric loader, and mods with caching'
    )
    parser.add_argument(
        '--rebuild-cache',
        action='store_true',
        help='Rebuild download cache from config instead of using existing cache'
    )
    parser.add_argument(
        '--cache-file',
        type=str,
        default='.download_cache.json',
        help='Path to cache file (default: .download_cache.json)'
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

    args = parser.parse_args()

    print("="*70)
    print("MINECRAFT SERVER DOWNLOAD MANAGER")
    print("="*70)

    manager = DownloadManager(
        config_file=args.config,
        mappings_file=args.mappings,
        cache_file=args.cache_file
    )

    if args.rebuild_cache or not manager.cache:
        print("\nMode: Building new download list")
        manager.download_all()
    else:
        print("\nMode: Using cached download list")
        manager.download_from_cache()

    print()


if __name__ == '__main__':
    main()
