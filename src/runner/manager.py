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

logger = logging.getLogger(__name__)

class PackageManager:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self._ensure_dirs()
        self.registry: Dict[str, RegistryEntry] = self._load_registry()

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
            with zipfile.ZipFile(zip_path, 'r') as z:
                namelist = z.namelist()
                
                if "manifest.json" not in namelist:
                    raise ManifestMissingError("manifest.json missing")
                if "requirements.txt" not in namelist:
                    raise WheelsMissingError("requirements.txt missing")
                
                # Check for wheels directory
                has_wheels = any(n.startswith("wheels/") for n in namelist)
                if not has_wheels:
                    raise WheelsMissingError("wheels/ directory missing")

                with z.open("manifest.json") as f:
                    manifest: Manifest = json.load(f)
                    required_fields = ["name", "version", "entry_point", "supported_pids"]
                    for field in required_fields:
                        if field not in manifest:
                            raise ManifestMissingError(f"Manifest missing field: {field}")
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
            # 1. Unzip
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(install_dir)

            # 2. Create venv
            venv_dir = os.path.join(install_dir, "venv")
            logger.info(f"Creating venv at {venv_dir}...")
            subprocess.check_call([sys.executable, "-m", "venv", venv_dir])

            # 3. Install dependencies
            # Determine pip path in venv
            if os.name == 'nt':
                pip_cmd = os.path.join(venv_dir, "Scripts", "pip.exe")
                python_cmd = os.path.join(venv_dir, "Scripts", "python.exe")
            else:
                pip_cmd = os.path.join(venv_dir, "bin", "pip")
                python_cmd = os.path.join(venv_dir, "bin", "python")

            wheels_dir = os.path.join(install_dir, "wheels")
            requirements_path = os.path.join(install_dir, "requirements.txt")

            logger.info(f"Installing dependencies for {key}...")
            cmd = [
                pip_cmd, "install",
                "--no-index",
                "--find-links", wheels_dir,
                "-r", requirements_path
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            # 4. Register
            entry: RegistryEntry = {
                "name": name,
                "version": version,
                "supported_pids": manifest["supported_pids"],
                "state": PackageState.INSTALLED,
                "created_at": time.time(),
                "install_path": install_dir
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
