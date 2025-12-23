import json
import logging
import threading
import queue
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

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
        """Fetch algorithms from mock data."""
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
