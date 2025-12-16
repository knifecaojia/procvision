import threading
import uuid
import time
import logging
from typing import Dict, Any, Optional, Union
import numpy as np

from .config import RunnerConfig, default_config
from .manager import PackageManager
from .process import AlgorithmProcess
from .shared_memory import write_image_to_shared_memory, clear_shared_memory
from .types import RegistryEntry, CallRequest, CallResult
from .exceptions import InvalidPidError, RunnerError

logger = logging.getLogger(__name__)

class RunnerEngine:
    def __init__(self, config: RunnerConfig = default_config):
        self.config = config
        self.package_manager = PackageManager(self.config)
        self.processes: Dict[str, AlgorithmProcess] = {} # key="name:version"
        self._proc_lock = threading.Lock()

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
            import json
            try:
                with open(f"{entry['install_path']}/manifest.json") as f:
                    manifest = json.load(f)
                    entry_point = manifest["entry_point"]
            except Exception as e:
                raise RunnerError(f"Failed to read manifest for {key}: {e}", "2002")

            proc = AlgorithmProcess(entry['install_path'], entry_point, self.config)
            proc.start()
            self.processes[key] = proc
            return proc

    def execute_flow(self, pid: str, image: Union[bytes, np.ndarray], context: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Executes the full detection flow (Pre -> Execute).
        """
        # 1. Resolve Package
        pkg_entry = self.package_manager.get_active_package(pid)
        if not pkg_entry:
            raise InvalidPidError(f"PID {pid} not mapped to any active package")

        # 2. Prepare Resources
        session_id = f"sid-{uuid.uuid4()}"
        shared_mem_id = f"shm-{session_id}"
        
        # Write Image
        try:
            write_image_to_shared_memory(shared_mem_id, image)
        except Exception as e:
            raise RunnerError(f"Failed to write shared memory: {e}", "1002")

        proc = self._get_or_create_process(pkg_entry)

        # Image Meta
        height, width = 0, 0
        if isinstance(image, np.ndarray):
            height, width = image.shape[:2]
        # For bytes, we might need to parse headers or let algorithm handle it.
        # Spec says inject width/height. If bytes, we might guess or set 0?
        # SDK read_image handles 0 check.
        
        image_meta = {
            "width": width,
            "height": height,
            "timestamp_ms": int(time.time() * 1000),
            "camera_id": context.get("camera_id", "unknown"),
            "color_space": self.config.color_space_default
        }

        base_req = {
            "pid": pid,
            "session": {"id": session_id, "context": context},
            "user_params": context.get("user_params", {}),
            "shared_mem_id": shared_mem_id,
            "image_meta": image_meta
        }

        try:
            # 3. Pre-Execute
            req_pre = base_req.copy()
            req_pre.update({
                "type": "call",
                "phase": "pre",
                "step_index": 1
            })
            
            res_pre = proc.call(req_pre, self.config.pre_execute_timeout_ms)
            if res_pre["status"] != "OK":
                return res_pre # Return error immediately

            # 4. Execute
            req_exec = base_req.copy()
            req_exec.update({
                "type": "call",
                "phase": "execute",
                "step_index": 2
            })
            
            res_exec = proc.call(req_exec, self.config.execute_timeout_ms)
            return res_exec

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            if isinstance(e, RunnerError):
                return {"status": "ERROR", "error_code": e.error_code, "message": e.message}
            return {"status": "ERROR", "error_code": "9999", "message": str(e)}
        finally:
            # Cleanup
            clear_shared_memory(shared_mem_id)

    def stop_all(self):
        with self._proc_lock:
            for key, proc in self.processes.items():
                proc.stop()
            self.processes.clear()
