import os
import shutil
import logging
import zipfile
import json
import time
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtCore import QObject, Signal, QThread

from src.runner.manager import PackageManager
from src.runner.config import default_config, RunnerConfig

logger = logging.getLogger(__name__)

class WorkerSignals(QObject):
    progress = Signal(int)
    finished = Signal(bool, str) # success, message

class AsyncWorker(QThread):
    def __init__(self, task: Callable, signals: WorkerSignals, *args, **kwargs):
        super().__init__()
        self.task = task
        self.signals = signals
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.task(self.signals.progress, *self.args, **self.kwargs)
            self.signals.finished.emit(True, "Success")
        except Exception as e:
            logger.error(f"Task failed: {e}")
            self.signals.finished.emit(False, str(e))

class AlgorithmManager:
    """
    Manages algorithm lifecycle, bridging Mock Server and Local Runner.
    """
    
    def __init__(self, runner_config: RunnerConfig = default_config):
        self.package_manager = PackageManager(runner_config)
        self.runner_config = runner_config
        
        # MOCK SERVER DATA
        self.mock_server_data = [
            {
                "id": 1,
                "name": "Edge Detection Standard",
                "version": "2.1.0",
                "description": "Canny边缘检测算法，用于零件边缘识别",
                "size": "1.2 MB",
                "last_updated": "2024-11-05",
                "type": "opencv",
                "type_label": "OpenCV",
                "type_icon": "🖥️",
                "minio_url": "mock://edge-detection-v2.1.0.zip",
                "steps": 2
            },
            {
                "id": 2,
                "name": "PCB Defect Detection",
                "version": "5.0.2",
                "description": "YOLOv8缺陷检测模型，识别PCB焊接缺陷",
                "size": "45.6 MB",
                "last_updated": "2024-11-03",
                "type": "yolo",
                "type_label": "YOLO",
                "type_icon": "🧠",
                "minio_url": "mock://pcb-defect-v5.0.2.zip",
                "steps": 1
            }
        ]

    def get_all_algorithms(self) -> List[Dict[str, Any]]:
        """
        Returns a unified list of algorithms with status (REMOTE_ONLY, DOWNLOADED, DEPLOYED).
        """
        # 1. Get Server List
        server_map = {f"{item['name']}:{item['version']}": item for item in self.mock_server_data}
        
        # 2. Scan Downloaded Zips
        downloaded_zips = self.package_manager.scan_zips()
        downloaded_map = {}
        for zip_path in downloaded_zips:
            try:
                # Need to read manifest to identify name/version
                with zipfile.ZipFile(zip_path, 'r') as z:
                    namelist = z.namelist()
                    manifest_path = None
                    # Search for manifest.json in any directory
                    for name in namelist:
                        if name.endswith("manifest.json"):
                            manifest_path = name
                            break
                    
                    if not manifest_path:
                        continue

                    with z.open(manifest_path) as f:
                        m = json.load(f)
                        key = f"{m['name']}:{m['version']}"
                        downloaded_map[key] = {"path": zip_path, "manifest": m}
            except Exception:
                continue

        # 3. Get Deployed (Registry)
        registry = self.package_manager.registry
        
        # 4. Merge
        unified_list = []
        all_keys = set(server_map.keys()) | set(downloaded_map.keys()) | set(registry.keys())
        
        for key in all_keys:
            # Base info
            info = {
                "id": 0, # Generate or use server ID
                "name": key.split(":")[0],
                "version": key.split(":")[1],
                "status": "remote_only", # Default
                "source": "server",
                "local_path": None,
                "description": "",
                "size": "Unknown",
                "last_updated": "Unknown",
                "type_label": "Unknown",
                "type_icon": "📦"
            }
            
            # Fill from Server
            if key in server_map:
                s_item = server_map[key]
                info.update(s_item)
                info["source"] = "server"
                
            # Fill from Local Zip (Overrides description if local-only)
            if key in downloaded_map:
                d_item = downloaded_map[key]
                info["local_path"] = d_item["path"]
                info["status"] = "downloaded"
                
                # Get Zip Size
                try:
                    size_bytes = os.path.getsize(d_item["path"])
                    info["size"] = f"{size_bytes / 1024 / 1024:.1f} MB"
                except:
                    pass

                if key not in server_map:
                    info["source"] = "local"
                    info["description"] = d_item["manifest"].get("description", "Local Package")
                    info["name"] = d_item["manifest"].get("name") # Ensure correct casing
                    # Use file modification time as imported time for local packages
                    try:
                        mtime = os.path.getmtime(d_item["path"])
                        # Format as YYYY-MM-DD
                        import datetime
                        info["last_updated"] = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                    except:
                        pass
            
            # Check Registry (Overrides status)
            if key in registry:
                info["status"] = "deployed"
                # If deployed but local source (and not in downloaded_map for some reason, though it should be),
                # we might miss size/time if zip is gone.
                # But typically zip stays.
                
            # Status Label Mapping
            status_labels = {
                "remote_only": "未下载",
                "downloaded": "待部署",
                "deployed": "已部署"
            }
            info["status_label"] = status_labels.get(info["status"], info["status"])
            
            unified_list.append(info)
            
        return sorted(unified_list, key=lambda x: x["name"])

    def download_algorithm(self, progress_callback, name: str, version: str):
        """Mock download task."""
        # Find URL (mock)
        # In real world, use self.server_map to get URL
        
        # Simulate Progress
        for i in range(0, 101, 10):
            time.sleep(0.2) # 2 seconds total
            progress_callback.emit(i)
            
        # Copy template zip to zips_dir
        # Assuming we have a template in tests/assets/template_algo.zip
        # And we need to patch the manifest inside to match requested name/version
        # For simplicity, we just copy the template and don't patch, 
        # BUT the Runner Manager validates manifest. 
        # So we MUST patch manifest or the subsequent deploy will fail validation if names mismatch.
        # Or we rely on the template having "mock-algo" and we only request "mock-algo".
        # But UI requests "Edge Detection Standard".
        # So we must create a valid zip dynamically.
        
        target_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")
        
        # Create Zip dynamically
        manifest = {
            "name": name,
            "version": version,
            "entry_point": "procvision_algorithm_sdk.adapter",
            "supported_pids": ["A01", "A02"],
            "description": f"Downloaded {name}",
            "python_version": "3.10"
        }
        
        # We need wheels. We can borrow from tests/assets/wheels if exists, or create empty dummy wheels?
        # Runner manager checks for 'wheels/' dir existence.
        
        try:
            with zipfile.ZipFile(target_path, 'w') as z:
                z.writestr("manifest.json", json.dumps(manifest))
                z.writestr("requirements.txt", "numpy")
                # Create dummy wheel file to satisfy structure
                z.writestr("wheels/dummy.whl", "") 
        except Exception as e:
            raise Exception(f"Failed to create mock zip: {e}")

    def deploy_algorithm(self, progress_callback, name: str, version: str):
        """Deploy task."""
        # Find zip
        zip_path = None
        candidates = self.package_manager.scan_zips()
        for p in candidates:
            # More robust matching: Check manifest inside zip
            try:
                with zipfile.ZipFile(p, 'r') as z:
                    namelist = z.namelist()
                    manifest_path = None
                    for n in namelist:
                        if n.endswith("manifest.json"):
                            manifest_path = n
                            break
                    
                    if manifest_path:
                        with z.open(manifest_path) as f:
                            m = json.load(f)
                            if m.get("name") == name and m.get("version") == version:
                                zip_path = p
                                break
            except:
                continue
        
        if not zip_path:
            # Fallback for exact match if constructed above (legacy behavior)
            zip_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")
        
        if not os.path.exists(zip_path):
            raise Exception(f"Zip file not found for {name} {version}")

        progress_callback.emit(10)
        # Call Manager (Blocking)
        # We wrap it to emit progress (fake progress for the blocking call)
        self.package_manager.install_package(zip_path, force=True)
        progress_callback.emit(100)

    def import_local_algorithm(self, src_path: str):
        """Import local zip."""
        if not os.path.exists(src_path):
            raise Exception("Source file not found")
            
        # Validate it's a zip and has manifest
        with zipfile.ZipFile(src_path, 'r') as z:
            namelist = z.namelist()
            manifest_path = None
            
            # Search for manifest.json in any directory
            for name in namelist:
                if name.endswith("manifest.json"):
                    manifest_path = name
                    break
            
            if not manifest_path:
                raise Exception("Invalid package: manifest.json missing")
                
            with z.open(manifest_path) as f:
                m = json.load(f)
                name = m.get("name")
                version = m.get("version")
        
        target_name = f"{name}-{version}.zip"
        target_path = os.path.join(self.runner_config.zips_dir, target_name)
        
        shutil.copy2(src_path, target_path)

    def undeploy_algorithm(self, name: str, version: str):
        self.package_manager.uninstall_package(name, version)

    def delete_package(self, name: str, version: str):
        self.package_manager.delete_zip(name, version)
