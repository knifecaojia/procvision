import os
import json
import shutil
import zipfile
import subprocess
import time
import glob
import logging
import sys
from typing import List, Dict, Optional, Tuple

from .config import RunnerConfig
from .types import PackageState, RegistryEntry, ActiveMapping, Manifest
from .exceptions import (
    InvalidZipError, ManifestMissingError, WheelsMissingError, 
    InstallFailedError, ActivationConflictError, RunnerError
)

import re

logger = logging.getLogger(__name__)

class PackageManager:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self._ensure_dirs()
        self.registry: Dict[str, RegistryEntry] = self._load_registry()

    def _detect_python_version(self, wheels_path: str) -> Optional[str]:
        """Detects Python version from wheel filenames (e.g., cp310, cp312)."""
        if not os.path.exists(wheels_path):
            return None
        
        # Pattern to match cp38, cp310, cp312 etc.
        # Filename example: numpy-2.2.6-cp312-cp312-win_amd64.whl
        pattern = re.compile(r'-cp(\d{2,})-')
        
        versions = []
        for f in os.listdir(wheels_path):
            if f.endswith(".whl"):
                match = pattern.search(f)
                if match:
                    versions.append(match.group(1))
        
        if not versions:
            return None
            
        # Get most common version
        from collections import Counter
        most_common = Counter(versions).most_common(1)[0][0]
        
        # Convert "312" to "3.12"
        if len(most_common) >= 2:
            return f"{most_common[0]}.{most_common[1:]}"
        return None

    def _ensure_dirs(self):
        os.makedirs(self.config.zips_dir, exist_ok=True)
        os.makedirs(self.config.deployed_dir, exist_ok=True)
        os.makedirs(self.config.active_dir, exist_ok=True)
        os.makedirs(self.config.logs_dir, exist_ok=True)

    def _load_registry(self) -> Dict[str, RegistryEntry]:
        if not os.path.exists(self.config.registry_path):
            return {}
        try:
            with open(self.config.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert list to dict key=<name>:<version>
                registry = {}
                for item in data:
                    key = f"{item['name']}:{item['version']}"
                    registry[key] = item
                return registry
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}

    def _save_registry(self):
        try:
            with open(self.config.registry_path, "w", encoding="utf-8") as f:
                json.dump(list(self.registry.values()), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def scan_zips(self) -> List[str]:
        """Scans the zips directory for new packages."""
        return glob.glob(os.path.join(self.config.zips_dir, "*.zip"))

    def validate_package(self, zip_path: str) -> Manifest:
        """Validates the structure of a zip package."""
        if not zipfile.is_zipfile(zip_path):
            raise InvalidZipError(f"Not a valid zip file: {zip_path}")

        try:
            # Fix for encoding: Python's zipfile module handles filename encoding, 
            # but sometimes non-standard zips (e.g. from Windows) use CP437 or GBK without flag.
            # We must use metadata_encoding='utf-8' if possible, or manual fix.
            # Python 3.11+ supports metadata_encoding in ZipFile.
            # For older Python, we rely on standard behavior.
            # If filenames are garbled (e.g. '╩╙╛⌡...'), extraction will fail or produce garbage.
            
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Attempt to fix encoding of filenames in namelist if they look like CP437 interpreted as UTF-8/GBK?
                # Actually, standard zipfile behavior:
                # If flag_bits & 0x800, name is UTF-8. Else CP437.
                # Chinese Windows zips often use GBK but don't set the flag, so they are read as CP437.
                
                namelist = []
                for info in z.infolist():
                    name = info.filename
                    # Try to decode if it looks garbled
                    # Common issue: CP437 bytes that are actually GBK
                    try:
                        # Check if we can encode back to CP437 and decode as GBK
                        # This is a heuristic.
                        if info.flag_bits & 0x800:
                            # It is UTF-8, trust it
                            pass
                        else:
                            # It was decoded as CP437 by default (in Python < 3.11 logic or if not flagged)
                            # Let's try to recover raw bytes
                            raw = name.encode('cp437')
                            # Try decoding as GBK
                            name = raw.decode('gbk')
                    except Exception:
                        pass
                    namelist.append(name)
                
                # We can't easily change the filenames inside the ZipFile object for extraction directly.
                # But we can find the manifest and wheels using corrected names to validate logic.
                # HOWEVER, install_package uses extractall(), which will use the filenames AS IS in the zip object.
                # So if they are garbled in the zip object (because of mismatch encoding), they will be extracted as garbled files.
                # That's exactly what happened: '╩╙╛⌡...' directory was created.
                
                # To fix this, we need to manually extract files with corrected names.
                # 1. Find manifest using corrected names logic.
                
                manifest_path_corrected = None
                manifest_info = None
                algo_root_corrected = None
                
                for idx, info in enumerate(z.infolist()):
                    name = namelist[idx] # Corrected name
                    if name.endswith("manifest.json"):
                        manifest_path_corrected = name
                        manifest_info = info
                        algo_root_corrected = os.path.dirname(name)
                        break
                
                if not manifest_info:
                    raise ManifestMissingError("manifest.json missing in any subdirectory")

                # 2. Find wheels directory
                wheels_path_corrected = None
                wheel_dirs = [n for n in namelist if n.endswith("wheels/") or n == "wheels/"]
                
                if not wheel_dirs:
                    for n in namelist:
                        parts = n.split("/")
                        if "wheels" in parts:
                            idx = parts.index("wheels")
                            wheels_path_corrected = "/".join(parts[:idx+1])
                            break
                else:
                    wheel_dirs.sort(key=len)
                    wheels_path_corrected = wheel_dirs[0].rstrip("/")

                if not wheels_path_corrected:
                     raise WheelsMissingError("wheels/ directory missing")

                # Read manifest content (using original info)
                with z.open(manifest_info) as f:
                    manifest: Manifest = json.load(f)
                    
                    # Inject internal path info for installation
                    manifest["_internal_root"] = algo_root_corrected
                    manifest["_internal_wheels_path"] = wheels_path_corrected
                    manifest["_needs_encoding_fix"] = True # Signal to install_package
                    return manifest
        except RunnerError:
            raise
        except Exception as e:
            raise InvalidZipError(f"Validation failed: {str(e)}")

    def install_package(self, zip_path: str, force: bool = False) -> RegistryEntry:
        """Installs a package from a zip file."""
        manifest = self.validate_package(zip_path)
        name = manifest["name"]
        version = manifest["version"]
        algo_root = manifest.get("_internal_root", "")
        wheels_internal_path = manifest.get("_internal_wheels_path", "wheels")
        needs_fix = manifest.get("_needs_encoding_fix", False)
        
        key = f"{name}:{version}"

        if key in self.registry and not force:
            logger.info(f"Package {key} already installed.")
            return self.registry[key]

        install_dir = os.path.join(self.config.deployed_dir, name, version)
        if os.path.exists(install_dir):
            if force:
                shutil.rmtree(install_dir)
            else:
                logger.warning(f"Installation directory exists but not in registry: {install_dir}")

        try:
            # 1. Unzip with encoding fix
            os.makedirs(install_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as z:
                if not needs_fix:
                     z.extractall(install_dir)
                else:
                    # Manually extract and rename
                    for info in z.infolist():
                        # Logic to fix name
                        filename = info.filename
                        if not (info.flag_bits & 0x800):
                            try:
                                filename = filename.encode('cp437').decode('gbk')
                            except:
                                pass
                        
                        # Prevent path traversal
                        if filename.startswith("/") or ".." in filename:
                            continue
                            
                        target_path = os.path.join(install_dir, filename)
                        
                        if info.is_dir():
                            os.makedirs(target_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            with z.open(info) as source, open(target_path, "wb") as target:
                                shutil.copyfileobj(source, target)

            # 2. Create venv or conda env
            venv_dir = os.path.join(install_dir, "venv")
            
            # Determine target python version
            # First check manifest, then check wheels
            target_py_version = manifest.get("python_version")
            wheels_dir_abs = os.path.join(install_dir, wheels_internal_path)
            
            if not target_py_version:
                target_py_version = self._detect_python_version(wheels_dir_abs)
                if target_py_version:
                    logger.info(f"Detected Python version from wheels: {target_py_version}")
            
            # Check if we need Conda
            use_conda = False
            current_py = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            if target_py_version and target_py_version != current_py:
                # Try to use Conda
                try:
                    subprocess.check_call(["conda", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    use_conda = True
                    logger.info(f"Target Python {target_py_version} != Current {current_py}. Using Conda.")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    logger.warning(f"Target Python {target_py_version} requested but Conda not found. Trying venv (might fail).")

            python_rel_path = ""
            
            if use_conda:
                logger.info(f"Creating Conda env at {venv_dir} with python={target_py_version}...")
                # Create conda env in prefix mode
                cmd = ["conda", "create", "-p", venv_dir, f"python={target_py_version}", "-y"]
                # We might need to handle offline mode for conda too if no internet?
                # Assuming conda can fetch python or has it cached. 
                # If offline, this will fail unless user has local channel.
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    logger.error("Conda create failed. Check internet connection or conda config.")
                    raise InstallFailedError(f"Conda create failed: {e}")
                
                # Resolve paths for Conda (Windows)
                # In prefix env: python.exe is at root, pip is in Scripts
                if os.name == 'nt':
                    python_cmd = os.path.join(venv_dir, "python.exe")
                    pip_cmd = os.path.join(venv_dir, "Scripts", "pip.exe")
                    python_rel_path = "venv/python.exe"
                else:
                    python_cmd = os.path.join(venv_dir, "bin", "python")
                    pip_cmd = os.path.join(venv_dir, "bin", "pip")
                    python_rel_path = "venv/bin/python"

            else:
                logger.info(f"Creating venv at {venv_dir}...")
                subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
                
                if os.name == 'nt':
                    python_cmd = os.path.join(venv_dir, "Scripts", "python.exe")
                    pip_cmd = os.path.join(venv_dir, "Scripts", "pip.exe")
                    python_rel_path = "venv/Scripts/python.exe"
                else:
                    python_cmd = os.path.join(venv_dir, "bin", "python")
                    pip_cmd = os.path.join(venv_dir, "bin", "pip")
                    python_rel_path = "venv/bin/python"

            # 3. Install dependencies
            # Determine pip path in venv

            # Resolve actual paths on disk
            wheels_dir = os.path.join(install_dir, wheels_internal_path)
            requirements_path = os.path.join(install_dir, algo_root, "requirements.txt")

            logger.info(f"Installing dependencies for {key}...")
            logger.info(f"Wheels dir: {wheels_dir}")
            logger.info(f"Requirements: {requirements_path}")
            
            cmd = [
                pip_cmd, "install",
                "--no-index",
                "--find-links", wheels_dir,
                "-r", requirements_path
            ]
            # Capture output to show error details
            try:
                subprocess.run(
                    cmd, 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Pip install stdout: {e.stdout}")
                logger.error(f"Pip install stderr: {e.stderr}")
                raise InstallFailedError(f"Pip install failed: {e.stderr}")

            # 4. Register
            entry: RegistryEntry = {
                "name": name,
                "version": version,
                "supported_pids": manifest["supported_pids"],
                "state": PackageState.INSTALLED,
                "created_at": time.time(),
                "install_path": install_dir, # Root with venv
                "working_dir": os.path.join(install_dir, algo_root).replace("\\", "/"), # Actual algo root
                "python_rel_path": python_rel_path # Relative path to python executable
            }

            self.registry[key] = entry
            self._save_registry()
            logger.info(f"Package {key} installed successfully.")
            return entry

        except subprocess.CalledProcessError as e:
            shutil.rmtree(install_dir, ignore_errors=True)
            raise InstallFailedError(f"Pip install failed: {e}")
        except Exception as e:
            shutil.rmtree(install_dir, ignore_errors=True)
            raise InstallFailedError(f"Installation failed: {str(e)}")

    def activate_package(self, pid: str, name: str, version: str) -> ActiveMapping:
        """Activates a package for a specific PID."""
        key = f"{name}:{version}"
        if key not in self.registry:
            raise RunnerError(f"Package {key} not installed", "2005")

        package = self.registry[key]
        if pid not in package["supported_pids"]:
            raise ActivationConflictError(f"PID {pid} not supported by {key}")

        mapping: ActiveMapping = {
            "name": name,
            "version": version,
            "activated_at": time.time()
        }
        
        mapping_path = os.path.join(self.config.active_dir, f"{pid}.json")
        try:
            with open(mapping_path, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2)
        except Exception as e:
            raise RunnerError(f"Failed to activate package: {e}", "2006")
        
        return mapping

    def get_active_package(self, pid: str) -> Optional[RegistryEntry]:
        """Returns the active package entry for a PID."""
        mapping_path = os.path.join(self.config.active_dir, f"{pid}.json")
        if not os.path.exists(mapping_path):
            return None
        
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping: ActiveMapping = json.load(f)
            
            key = f"{mapping['name']}:{mapping['version']}"
            return self.registry.get(key)
        except Exception:
            return None

    def get_package_path(self, name: str, version: str) -> Optional[str]:
        key = f"{name}:{version}"
        if key in self.registry:
            return self.registry[key]["install_path"]
        return None

    def uninstall_package(self, name: str, version: str):
        """Uninstalls a deployed package."""
        key = f"{name}:{version}"
        if key not in self.registry:
            raise RunnerError(f"Package {key} not installed", "2005")

        # Check if active
        for mapping_file in glob.glob(os.path.join(self.config.active_dir, "*.json")):
            try:
                with open(mapping_file, "r") as f:
                    mapping = json.load(f)
                    if mapping.get("name") == name and mapping.get("version") == version:
                         raise UnsafeUninstallError(f"Package {key} is currently active")
            except Exception:
                pass

        install_path = self.registry[key]["install_path"]
        try:
            shutil.rmtree(install_path)
        except Exception as e:
            logger.error(f"Failed to remove directory {install_path}: {e}")
            # Continue to remove from registry

        del self.registry[key]
        self._save_registry()
        logger.info(f"Package {key} uninstalled.")

    def delete_zip(self, name: str, version: str):
        """Deletes the zip file for a package."""
        # This is a bit heuristic since we don't store exact zip paths, 
        # but we can search for name-version patterns or assume a naming convention.
        # For this implementation, we'll search.
        pattern = f"{name}-v{version}*.zip" # Assumption: <name>-v<version>...
        # Also try without 'v' prefix if needed, or rely on caller to provide filename?
        # The spec says "Scan zips". Let's try to match more loosely or assume standard naming.
        
        # Better approach: Scan all zips, inspect manifest inside? Too slow.
        # Let's assume standard naming: <name>-<version>.zip or <name>-v<version>.zip
        
        candidates = glob.glob(os.path.join(self.config.zips_dir, "*.zip"))
        for zip_path in candidates:
            # Quick check on filename
            filename = os.path.basename(zip_path)
            if name in filename and version in filename:
                try:
                    os.remove(zip_path)
                    logger.info(f"Deleted zip: {zip_path}")
                    return
                except Exception as e:
                    logger.error(f"Failed to delete zip {zip_path}: {e}")
                    raise RunnerError(f"Failed to delete zip: {e}")
        
        logger.warning(f"Zip not found for {name} {version}")
