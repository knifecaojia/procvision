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
from src.services.data_service import DataService

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
        self.data_service = DataService()

    def get_all_algorithms(self) -> List[Dict[str, Any]]:
        """
        Returns a unified list of algorithms with status (REMOTE_ONLY, DOWNLOADED, DEPLOYED).
        """
        # 1. Get Server List via DataService
        server_algorithms = self.data_service.get_algorithms()
        server_map = {}
        for item in server_algorithms:
            key = f"{item['name']}:{item['version']}"
            # Map API fields to UI expected fields
            server_map[key] = {
                "id": item.get("code"),
                "name": item.get("name"),
                "version": item.get("version"),
                "description": item.get("name", "Unknown Algorithm"), # Fallback
                "size": item.get("size", "Unknown"),
                "last_updated": item.get("create_time", "Unknown"),
                "minio_url": item.get("url"),
                "type": "unknown", # Default
                "type_label": "Algorithm",
                "type_icon": "📦",
                "steps": 0 # Default
            }
        
        # 2. Scan Downloaded Zips
        downloaded_zips = self.package_manager.scan_zips()
        downloaded_map = {}
        for zip_path in downloaded_zips:
            try:
                # Optimized check: Just verify filename pattern match
                # Pattern: <name>-<version>.zip
                # This avoids expensive zip reads for every file on every refresh
                
                filename = os.path.basename(zip_path)
                if not filename.endswith(".zip"):
                    continue
                    
                base_name = filename[:-4] # Remove .zip
                
                # Split by last hyphen to separate version?
                # Or try to match against known server keys?
                # A robust way is to iterate server_map keys and see if filename matches f"{name}-{version}.zip"
                
                # We can do this reverse mapping later in step 4.
                # Here we just store available zip filenames
                
                downloaded_map[filename] = {"path": zip_path}

            except Exception:
                continue

        # 3. Get Deployed (Registry)
        registry = self.package_manager.registry
        
        # 4. Merge
        unified_list = []
        # all_keys = set(server_map.keys()) | set(downloaded_map.keys()) | set(registry.keys())
        # Strict mode: Only show algorithms from server response
        # If downloaded/deployed algorithms are not in server response, ignore them (or show as separate/unknown?)
        # User instruction: "算法列表要严格显示接口获取的算法数据"
        
        all_keys = list(server_map.keys())
        
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
            # Check if corresponding zip exists
            expected_zip_name = f"{info['name']}-{info['version']}.zip"
            
            if expected_zip_name in downloaded_map:
                d_item = downloaded_map[expected_zip_name]
                info["local_path"] = d_item["path"]
                info["status"] = "downloaded"
                
                # Get Zip Size
                try:
                    size_bytes = os.path.getsize(d_item["path"])
                    info["size"] = f"{size_bytes / 1024 / 1024:.1f} MB"
                    
                    # Update last_updated using zip modification time
                    mtime = os.path.getmtime(d_item["path"])
                    import datetime
                    info["last_updated"] = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                except:
                    pass
            
            deployed_dir_new = os.path.join(self.runner_config.deployed_dir, f"{info['name']}-{info['version']}")
            deployed_dir_old = os.path.join(self.runner_config.deployed_dir, info["name"], info["version"])

            if os.path.isdir(deployed_dir_new) or os.path.isdir(deployed_dir_old):
                info["status"] = "deployed"
                
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
        """
        Download algorithm from remote server using URL from data_service.
        """
        # 1. Get algorithm info to find the URL
        server_algorithms = self.data_service.get_algorithms()
        target_algo = None
        for item in server_algorithms:
            if item.get("name") == name and item.get("version") == version:
                target_algo = item
                break
        
        if not target_algo:
             # Fallback: Maybe it's not in the list but we know name/version?
             # Or we can't download if we don't have URL.
             # Check if we have a local mock fallback (repo)
             # This preserves local testing capability if server list is missing the item
             logger.warning(f"Algorithm {name}:{version} not found in server list. Checking local assets...")
        else:
             download_url = target_algo.get("url")
             logger.info(f"Downloading {name}:{version} from {download_url}")
             
             # If URL is a local file path (mock data might use file:// or just path)
             # Or if it's http/https, we need a real download.
             # Since we don't have requests/httpx in imports yet, let's assume we might need to add it 
             # OR if this is a POC, we might still rely on local file copy if the URL is local.
             
             # The user instruction says: "使用算法数据中给出的url 下载算法"
             # If the URL is "http://...", we need to implement HTTP download.
             # If it is "/path/to/...", we copy.
             
             # Let's try to implement a robust downloader using urllib (standard lib) or just handling local copy if it is a file path.
             
             import urllib.request
             import urllib.error
             
             target_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")
             
             if download_url and (download_url.startswith("http://") or download_url.startswith("https://")):
                 try:
                     def report_reporthook(block_num, block_size, total_size):
                        if total_size > 0:
                            percent = int((block_num * block_size * 100) / total_size)
                            # Emit progress occasionally to avoid flooding
                            if percent % 5 == 0: 
                                progress_callback.emit(percent)

                     urllib.request.urlretrieve(download_url, target_path, report_reporthook)
                     progress_callback.emit(100)
                     logger.info(f"Download completed: {target_path}")
                     return
                 except Exception as e:
                     logger.error(f"HTTP download failed: {e}")
                     raise Exception(f"Download failed: {e}")
             
             elif download_url and os.path.exists(download_url):
                 # Local file copy (Mock scenario but driven by data)
                 source_zip = download_url
                 logger.info(f"Copying from local URL: {source_zip}")
                 total_size = os.path.getsize(source_zip)
                 copied = 0
                 chunk_size = 1024 * 1024 # 1MB
                 
                 # Temp file to ensure atomicity or just simple copy
                 # But to track progress we copy manually
                 try:
                     with open(source_zip, 'rb') as src, open(target_path, 'wb') as dst:
                        while True:
                            chunk = src.read(chunk_size)
                            if not chunk:
                                break
                            dst.write(chunk)
                            copied += len(chunk)
                            percent = int((copied / total_size) * 100)
                            progress_callback.emit(percent)
                            time.sleep(0.05)
                     
                     # No size verification required for local copy as per user request
                         
                 except Exception as e:
                     # Cleanup partial
                     if os.path.exists(target_path):
                         os.remove(target_path)
                     raise e
                     
                 return

        # Fallback to local 'assets/repo' if URL download failed or URL missing
        # This keeps the previous logic as a safety net for development
        repo_dir = os.path.join(os.getcwd(), "assets", "repo")
        source_zip = os.path.join(repo_dir, f"{name}-{version}.zip")
        
        target_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")
        
        if os.path.exists(source_zip):
            logger.info(f"Simulating download by copying from {source_zip}")
            total_size = os.path.getsize(source_zip)
            copied = 0
            chunk_size = 1024 * 1024 # 1MB
            
            with open(source_zip, 'rb') as src, open(target_path, 'wb') as dst:
                while True:
                    chunk = src.read(chunk_size)
                    if not chunk:
                        break
                    dst.write(chunk)
                    copied += len(chunk)
                    percent = int((copied / total_size) * 100)
                    progress_callback.emit(percent)
                    time.sleep(0.05)
            return

        raise Exception(f"Algorithm source not found for {name}:{version}. Please check server data or local assets.")

    def deploy_algorithm(self, progress_callback, name: str, version: str):
        """Deploy task."""
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

    def check_deployment_status(self, name: str, version: str) -> Dict[str, Any]:
        """
        Check if an algorithm is deployed.
        """
        key = f"{name}:{version}"

        deployed_dir_new = os.path.join(self.runner_config.deployed_dir, f"{name}-{version}")
        deployed_dir_old = os.path.join(self.runner_config.deployed_dir, name, version)
        if os.path.isdir(deployed_dir_new) or os.path.isdir(deployed_dir_old):
            return {"status": "deployed", "label": "已部署", "deployed": True}

        zip_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")
        if os.path.exists(zip_path):
            return {"status": "downloaded", "label": "待部署", "deployed": False}

        return {"status": "remote_only", "label": "未下载", "deployed": False}
