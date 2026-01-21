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

                # Heuristic 1: Explicit 'python_runtime' directory (Preferred)
                has_python_runtime = False
                for name in namelist:
                    if name.startswith("python_runtime/") or "python_runtime/" in name:
                        has_python_runtime = True
                        break
                
                if has_python_runtime:
                    for name in namelist:
                        if "python_runtime" in name:
                            if name.lower().endswith("/python.exe") or name.lower() == "python.exe":
                                 internal_python_path = os.path.dirname(name)
                                 break
                            if name.endswith("/bin/python"):
                                 internal_python_path = os.path.dirname(os.path.dirname(name))
                                 break
                
                # Heuristic 2: Scan for any python executable
                if not internal_python_path:
                    for name in namelist:
                        if name.lower().endswith("/python.exe") or name.lower() == "python.exe":
                             internal_python_path = os.path.dirname(name)
                             break
                        if name.endswith("/bin/python"):
                             internal_python_path = os.path.dirname(os.path.dirname(name))
                             break
                
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
        env_dir_name = "_env"

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

            # 2. Create venv or conda env
            if progress_callback:
                progress_callback.emit(72)
            venv_dir = os.path.join(install_dir, env_dir_name)
            python_rel_path = ""
            
            # Priority 1: Use Bundled Python Interpreter if available
            if internal_python_path:
                logger.info(f"Found bundled python interpreter at {internal_python_path}")
                # Resolve absolute path to the bundled python executable
                # Note: internal_python_path is relative to install_dir
                
                # We need to find the executable path inside
                bundled_python_dir = os.path.join(install_dir, internal_python_path)
                
                # Check if it is a venv (contains pyvenv.cfg)
                is_bundled_venv = os.path.exists(os.path.join(bundled_python_dir, "pyvenv.cfg"))
                
                if os.name == 'nt':
                    bundled_python_exe = os.path.join(bundled_python_dir, "python.exe")
                    # Try Scripts/python.exe if root one doesn't exist (common in venv)
                    if not os.path.exists(bundled_python_exe):
                         bundled_python_exe = os.path.join(bundled_python_dir, "Scripts", "python.exe")
                else:
                    bundled_python_exe = os.path.join(bundled_python_dir, "bin", "python")
                
                if os.path.exists(bundled_python_exe):
                    logger.info(f"Using bundled python: {bundled_python_exe}")
                    
                    if is_bundled_venv:
                        logger.info("Bundled python is a venv. Using it directly.")
                        # Use the bundled dir as venv_dir
                        venv_dir = bundled_python_dir
                        
                        # Set paths
                        if os.name == 'nt':
                            python_cmd = bundled_python_exe
                            pip_cmd = os.path.join(venv_dir, "Scripts", "pip.exe")
                            # Calculate relative path from install_dir
                            # internal_python_path might be "python_runtime"
                            # We need "python_runtime/Scripts/python.exe"
                            # But bundled_python_exe is absolute.
                            python_rel_path = os.path.relpath(bundled_python_exe, install_dir).replace("\\", "/")
                        else:
                            python_cmd = bundled_python_exe
                            pip_cmd = os.path.join(venv_dir, "bin", "pip")
                            python_rel_path = os.path.relpath(bundled_python_exe, install_dir).replace("\\", "/")
                        
                        # Skip creation
                        target_py_version = None
                        
                    else:
                        # Not a venv (e.g. base python), create new venv using it
                        # Verify it runs
                        try:
                             subprocess.check_call([bundled_python_exe, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except Exception as e:
                             logger.warning(f"Bundled python check failed: {e}. Fallback to auto-detection.")
                             internal_python_path = None # Disable bundled logic
                        else:
                             # Create venv using this python
                             logger.info(f"Creating venv using bundled python...")
                             subprocess.check_call([bundled_python_exe, "-m", "venv", venv_dir])
                             
                             # Set paths for venv
                             if os.name == 'nt':
                                 python_cmd = os.path.join(venv_dir, "Scripts", "python.exe")
                                 pip_cmd = os.path.join(venv_dir, "Scripts", "pip.exe")
                                 python_rel_path = f"{env_dir_name}/Scripts/python.exe"
                             else:
                                 python_cmd = os.path.join(venv_dir, "bin", "python")
                                 pip_cmd = os.path.join(venv_dir, "bin", "pip")
                                 python_rel_path = f"{env_dir_name}/bin/python"
                             
                             # Skip Conda logic
                             target_py_version = None 
                else:
                     logger.warning(f"Bundled python executable not found at expected path. Fallback.")
                     internal_python_path = None

            # Fallback Logic (Conda / System or App-bundled runtime)
            if not internal_python_path:
                logger.info("Internal python interpreter NOT found. Falling back to environment detection.")
                
                # Determine target python version
                target_py_version = None
                
                # Priority 2: Check .procvision_env.json
                if env_config:
                    target_py_version = env_config.get("python_version")
                    if target_py_version:
                        logger.info(f"Using python version from .procvision_env.json: {target_py_version}")
                    else:
                        logger.warning(".procvision_env.json found but 'python_version' is missing or empty.")
                else:
                    logger.info(".procvision_env.json not found in package.")

                # Priority 3: Check manifest
                if not target_py_version:
                    target_py_version = manifest.get("python_version")
                    if target_py_version:
                         logger.info(f"Using python version from manifest.json: {target_py_version}")
                
                # Priority 4: Detect from wheels
                wheels_dir_abs = os.path.join(install_dir, wheels_internal_path)
                if not target_py_version:
                    target_py_version = self._detect_python_version(wheels_dir_abs)
                    if target_py_version:
                        logger.info(f"Detected Python version from wheels: {target_py_version}")
                
                if not target_py_version:
                    logger.warning("Could not determine target python version. Using current system python.")

                # Check if we need Conda
                use_conda = False
                conda_cmd = "conda"
                current_py = f"{sys.version_info.major}.{sys.version_info.minor}"
                
                logger.info(f"Environment Check: Target={target_py_version}, Current={current_py}")
                
                if target_py_version and target_py_version != current_py:
                    if os.name == "nt":
                        try:
                            subprocess.check_call("conda --version", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                            use_conda = True
                            logger.info(f"Target Python {target_py_version} != Current {current_py}. Using Conda.")
                        except Exception:
                            candidates = [
                                os.environ.get("CONDA_EXE"),
                                os.path.join(os.environ.get("USERPROFILE", ""), "miniconda3", "condabin", "conda.bat"),
                                os.path.join(os.environ.get("USERPROFILE", ""), "miniconda3", "Scripts", "conda.exe"),
                                os.path.join("C:\\ProgramData\\miniconda3", "condabin", "conda.bat"),
                                os.path.join("C:\\ProgramData\\miniconda3", "Scripts", "conda.exe"),
                            ]
                            for c in candidates:
                                if c and os.path.exists(c):
                                    conda_cmd = c
                                    use_conda = True
                                    logger.info(f"Detected Conda at {conda_cmd}")
                                    break
                            if not use_conda:
                                logger.warning(f"Target Python {target_py_version} requested but Conda not found. Trying venv (might fail).")
                    else:
                        try:
                            subprocess.check_call(["conda", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            use_conda = True
                            logger.info(f"Target Python {target_py_version} != Current {current_py}. Using Conda.")
                        except Exception:
                            c = os.environ.get("CONDA_EXE")
                            if c and os.path.exists(c):
                                conda_cmd = c
                                use_conda = True
                                logger.info(f"Detected Conda at {conda_cmd}")
                            else:
                                logger.warning(f"Target Python {target_py_version} requested but Conda not found. Trying venv (might fail).")

                # Priority: Use app-bundled runtime if present (PyInstaller one-dir)
                packaged_python_exe = None
                try:
                    if getattr(sys, "frozen", False):
                        app_root = os.path.dirname(sys.executable)
                        candidates = [
                            os.path.join(app_root, "_internal", "runtime", "python", "python.exe"),
                            os.path.join(app_root, "runtime", "python", "python.exe"),
                            os.path.join(app_root, "_internal", "runtime", "venv", "Scripts", "python.exe"),
                            os.path.join(app_root, "runtime", "venv", "Scripts", "python.exe"),
                        ]
                        for p in candidates:
                            if os.path.exists(p):
                                packaged_python_exe = p
                                break
                        if packaged_python_exe:
                            logger.info(f"Using app-bundled python runtime: {packaged_python_exe}")
                            python_cmd = packaged_python_exe
                            # Store absolute path so process can use it
                            python_rel_path = os.path.abspath(packaged_python_exe).replace("\\", "/")
                except Exception:
                    packaged_python_exe = None
                
                if packaged_python_exe:
                    pass
                elif use_conda:
                    logger.info(f"Creating Conda env at {venv_dir} with python={target_py_version}...")
                    try:
                        def _run_conda(args: list[str]) -> subprocess.CompletedProcess:
                            conda_path = conda_cmd
                            conda_path_l = str(conda_path or "").lower()
                            if os.name == "nt" and conda_path_l.endswith((".bat", ".cmd")):
                                joined = " ".join([f"\"{a}\"" if (" " in a or "\t" in a) else a for a in args])
                                return subprocess.run(
                                    ["cmd.exe", "/d", "/s", "/c", f'call "{conda_path}" {joined}'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    encoding="utf-8",
                                    errors="replace",
                                )
                            return subprocess.run(
                                [conda_path, *args],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding="utf-8",
                                errors="replace",
                            )

                        r = _run_conda(["create", "-p", venv_dir, f"python={target_py_version}", "-y"])
                        if r.returncode != 0:
                            raise InstallFailedError(
                                f"Conda create failed (rc={r.returncode}): {(r.stderr or r.stdout).strip()}"
                            )
                    except InstallFailedError:
                        logger.error("Conda create failed. Check conda config / permissions / existing prefix.")
                        raise
                    except Exception as e:
                        logger.error("Conda create failed. Check conda config / permissions / existing prefix.")
                        raise InstallFailedError(f"Conda create failed: {e}")
                    
                    # Resolve paths for Conda (Windows)
                    # In prefix env: python.exe is at root, pip is in Scripts
                    if os.name == 'nt':
                        python_cmd = os.path.join(venv_dir, "python.exe")
                        python_rel_path = f"{env_dir_name}/python.exe"
                    else:
                        python_cmd = os.path.join(venv_dir, "bin", "python")
                        python_rel_path = f"{env_dir_name}/bin/python"

                else:
                    logger.info(f"Creating venv at {venv_dir}...")
                    if getattr(sys, "frozen", False):
                        try:
                            python_which = shutil.which("python")
                            if python_which:
                                subprocess.check_call([python_which, "-m", "venv", venv_dir])
                            else:
                                raise FileNotFoundError("python command not found in PATH")
                        except Exception as e:
                            if use_conda and conda_cmd:
                                try:
                                    if os.name == "nt":
                                        cmd = f'\"{conda_cmd}\" create -p \"{venv_dir}\" python={target_py_version or current_py} -y'
                                        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", shell=True)
                                        if r.returncode != 0:
                                            raise InstallFailedError(f"Conda create failed: {r.stderr.strip() or r.stdout.strip()}")
                                    else:
                                        cmd = [conda_cmd, "create", "-p", venv_dir, f"python={target_py_version or current_py}", "-y"]
                                        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
                                        if r.returncode != 0:
                                            raise InstallFailedError(f"Conda create failed: {r.stderr.strip() or r.stdout.strip()}")
                                except InstallFailedError:
                                    raise
                                except Exception as e2:
                                    raise InstallFailedError(f"Conda create failed: {e2}")
                            else:
                                raise InstallFailedError(f"Python runtime not found. Include python_runtime in package or install Python: {e}")
                    else:
                        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
                    
                    if os.name == 'nt':
                        python_cmd = os.path.join(venv_dir, "Scripts", "python.exe")
                        python_rel_path = f"{env_dir_name}/Scripts/python.exe"
                    else:
                        python_cmd = os.path.join(venv_dir, "bin", "python")
                        python_rel_path = f"{env_dir_name}/bin/python"

            # 3. Install dependencies
            # Determine pip path in venv
            if progress_callback:
                progress_callback.emit(86)

            # Resolve actual paths on disk
            wheels_dir = os.path.join(install_dir, wheels_internal_path)
            requirements_path = os.path.join(install_dir, algo_root, "requirements.txt")

            logger.info(f"Installing dependencies for {key}...")
            logger.info(f"Wheels dir: {wheels_dir}")
            logger.info(f"Requirements: {requirements_path}")
            
            if python_cmd:
                try:
                    subprocess.run(
                        [python_cmd, "-m", "ensurepip", "--upgrade"],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                except Exception:
                    pass
            cmd = [
                python_cmd, "-m", "pip", "install",
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
                # If pip is missing in conda-created env, install pip via conda then retry
                try:
                    if 'not found' in (e.stderr or '').lower() or 'no module named pip' in (e.stderr or '').lower():
                        if 'use_conda' in locals() and use_conda:
                            logger.info("Installing pip into conda prefix environment...")
                            if os.name == "nt":
                                conda_path = conda_cmd
                                conda_path_l = str(conda_path or "").lower()
                                if conda_path_l.endswith((".bat", ".cmd")):
                                    ccmd = f'call "{conda_path}" install -p "{venv_dir}" pip -y'
                                    subprocess.check_call(
                                        ["cmd.exe", "/d", "/s", "/c", ccmd],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE,
                                    )
                                else:
                                    subprocess.check_call(
                                        [conda_path, "install", "-p", venv_dir, "pip", "-y"],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE,
                                    )
                            else:
                                ccmd = [conda_cmd, "install", "-p", venv_dir, "pip", "-y"]
                                subprocess.check_call(ccmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                            subprocess.run(
                                cmd, 
                                check=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True,
                                encoding='utf-8',
                                errors='replace'
                            )
                            logger.info("Pip install succeeded after installing pip via conda.")
                        else:
                            raise InstallFailedError(f"Pip install failed and conda not available: {e.stderr}")
                    else:
                        raise InstallFailedError(f"Pip install failed: {e.stderr}")
                except subprocess.CalledProcessError as e2:
                    logger.error("Conda pip install failed.")
                    raise InstallFailedError(f"Conda pip install failed: {e2}")

            # 4. Register
            if progress_callback:
                progress_callback.emit(98)
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
