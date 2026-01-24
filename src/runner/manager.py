import os
import json
import shutil
import zipfile
import subprocess
import time
import glob
import logging
import sys
import tempfile
import threading
from typing import List, Dict, Optional, Tuple, Any

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
        self._registry_lock = threading.Lock()
        self._ensure_dirs()
        self.registry: Dict[str, RegistryEntry] = self._load_registry()
        try:
            self._reconcile_registry_with_deployed()
        except Exception:
            pass

    def _extract_zip_with_progress(
        self,
        zip_path: str,
        install_dir: str,
        needs_fix: bool,
        progress_callback=None,
        start_percent: int = 0,
        end_percent: int = 70,
    ) -> None:
        start_percent = int(start_percent)
        end_percent = int(end_percent)
        start_percent = max(0, min(100, start_percent))
        end_percent = max(0, min(100, end_percent))
        if end_percent < start_percent:
            start_percent, end_percent = end_percent, start_percent

        def emit(value: int) -> None:
            if not progress_callback:
                return
            progress_callback.emit(max(0, min(100, int(value))))

        emit(start_percent)
        with zipfile.ZipFile(zip_path, "r") as z:
            infos = [info for info in z.infolist() if not info.is_dir()]
            total_bytes = sum(int(getattr(info, "file_size", 0) or 0) for info in infos)
            total_files = len(infos)
            done_bytes = 0
            done_files = 0
            last_percent = start_percent

            for info in z.infolist():
                filename = info.filename
                if needs_fix and not (info.flag_bits & 0x800):
                    try:
                        filename = filename.encode("cp437").decode("gbk")
                    except Exception:
                        pass

                if filename.startswith("/") or ".." in filename:
                    continue

                target_path = os.path.join(install_dir, filename)
                if info.is_dir():
                    os.makedirs(target_path, exist_ok=True)
                    continue

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with z.open(info) as source, open(target_path, "wb") as target:
                    while True:
                        chunk = source.read(1024 * 1024)
                        if not chunk:
                            break
                        target.write(chunk)
                        done_bytes += len(chunk)
                        if not progress_callback:
                            continue
                        if total_bytes > 0:
                            ratio = min(1.0, done_bytes / total_bytes)
                        else:
                            ratio = min(1.0, done_files / max(1, total_files))
                        percent = start_percent + int(ratio * (end_percent - start_percent))
                        if percent != last_percent:
                            last_percent = percent
                            emit(percent)

                done_files += 1
                if progress_callback and total_bytes <= 0:
                    ratio = min(1.0, done_files / max(1, total_files))
                    percent = start_percent + int(ratio * (end_percent - start_percent))
                    if percent != last_percent:
                        last_percent = percent
                        emit(percent)

        emit(end_percent)

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
                    try:
                        spids = item.get("supported_pids", [])
                        if spids is None:
                            spids = []
                        item["supported_pids"] = [str(p).strip() for p in spids if str(p).strip()]
                    except Exception:
                        item["supported_pids"] = []
                    try:
                        if not item.get("supported_pids"):
                            install_path = item.get("install_path")
                            working_dir = item.get("working_dir")
                            candidates = []
                            if working_dir:
                                candidates.append(os.path.join(working_dir, "manifest.json"))
                            if install_path:
                                candidates.append(os.path.join(install_path, "manifest.json"))
                            for p in candidates:
                                if p and os.path.exists(p):
                                    with open(p, "r", encoding="utf-8") as mf:
                                        mf_data = json.load(mf) or {}
                                    sp = mf_data.get("supported_pids", []) or []
                                    item["supported_pids"] = [str(x).strip() for x in sp if str(x).strip()]
                                    break
                    except Exception:
                        pass
                    key = f"{item['name']}:{item['version']}"
                    registry[key] = item
                return registry
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}

    def reload_registry(self) -> None:
        self.registry = self._load_registry()

    def _save_registry(self):
        registry_path = self.config.registry_path
        parent = os.path.dirname(registry_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_fd = None
        tmp_path = None
        with self._registry_lock:
            try:
                tmp_fd, tmp_path = tempfile.mkstemp(prefix="registry.", suffix=".tmp", dir=parent or None, text=True)
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    tmp_fd = None
                    json.dump(list(self.registry.values()), f, indent=2)
                os.replace(tmp_path, registry_path)
                tmp_path = None
            except Exception as e:
                raise RunnerError(f"Failed to save registry: {e}", "2005")
            finally:
                try:
                    if tmp_fd is not None:
                        os.close(tmp_fd)
                except Exception:
                    pass
                try:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

    def _reconcile_registry_with_deployed(self) -> None:
        changed = False
        deployed_dir = self.config.deployed_dir
        if not os.path.isdir(deployed_dir):
            return

        def _read_manifest(path: str) -> Dict[str, Any]:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
            except UnicodeDecodeError:
                pass
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return json.load(f) or {}
            except Exception:
                pass
            try:
                with open(path, "r", encoding="gbk") as f:
                    return json.load(f) or {}
            except Exception:
                pass
            with open(path, "rb") as f:
                raw = f.read()
            try:
                return json.loads(raw.decode("utf-8", errors="ignore")) or {}
            except Exception:
                return json.loads(raw.decode("latin-1")) or {}

        for child in os.listdir(deployed_dir):
            install_path = os.path.join(deployed_dir, child)
            if not os.path.isdir(install_path):
                continue

            manifest_path = None
            working_dir = install_path
            try:
                for root, dirs, files in os.walk(install_path):
                    dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}]
                    if "manifest.json" in files:
                        manifest_path = os.path.join(root, "manifest.json")
                        working_dir = root
                        break
            except Exception:
                manifest_path = None

            if not manifest_path:
                continue

            try:
                mf = _read_manifest(manifest_path)
            except Exception:
                continue

            name = str(mf.get("name") or "").strip()
            version = str(mf.get("version") or "").strip()
            if not name or not version:
                if "-" in child:
                    n, v = child.rsplit("-", 1)
                    name = name or n
                    version = version or v
            if not name or not version:
                continue

            key = f"{name}:{version}"
            if key in self.registry:
                continue

            python_rel = ""
            if os.name == "nt":
                candidates = [
                    os.path.join(install_path, "__procvision_env", "Scripts", "python.exe"),
                    os.path.join(install_path, "_env", "Scripts", "python.exe"),
                    os.path.join(install_path, "venv", "Scripts", "python.exe"),
                ]
            else:
                candidates = [
                    os.path.join(install_path, "__procvision_env", "bin", "python"),
                    os.path.join(install_path, "_env", "bin", "python"),
                    os.path.join(install_path, "venv", "bin", "python"),
                ]
            for c in candidates:
                if os.path.exists(c):
                    python_rel = os.path.relpath(c, install_path).replace("\\", "/")
                    break

            spids = mf.get("supported_pids", []) or []
            supported_pids = [str(p).strip() for p in spids if str(p).strip()]
            try:
                created_at = float(os.path.getmtime(install_path))
            except Exception:
                created_at = time.time()

            entry: RegistryEntry = {
                "name": name,
                "version": version,
                "supported_pids": supported_pids,
                "state": PackageState.INSTALLED,
                "created_at": created_at,
                "install_path": install_path,
                "working_dir": working_dir.replace("\\", "/"),
                "python_rel_path": python_rel,
            }
            self.registry[key] = entry
            changed = True

        for key, entry in list(self.registry.items()):
            try:
                install_path = entry.get("install_path")
            except Exception:
                install_path = None
            if not install_path or not os.path.isdir(str(install_path)):
                try:
                    del self.registry[key]
                    changed = True
                except Exception:
                    pass

        if changed:
            self._save_registry()

    def scan_zips(self) -> List[str]:
        """Scans the zips directory for new packages."""
        return glob.glob(os.path.join(self.config.zips_dir, "*.zip"))

    def validate_package(self, zip_path: str) -> Manifest:
        """Validates the structure of a zip package."""
        if not zipfile.is_zipfile(zip_path):
            raise InvalidZipError(f"Not a valid zip file: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                namelist = []
                for info in z.infolist():
                    name = info.filename
                    # Try to decode if it looks garbled
                    try:
                        if info.flag_bits & 0x800:
                            pass
                        else:
                            raw = name.encode('cp437')
                            name = raw.decode('gbk')
                    except Exception:
                        pass
                    namelist.append(name)
                
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
                     # Warn but allow if using internal python runtime which might not need wheels?
                     # No, we usually need wheels for adapter.
                     # But new spec might allow pure python with embedded deps?
                     # For now, keep it mandatory but maybe relax for specific cases.
                     # raise WheelsMissingError("wheels/ directory missing")
                     pass

                # 3. Check for bundled python interpreter
                internal_python_path = None
                
                env_config_path = None
                env_config_data = None
                
                for n in namelist:
                    if n.endswith(".procvision_env.json"):
                        try:
                            with z.open(n) as f:
                                env_config_data = json.load(f)
                                logger.info(f"Found .procvision_env.json at {n}")
                                break # Found it
                        except Exception as e:
                            logger.warning(f"Failed to read {n}: {e}")
                
                if not env_config_data:
                     logger.info(".procvision_env.json not found in zip.")

                # Prefer python_runtime by directly locating python executable inside it.
                def _find_python_runtime_root() -> Optional[str]:
                    best_root = None
                    best_score = None
                    for n in namelist:
                        nl = str(n).replace("\\", "/").lower()
                        if "python_runtime/" not in nl:
                            continue
                        if not (nl.endswith("/python.exe") or nl.endswith("/scripts/python.exe") or nl.endswith("/bin/python")):
                            continue
                        parts = str(n).replace("\\", "/").split("/")
                        try:
                            idx = parts.index("python_runtime")
                        except ValueError:
                            try:
                                idx = [p.lower() for p in parts].index("python_runtime")
                            except ValueError:
                                continue
                        root = "/".join(parts[: idx + 1]).strip("/")
                        if not root:
                            continue
                        if nl.endswith("/python_runtime/python.exe"):
                            score = 0
                        elif nl.endswith("/python_runtime/scripts/python.exe"):
                            score = 1
                        else:
                            score = 2
                        if best_score is None or score < best_score or (score == best_score and len(root) < len(best_root or "")):
                            best_root = root
                            best_score = score
                            if score == 0:
                                break
                    return best_root

                internal_python_path = _find_python_runtime_root()
                
                # Read manifest content (using original info)
                zip_filename = os.path.basename(zip_path)
                if not zip_filename.lower().endswith(".zip"):
                    raise InvalidZipError(f"Not a zip file: {zip_path}")

                base = zip_filename[:-4]
                if "-" not in base:
                    raise InvalidZipError(f"Zip filename must include version: <name>-<version>.zip, got '{zip_filename}'")

                parsed_name, parsed_version = base.rsplit("-", 1)
                if not parsed_name or not parsed_version:
                    raise InvalidZipError(f"Zip filename must include version: <name>-<version>.zip, got '{zip_filename}'")

                manifest: Manifest = {
                    "name": parsed_name,
                    "version": parsed_version,
                    "entry_point": "",
                    "supported_pids": [],
                    "description": None,
                    "python_version": None
                }

                try:
                    if manifest_path_corrected:
                        with z.open(manifest_path_corrected) as mf:
                            raw_manifest = json.load(mf) or {}
                        if isinstance(raw_manifest, dict):
                            if raw_manifest.get("entry_point"):
                                manifest["entry_point"] = str(raw_manifest.get("entry_point")).strip()
                            spids = raw_manifest.get("supported_pids", []) or []
                            manifest["supported_pids"] = [str(p).strip() for p in spids if str(p).strip()]
                            if raw_manifest.get("description") is not None:
                                manifest["description"] = raw_manifest.get("description")
                            if raw_manifest.get("python_version") is not None:
                                manifest["python_version"] = raw_manifest.get("python_version")
                except Exception as e:
                    logger.warning(f"Failed to read manifest.json from zip: {e}")

                manifest["_internal_root"] = algo_root_corrected
                manifest["_internal_wheels_path"] = wheels_path_corrected
                manifest["_internal_python_path"] = internal_python_path
                manifest["_needs_encoding_fix"] = True
                if env_config_data:
                    manifest["_env_config"] = env_config_data
                return manifest
        except RunnerError:
            raise
        except Exception as e:
            raise InvalidZipError(f"Validation failed: {str(e)}")

    def install_package(self, zip_path: str, force: bool = False, progress_callback=None) -> RegistryEntry:
        """Installs a package from a zip file."""
        if progress_callback:
            progress_callback.emit(0)
        manifest = self.validate_package(zip_path)
        name = manifest["name"]
        version = manifest["version"]
        algo_root = manifest.get("_internal_root", "")
        wheels_internal_path = manifest.get("_internal_wheels_path", "wheels")
        internal_python_path = manifest.get("_internal_python_path")
        needs_fix = manifest.get("_needs_encoding_fix", False)
        env_config = manifest.get("_env_config")
        
        key = f"{name}:{version}"

        if key in self.registry and not force:
            logger.info(f"Package {key} already installed.")
            return self.registry[key]

        install_dir = os.path.join(self.config.deployed_dir, f"{name}-{version}")
        if os.path.exists(install_dir):
            if force:
                shutil.rmtree(install_dir)
            else:
                logger.warning(f"Installation directory exists but not in registry: {install_dir}")

        try:
            # 1. Unzip with encoding fix
            os.makedirs(install_dir, exist_ok=True)
            self._extract_zip_with_progress(
                zip_path,
                install_dir,
                bool(needs_fix),
                progress_callback=progress_callback,
                start_percent=0,
                end_percent=70,
            )

            # 2. Create venv using host Python 3.12 and install dependencies from bundled wheels (offline).
            if progress_callback:
                progress_callback.emit(72)

            env_dir_name = "__procvision_env"
            venv_dir = os.path.join(install_dir, env_dir_name)
            try:
                shutil.rmtree(venv_dir, ignore_errors=True)
            except Exception:
                pass

            def _detect_python_major_minor(python_exe: str) -> Optional[str]:
                try:
                    r = subprocess.run(
                        [python_exe, "-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if r.returncode != 0:
                        return None
                    return str((r.stdout or "").strip() or "")
                except Exception:
                    return None

            required_py = "3.12"
            host_python = None
            if getattr(sys, "frozen", False):
                app_root = os.path.dirname(sys.executable)
                bundled_candidates = [
                    os.path.join(app_root, "_internal", "runtime", "python", "python.exe"),
                    os.path.join(app_root, "runtime", "python", "python.exe"),
                ]
                for c in bundled_candidates:
                    if os.path.exists(c) and _detect_python_major_minor(c) == required_py:
                        host_python = c
                        break
                if not host_python:
                    python_which = shutil.which("python")
                    if python_which and _detect_python_major_minor(python_which) == required_py:
                        host_python = python_which
            else:
                if _detect_python_major_minor(sys.executable) == required_py:
                    host_python = sys.executable

            if not host_python:
                raise InstallFailedError(f"Python {required_py} runtime not found. Please install Python {required_py} or bundle it with the app.")

            try:
                subprocess.run(
                    [host_python, "-m", "venv", venv_dir],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            except subprocess.CalledProcessError as e:
                raise InstallFailedError(f"Venv create failed: {(e.stderr or e.stdout or '').strip()}")

            if os.name == "nt":
                python_cmd = os.path.join(venv_dir, "Scripts", "python.exe")
                python_rel_path = f"{env_dir_name}/Scripts/python.exe"
            else:
                python_cmd = os.path.join(venv_dir, "bin", "python")
                python_rel_path = f"{env_dir_name}/bin/python"

            wheels_dir = os.path.join(install_dir, wheels_internal_path)
            requirements_path = os.path.join(install_dir, algo_root, "requirements.txt")

            if not os.path.isdir(wheels_dir):
                raise InstallFailedError(f"Wheels directory missing: {wheels_dir}")
            if not os.path.exists(requirements_path):
                raise InstallFailedError(f"requirements.txt missing: {requirements_path}")

            subprocess_env = os.environ.copy()
            for k in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
                subprocess_env.pop(k, None)
            subprocess_env["PYTHONNOUSERSITE"] = "1"
            subprocess_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

            try:
                subprocess.run(
                    [python_cmd, "-m", "ensurepip", "--upgrade"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=subprocess_env,
                    cwd=venv_dir,
                )
            except Exception:
                pass

            try:
                subprocess.run(
                    [
                        python_cmd,
                        "-m",
                        "pip",
                        "install",
                        "--no-index",
                        "--find-links",
                        wheels_dir,
                        "-r",
                        requirements_path,
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=subprocess_env,
                    cwd=venv_dir,
                )
            except subprocess.CalledProcessError as e:
                raise InstallFailedError(f"Pip install failed: {(e.stderr or e.stdout or '').strip()}")

            if progress_callback:
                progress_callback.emit(86)

            # 4. Register
            if progress_callback:
                progress_callback.emit(98)
            entry: RegistryEntry = {
                "name": name,
                "version": version,
                "supported_pids": manifest["supported_pids"],
                "state": PackageState.INSTALLED,
                "created_at": time.time(),
                "install_path": install_dir,
                "working_dir": os.path.join(install_dir, algo_root).replace("\\", "/"), # Actual algo root
                "python_rel_path": python_rel_path # Relative path to python executable
            }

            self.registry[key] = entry
            try:
                self._save_registry()
            except Exception:
                try:
                    del self.registry[key]
                except Exception:
                    pass
                raise
            logger.info(f"Package {key} installed successfully.")
            if progress_callback:
                progress_callback.emit(100)
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
        pid = str(pid).strip()
        supported = [str(x).strip() for x in (package.get("supported_pids") or []) if str(x).strip()]
        package["supported_pids"] = supported
        if pid not in supported:
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
            deployed_dir_new = os.path.join(self.config.deployed_dir, f"{name}-{version}")
            deployed_dir_old = os.path.join(self.config.deployed_dir, name, version)
            install_path = None
            if os.path.isdir(deployed_dir_new):
                install_path = deployed_dir_new
            elif os.path.isdir(deployed_dir_old):
                install_path = deployed_dir_old
            if not install_path:
                raise RunnerError(f"Package {key} not installed", "2005")

            for mapping_file in glob.glob(os.path.join(self.config.active_dir, "*.json")):
                try:
                    with open(mapping_file, "r") as f:
                        mapping = json.load(f) or {}
                    if mapping.get("name") == name and mapping.get("version") == version:
                        os.remove(mapping_file)
                except Exception:
                    pass

            try:
                shutil.rmtree(install_path)
            except Exception as e:
                logger.error(f"Failed to remove directory {install_path}: {e}")

            try:
                self._reconcile_registry_with_deployed()
            except Exception:
                pass
            return

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
