import os
import hashlib
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

MAX_DOWNLOAD_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0

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
            matched_zip = downloaded_map.get(expected_zip_name)

            if matched_zip:
                info["local_path"] = matched_zip["path"]
                info["status"] = "downloaded"
                try:
                    size_bytes = os.path.getsize(matched_zip["path"])
                    info["size"] = f"{size_bytes / 1024 / 1024:.1f} MB"
                    mtime = os.path.getmtime(matched_zip["path"])
                    import datetime
                    info["last_updated"] = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                except Exception:
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
        target_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")

        if os.path.exists(target_path) and not self._validate_local_zip(target_path):
            logger.info(f"Algorithm {name}:{version} already downloaded at {target_path}")
            progress_callback.emit(100)
            return

        if os.path.exists(target_path):
            logger.warning(f"Removing corrupted zip: {target_path}")
            try:
                os.remove(target_path)
            except Exception:
                pass

        server_algorithms = self.data_service.get_algorithms()
        target_algo = None
        for item in server_algorithms:
            if item.get("name") == name and item.get("version") == version:
                target_algo = item
                break

        expected_size = None
        expected_md5 = None
        if target_algo:
            raw_size = target_algo.get("size")
            if raw_size is not None:
                try:
                    expected_size = int(str(raw_size).replace("MB", "").replace("KB", "").strip()) if isinstance(raw_size, str) else int(raw_size)
                    if isinstance(raw_size, str) and "MB" in raw_size.upper():
                        expected_size = expected_size * 1024 * 1024
                    elif isinstance(raw_size, str) and "KB" in raw_size.upper():
                        expected_size = expected_size * 1024
                except Exception:
                    expected_size = None
            expected_md5 = (target_algo.get("md5") or target_algo.get("hash") or "").strip() or None

        download_url = None
        if target_algo:
            download_url = target_algo.get("url")

        if not download_url:
            repo_dir = os.path.join(os.getcwd(), "assets", "repo")
            source_zip = os.path.join(repo_dir, f"{name}-{version}.zip")
            if os.path.exists(source_zip):
                download_url = source_zip
                logger.info(f"Using local fallback: {source_zip}")

        if not download_url:
            raise Exception(f"Algorithm source not found for {name}:{version}. Please check server data or local assets.")

        last_error = None
        for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
            try:
                logger.info(f"Download attempt {attempt}/{MAX_DOWNLOAD_RETRIES} for {name}:{version}")
                self._do_download(download_url, target_path, progress_callback, expected_size)
                validation_error = self._validate_local_zip(target_path)
                if validation_error:
                    raise Exception(validation_error)
                if expected_md5:
                    self._verify_md5(target_path, expected_md5)
                logger.info(f"Download completed and verified: {target_path}")
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Download attempt {attempt} failed: {e}")
                if os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                    except Exception:
                        pass
                if attempt < MAX_DOWNLOAD_RETRIES:
                    backoff = RETRY_BACKOFF_BASE ** (attempt - 1)
                    logger.info(f"Retrying in {backoff:.1f}s...")
                    time.sleep(backoff)

        raise Exception(f"Download failed after {MAX_DOWNLOAD_RETRIES} attempts: {last_error}")

    def _do_download(self, download_url: str, target_path: str, progress_callback, expected_size: Optional[int] = None):
        tmp_path = target_path + ".download"
        try:
            if download_url.startswith("http://") or download_url.startswith("https://"):
                self._download_http(download_url, tmp_path, progress_callback)
            elif os.path.exists(download_url):
                self._copy_local(download_url, tmp_path, progress_callback)
            else:
                raise Exception(f"Download source not accessible: {download_url}")

            if expected_size is not None:
                actual_size = os.path.getsize(tmp_path)
                if actual_size != expected_size:
                    raise Exception(f"Size mismatch: expected {expected_size} bytes, got {actual_size} bytes")

            if os.path.exists(target_path):
                os.remove(target_path)
            os.replace(tmp_path, target_path)
        except Exception:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            raise

    def _download_http(self, url: str, tmp_path: str, progress_callback):
        import urllib.request
        import urllib.error
        import ssl

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        proxy_handler = urllib.request.ProxyHandler({})
        https_handler = urllib.request.HTTPSHandler(context=ssl_ctx)
        opener = urllib.request.build_opener(proxy_handler, https_handler)

        try:
            response = opener.open(url, timeout=120)
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024

            with open(tmp_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = min(99, int(downloaded * 100 / total_size))
                        progress_callback.emit(percent)

            progress_callback.emit(100)
            logger.info(f"HTTP download completed: {tmp_path} ({downloaded} bytes)")
        except Exception as e:
            logger.error(f"HTTP download failed: {e}")
            raise Exception(f"HTTP download failed: {e}")

    def _copy_local(self, src_path: str, tmp_path: str, progress_callback):
        total_size = os.path.getsize(src_path)
        copied = 0
        chunk_size = 1024 * 1024

        with open(src_path, "rb") as src, open(tmp_path, "wb") as dst:
            while True:
                chunk = src.read(chunk_size)
                if not chunk:
                    break
                dst.write(chunk)
                copied += len(chunk)
                percent = int((copied / total_size) * 100)
                progress_callback.emit(percent)
                time.sleep(0.01)

        logger.info(f"Local copy completed: {tmp_path} ({copied} bytes)")

    @staticmethod
    def _validate_local_zip(zip_path: str) -> Optional[str]:
        if not os.path.exists(zip_path):
            return "Downloaded file not found"
        if os.path.getsize(zip_path) < 64:
            return "Downloaded file is too small to be a valid ZIP"
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                bad = z.testzip()
                if bad is not None:
                    return f"Corrupt entry in ZIP archive: {bad}"
                namelist = z.namelist()
                has_manifest = any(n.endswith("manifest.json") for n in namelist)
                if not has_manifest:
                    return "Invalid algorithm package: manifest.json not found in ZIP"
            return None
        except zipfile.BadZipFile:
            return "Downloaded file is not a valid ZIP archive"
        except Exception as e:
            return f"ZIP validation failed: {e}"

    @staticmethod
    def _verify_md5(file_path: str, expected_md5: str):
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                md5.update(chunk)
        actual = md5.hexdigest()
        if actual.lower() != expected_md5.lower():
            raise Exception(f"MD5 mismatch: expected {expected_md5}, got {actual}")
        logger.info(f"MD5 verified: {actual}")

    def deploy_algorithm(self, progress_callback, name: str, version: str):
        """Deploy task."""
        zip_path = os.path.join(self.runner_config.zips_dir, f"{name}-{version}.zip")
        if not os.path.exists(zip_path):
            raise Exception(f"Zip file not found for {name} {version}")

        progress_callback.emit(0)
        self.package_manager.install_package(zip_path, force=True, progress_callback=progress_callback)

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
