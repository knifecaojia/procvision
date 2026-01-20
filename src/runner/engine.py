import threading
import uuid
import time
import logging
import os
from typing import Dict, Any, Optional, Union
import numpy as np
import json

from .config import RunnerConfig, default_config
from .manager import PackageManager
from .process import AlgorithmProcess
from .shared_memory import write_image_to_shared_memory, clear_shared_memory
from .types import RegistryEntry, CallRequest, CallResult
from .exceptions import InvalidPidError, RunnerError

logger = logging.getLogger(__name__)

class RunnerEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(RunnerEngine, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: RunnerConfig = default_config):
        if getattr(self, "_initialized", False):
             return
        self.config = config
        self.package_manager = PackageManager(self.config)
        self.processes: Dict[str, AlgorithmProcess] = {} # key="name:version"
        self._proc_lock = threading.Lock()
        self._initialized = True

    def _get_process_key(self, entry: RegistryEntry) -> str:
        return f"{entry['name']}:{entry['version']}"

    def _get_or_create_process(self, entry: RegistryEntry) -> AlgorithmProcess:
        key = self._get_process_key(entry)
        with self._proc_lock:
            if key in self.processes:
                proc = self.processes[key]
                if proc.is_alive():
                    return proc
                else:
                    logger.warning(f"Process {key} is dead, removing.")
                    del self.processes[key]
            
            # Create new
            manifest_path = f"{entry['install_path']}/manifest.json" # Assumed
            # Actually PackageManager validates manifest, but we need entry_point.
            # We should probably read manifest again or store entry_point in RegistryEntry.
            # For now, let's read manifest quickly.
            # Note: entry['install_path'] points to root, but manifest might be in working_dir (subfolder)
            # Use working_dir to find manifest
            working_dir = entry.get('working_dir', entry['install_path'])
            manifest_path = os.path.join(working_dir, "manifest.json")
            
            def _read_manifest(p: str) -> Dict[str, Any]:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f) or {}
                except UnicodeDecodeError:
                    pass
                try:
                    with open(p, "r", encoding="utf-8-sig") as f:
                        return json.load(f) or {}
                except Exception:
                    pass
                try:
                    with open(p, "r", encoding="gbk") as f:
                        return json.load(f) or {}
                except Exception:
                    pass
                with open(p, "rb") as f:
                    raw = f.read()
                try:
                    return json.loads(raw.decode("utf-8", errors="ignore")) or {}
                except Exception:
                    return json.loads(raw.decode("latin-1")) or {}
            try:
                manifest = _read_manifest(manifest_path)
                entry_point = str(manifest.get("entry_point") or "").strip()
                if not entry_point:
                    raise RunnerError("entry_point missing", "2002")
            except Exception as e:
                try:
                    manifest = _read_manifest(os.path.join(entry['install_path'], "manifest.json"))
                    entry_point = str(manifest.get("entry_point") or "").strip()
                    if not entry_point:
                        raise RunnerError("entry_point missing", "2002")
                except Exception:
                    raise RunnerError(f"Failed to read manifest for {key}: {e}", "2002")

            python_rel_path = entry.get("python_rel_path", "")
            # Pass working_dir if available, else default to install_path
            working_dir = entry.get('working_dir', entry['install_path'])
            proc = AlgorithmProcess(entry['install_path'], entry_point, self.config, python_rel_path, working_dir)
            proc.start()
            self.processes[key] = proc
            return proc

    def get_algorithm_info(self, name: str, version: str) -> Dict[str, Any]:
        """
        Calls the 'info' phase of the algorithm to get process details (steps, etc.).
        """
        key = f"{str(name).strip()}:{str(version).strip()}"
        pkg_entry = self.package_manager.registry.get(key)
        if not pkg_entry:
            raise RunnerError(f"Algorithm {key} not installed", "2005")

        # 2. Get Process
        proc = self._get_or_create_process(pkg_entry)

        # 3. Call 'info'
        req = {
            "type": "call",
            "phase": "info",
            "session": {"id": "info-req", "context": {}},
            "user_params": {},
            "shared_mem_id": "", # Not needed for info
            "image_meta": {}
        }
        
        # Use a short timeout for info
        res = proc.call(req, 5000) 
        if res.get("status") == "OK":
            return res.get("data", {})
        else:
             logger.warning(f"Failed to get info for PID {pid}: {res.get('message')}")
             return {}

    def execute_flow(self, name: str, version: str, 
                     step_index: int, 
                     step_desc: str, 
                     cur_image: Union[bytes, np.ndarray], 
                     guide_image: Union[bytes, np.ndarray],
                     guide_info: list = [],
                     context: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Executes the detection flow (Single Execute Phase).
        """
        key = f"{str(name).strip()}:{str(version).strip()}"
        pkg_entry = self.package_manager.registry.get(key)
        if not pkg_entry:
            raise RunnerError(f"Algorithm {key} not installed", "2005")

        # 2. Prepare Resources
        req_id = str(uuid.uuid4())
        cur_shm_id = f"shm-{req_id}-cur"
        guide_shm_id = f"shm-{req_id}-guide"
        
        # Write Images
        try:
            write_image_to_shared_memory(cur_shm_id, cur_image)
            write_image_to_shared_memory(guide_shm_id, guide_image)
        except Exception as e:
            raise RunnerError(f"Failed to write shared memory: {e}", "1002")

        proc = self._get_or_create_process(pkg_entry)

        # Image Meta
        def get_meta(img, suffix):
            h, w = 0, 0
            if isinstance(img, np.ndarray):
                h, w = img.shape[:2]
            return {
                "width": w,
                "height": h,
                "timestamp_ms": int(time.time() * 1000),
                "camera_id": context.get(f"camera_id_{suffix}", "unknown"),
                "color_space": self.config.color_space_default
            }

        cur_meta = get_meta(cur_image, "cur")
        guide_meta = get_meta(guide_image, "guide")

        req_data = {
            "step_index": step_index,
            "step_desc": step_desc,
            "guide_info": guide_info,
            "cur_image_shm_id": cur_shm_id,
            "cur_image_meta": cur_meta,
            "guide_image_shm_id": guide_shm_id,
            "guide_image_meta": guide_meta
        }

        req = {
            "type": "call",
            "request_id": req_id,
            "data": req_data
        }

        try:
            # 3. Execute
            res = proc.call(req, self.config.execute_timeout_ms)
            return res

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            if isinstance(e, RunnerError):
                return {"status": "ERROR", "error_code": e.error_code, "message": e.message}
            return {"status": "ERROR", "error_code": "9999", "message": str(e)}
        finally:
            # Cleanup
            clear_shared_memory(cur_shm_id)
            clear_shared_memory(guide_shm_id)

    def stop_all(self):
        with self._proc_lock:
            for key, proc in self.processes.items():
                proc.stop()
            self.processes.clear()
