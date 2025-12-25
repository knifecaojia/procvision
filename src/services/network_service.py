import logging
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from ..core.config import get_config

logger = logging.getLogger(__name__)

class NetworkService:
    """
    Network service layer for handling communication with the server.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NetworkService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.config = get_config().network
        self.base_url = self.config.base_url
        self._project_root = Path(__file__).resolve().parents[2]
        self._load_server_config()
        self.timeout = self.config.timeout
        self.session = requests.Session()
        self.token = None
        self._initialized = True
        logger.info(f"Network base URL: {self.base_url}")
    
    def _load_server_config(self):
        """
        Load server address and port from external config.json if available.
        """
        try:
            cfg_path = self._project_root / "config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                server = cfg.get("server", {})
                addr = server.get("address")
                port = server.get("port")
                protocol = server.get("protocol", "http")
                if addr and port:
                    self.base_url = f"{protocol}://{addr}:{port}"
                    logger.info(f"Server config loaded from config.json: {self.base_url}")
            else:
                logger.debug("config.json not found, using default network config")
        except Exception as e:
            logger.warning(f"Failed to load config.json server settings: {e}")
        
    def _require_token(self):
        if not self.token:
            raise Exception("Missing auth token. Please login first.")
        
    def set_token(self, token: str):
        """Set authentication token for future requests."""
        self.token = token
        # Assuming standard Bearer token format, can be adjusted if spec differs
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def login(self, username, password) -> Dict[str, Any]:
        url = f"{self.base_url}/client/auth/login"
        payload = {"username": username, "password": password}
        
        logger.info(f"Attempting login for user: {username} at {url}")
        
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            return self._handle_login_response(response)
        except requests.RequestException as e:
            logger.error(f"Login network error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            try:
                response = self.session.post(url, data=payload, timeout=self.timeout)
                return self._handle_login_response(response)
            except requests.RequestException:
                try:
                    response = self.session.get(url, params=payload, timeout=self.timeout)
                    return self._handle_login_response(response)
                except requests.RequestException as e2:
                    logger.error(f"Login fallback error: {e2}")
                    raise

    def _handle_login_response(self, response: requests.Response) -> Dict[str, Any]:
        response.raise_for_status()
        try:
            data = response.json()
        except Exception as parse_err:
            logger.error(f"Login parse error: {parse_err}")
            logger.error(f"Login raw response: {response.text}")
            raise
        if data.get("code") == 200:
            token_data = data.get("data", {})
            token = token_data.get("token")
            if token:
                self.set_token(token)
                logger.info("Login successful, token received")
            else:
                logger.warning("Login successful but no token received")
            return data
        msg = data.get("msg", "Login failed")
        logger.warning(f"Login failed: {msg}")
        raise Exception(msg)

    def get_work_orders(self, page_num: int = 1, page_size: int = 10, status: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch work orders from the server.
        
        Args:
            page_num: Page number
            page_size: Page size
            status: Optional status filter (1: Pending, 2: In Progress, 3: Completed, 4: Blocked)
            
        Returns:
            Work order list data
        """
        self._require_token()
        url = f"{self.base_url}/client/workorder/list"
        params = {"pageNum": page_num, "pageSize": page_size}
        if status is not None:
            params["status"] = status
            
        logger.debug(f"Fetching work orders: {params}")
            
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Get work orders error: {e}")
            raise

    def get_algorithms(self, page_num: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Fetch algorithms from the server.
        
        Args:
            page_num: Page number
            page_size: Page size
            
        Returns:
            Algorithm list data
        """
        self._require_token()
        url = f"{self.base_url}/client/algorithm/list"
        params = {"pageNum": page_num, "pageSize": page_size}
        
        logger.debug(f"Fetching algorithms: {params}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Get algorithms error: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        logger.debug("Performing health check")
        self._require_token()
        url = f"{self.base_url}/client/auth/health"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            try:
                data = response.json()
                logger.info(f"Health data: {data}")
                return data
            except Exception as parse_err:
                raw_text = response.text
                logger.error(f"Health check parse error: {parse_err}")
                logger.error(f"Health raw response: {raw_text}")
                return {"code": response.status_code, "raw": raw_text}
        except Exception as e:
            logger.error(f"Health check error: {e}")
            try:
                logger.error(f"Response status: {getattr(e, 'response', None).status_code}")
                logger.error(f"Response text: {getattr(getattr(e, 'response', None), 'text', None)}")
            except Exception:
                pass
            return {"code": -1, "error": str(e)}
