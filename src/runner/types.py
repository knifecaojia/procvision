from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional

class PackageState(str, Enum):
    INSTALLED = "installed"
    RUNNING = "running"
    STOPPED = "stopped"
    INVALID = "invalid"

class ProcessState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"  # Handshake done
    EXECUTING = "executing" # Processing a request
    STOPPED = "stopped"
    ERROR = "error"

class Manifest(TypedDict):
    name: str
    version: str
    entry_point: str
    supported_pids: List[str]
    description: Optional[str]
    python_version: Optional[str]

class RegistryEntry(TypedDict, total=False):
    name: str
    version: str
    supported_pids: List[str]
    state: PackageState
    created_at: float
    install_path: str
    working_dir: Optional[str]
    python_rel_path: Optional[str]

class ActiveMapping(TypedDict):
    name: str
    version: str
    activated_at: float

class ImageMeta(TypedDict):
    width: int
    height: int
    timestamp_ms: int
    camera_id: str
    color_space: Optional[str]

class CallRequestData(TypedDict, total=False):
    step_index: int
    step_desc: str
    guide_info: List[str]
    cur_image_shm_id: str
    cur_image_meta: ImageMeta
    guide_image_shm_id: str
    guide_image_meta: ImageMeta

class CallRequest(TypedDict):
    type: str # "call"
    request_id: str
    data: CallRequestData

class CallResultData(TypedDict, total=False):
    result_status: str # "OK" | "NG"
    ng_reason: Optional[str]
    defect_rects: Optional[List[Dict[str, Any]]]
    step_index: Optional[int]
    debug: Optional[Dict[str, Any]]

class CallResult(TypedDict):
    type: str # "result"
    request_id: str
    timestamp_ms: int
    status: str # "OK" | "ERROR"
    message: Optional[str]
    error_code: Optional[str]
    data: Optional[CallResultData]
