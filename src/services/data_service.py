import json
import logging
import threading
import queue
import time
import os
import random
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from .network_service import NetworkService

logger = logging.getLogger(__name__)

class DataService:
    """
    Service layer for handling data fetching and submission.
    Implements a background queue for non-blocking uploads.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.upload_queue = queue.Queue()
        self.running = True
        self.network_service = NetworkService()
        
        # Determine data paths
        # Assuming run from project root or src parent
        current_dir = Path(__file__).parent.parent.parent
        self.data_dir = current_dir / "data" / "mock"
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
        logger.info("DataService initialized with background worker")

    def _process_queue(self):
        """Background worker to process upload tasks."""
        while self.running:
            try:
                task = self.upload_queue.get(timeout=1.0)
                try:
                    self._handle_upload_task(task)
                except Exception as e:
                    logger.error(f"Error processing upload task: {e}")
                finally:
                    self.upload_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                time.sleep(1)

    def _handle_upload_task(self, task: Dict[str, Any]):
        """Simulate uploading data to server."""
        task_type = task.get("type")
        payload = task.get("payload")
        
        logger.info(f"Processing upload task: {task_type}")
        
        # Simulate network delay
        time.sleep(0.5)
        
        if task_type == "image":
            # Simulate presigned URL -> upload sequence
            file_path = payload.get("file_path")
            logger.info(f"Uploading image: {file_path}")
            # In a real app, here we would get presigned url and put file
            
        elif task_type == "step_log":
            logger.info(f"Uploading step log: {payload}")
            
        elif task_type == "result_log":
            logger.info(f"Uploading result log: {payload}")
            
        logger.info(f"Upload task completed: {task_type}")

    def get_algorithms(self) -> List[Dict[str, Any]]:
        """Fetch algorithms from server or mock data."""
        # Try network first
        try:
            response = self.network_service.get_algorithms()
            if response.get("code") == 200:
                rows = response.get("rows")
                if isinstance(rows, list):
                    return rows
                data = response.get("data")
                if isinstance(data, dict):
                    rows = data.get("rows") or data.get("list") or data.get("records")
                    if isinstance(rows, list):
                        return rows
                if isinstance(data, list):
                    return data
                raise ValueError("Unexpected algorithms response shape")
        except Exception as e:
            logger.warning(f"Network fetch failed for algorithms, falling back to mock: {e}")

        # Fallback to local file
        try:
            file_path = self.data_dir / "algorithms.json"
            if not file_path.exists():
                logger.warning(f"Algorithms mock file not found: {file_path}")
                return []
                
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load algorithms: {e}")
            return []

    def get_work_orders(self, page: int = 1, page_size: int = 10, status: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch work orders with pagination and filtering.
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            status: Filter by status code (e.g. "1", "2", "3")
        """
        # Try network first
        try:
            status_int = int(status) if status else None
            response = self.network_service.get_work_orders(page_num=page, page_size=page_size, status=status_int)
            if response.get("code") == 200:
                return {
                    "items": response.get("rows", []),
                    "total": response.get("total", 0),
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (response.get("total", 0) + page_size - 1) // page_size
                }
        except Exception as e:
            logger.warning(f"Network fetch failed for work orders, falling back to mock: {e}")

        # Fallback to local file
        try:
            file_path = self.data_dir / "work_orders.json"
            if not file_path.exists():
                # Try singular just in case
                file_path = self.data_dir / "work_order.json"
            
            if not file_path.exists():
                logger.warning(f"Work orders mock file not found: {file_path}")
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0
                }
                
            with open(file_path, "r", encoding="utf-8") as f:
                all_orders = json.load(f)

            # Filter by status if provided
            if status:
                all_orders = [
                    order for order in all_orders 
                    if str(order.get("status")) == str(status)
                ]
                
            total = len(all_orders)
            if total == 0:
                 return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0
                }

            total_pages = (total + page_size - 1) // page_size
            
            # Adjust page if out of bounds
            if page < 1: page = 1
            if page > total_pages and total_pages > 0: page = total_pages
            
            start = (page - 1) * page_size
            end = start + page_size
            items = all_orders[start:end]
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Failed to load work orders: {e}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

    def get_work_orders_online(self, page: int = 1, page_size: int = 10, status: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch tasks from network; if server returns no tasks, mock 10 tasks per API spec.
        """
        def build_empty(error: Optional[str] = None) -> Dict[str, Any]:
            payload: Dict[str, Any] = {
                "items": [],
                "total": 0,
                "page": max(1, int(page)),
                "page_size": int(page_size),
                "total_pages": 1,
            }
            if error:
                payload["error"] = error
            return payload

        try:
            status_int = int(status) if status else None
            logger.info(
                "Fetching tasks from network: page=%s page_size=%s status=%s",
                page,
                page_size,
                status_int,
            )
            response = self.network_service.get_work_orders(page_num=page, page_size=page_size, status=status_int)
            if response.get("code") == 200:
                data = response.get("data")
                rows = response.get("rows")
                total = response.get("total", 0)

                if isinstance(data, dict):
                    rows = rows if isinstance(rows, list) else (data.get("rows") or data.get("list") or data.get("records"))
                    total = total or data.get("total", 0)
                elif isinstance(data, list):
                    rows = rows if isinstance(rows, list) else data

                if not isinstance(rows, list):
                    rows = []

                if len(rows) == 0:
                    return build_empty()

                logger.info(
                    "Tasks fetched from network: count=%s total=%s page=%s page_size=%s",
                    len(rows),
                    int(total or 0),
                    page,
                    page_size,
                )
                return {
                    "items": rows,
                    "total": int(total or 0),
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (int(total or 0) + page_size - 1) // page_size if int(total or 0) else 1
                }
            logger.warning(
                "Tasks fetch failed (non-200); returning empty: code=%s msg=%s",
                response.get("code"),
                response.get("msg"),
            )
            return build_empty(response.get("msg", "Network request failed"))
        except Exception as e:
            logger.warning("Tasks fetch exception; returning empty: %s", e)
            return build_empty(str(e))

    def _generate_mock_tasks(self, count: int = 10) -> List[Dict[str, Any]]:
        algorithms = []
        try:
            algorithms = self.get_algorithms() or []
        except Exception:
            algorithms = []

        algo_ids: List[str] = []
        for a in algorithms:
            algo_id = a.get("code") or a.get("id")
            if algo_id is not None and str(algo_id).strip():
                algo_ids.append(str(algo_id).strip())
        if not algo_ids:
            algo_ids = ["ALGO-001"]

        now = datetime.datetime.now()
        seed = int(now.strftime("%Y%m%d"))
        rng = random.Random(seed)

        craft_names = [
            "机械底座装配工艺",
            "主控板PCB装配工艺",
            "接口板PCB装配工艺",
            "外壳组装与紧固工艺",
            "标准包装工艺流程",
        ]
        processes = [
            ("30", "装配"),
            ("31", "测试"),
            ("32", "包装"),
        ]
        workers = [
            ("07488", "张三"),
            ("07489", "李四"),
            ("07490", "王五"),
            ("07491", "赵六"),
        ]
        statuses = [-1, -2, 1, 2, 3, 4]
        step_templates = [
            "按表格准备零部件和辅料。",
            "检查连接器状态，确认一致后装配。",
            "按工序简图所示进行对位并紧固螺钉。",
            "涂抹规定胶水/螺纹紧固剂并清理溢出物。",
            "进行外观检查与尺寸复核。",
            "完成后提交自检结果并进入下一步。",
        ]

        tasks: List[Dict[str, Any]] = []
        for i in range(count):
            task_no = f"TASK-{now.strftime('%Y%m%d')}-{i+1:04d}"
            craft_no = f"JZ2.940.{rng.randint(10000, 99999)}GY-TX{rng.randint(1, 9):02d}"
            craft_version = f"N.{rng.randint(1, 3)}"
            craft_name = rng.choice(craft_names)
            process_code, process_name = rng.choice(processes)
            worker_code, worker_name = rng.choice(workers)
            status = rng.choice(statuses)
            algorithm_id = rng.choice(algo_ids)

            start_offset_minutes = rng.randint(-240, 60)
            duration_minutes = rng.randint(30, 240)
            start_time = now + datetime.timedelta(minutes=start_offset_minutes)
            end_time = start_time + datetime.timedelta(minutes=duration_minutes)

            step_count = rng.randint(3, 6)
            step_infos = []
            for step_idx in range(step_count):
                step_infos.append(
                    {
                        "step_code": str(step_idx + 1),
                        "step_name": str(step_idx + 1),
                        "guide_url": "",
                        "step_content": rng.choice(step_templates),
                    }
                )

            tasks.append(
                {
                    "task_no": task_no,
                    "craft_no": craft_no,
                    "craft_version": craft_version,
                    "craft_name": craft_name,
                    "process_code": process_code,
                    "process_name": process_name,
                    "start_time": start_time.isoformat(timespec="seconds"),
                    "end_time": end_time.isoformat(timespec="seconds"),
                    "worker_code": worker_code,
                    "worker_name": worker_name,
                    "status": status,
                    "algorithm_id": algorithm_id,
                    "step_infos": step_infos,
                }
            )
        return tasks

    def upload_step_log(self, step_data: Dict[str, Any]):
        """Queue a guidance step log for upload."""
        task = {
            "type": "step_log",
            "payload": step_data,
            "timestamp": time.time()
        }
        self.upload_queue.put(task)

    def upload_result_log(self, result_data: Dict[str, Any]):
        """Queue a work order result log for upload."""
        task = {
            "type": "result_log",
            "payload": result_data,
            "timestamp": time.time()
        }
        self.upload_queue.put(task)

    def upload_image(self, file_path: str):
        """Queue an image for upload."""
        task = {
            "type": "image",
            "payload": {"file_path": file_path},
            "timestamp": time.time()
        }
        self.upload_queue.put(task)

    def get_upload_queue_size(self) -> int:
        return self.upload_queue.qsize()

    def stop(self):
        """Stop the background worker."""
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2.0)
