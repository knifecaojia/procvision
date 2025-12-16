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

class RegistryEntry(TypedDict):
    name: str
    version: str
    supported_pids: List[str]
    state: PackageState
    created_at: float
    install_path: str

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

class SessionContext(TypedDict):
    product_code: str
    trace_id: str
    # other fields...

class Session(TypedDict):
    id: str
    context: SessionContext

class CallRequest(TypedDict):
    type: str # "call"
    step_index: int
    pid: str
    session: Session
    user_params: Dict[str, Any]
    shared_mem_id: str
    image_meta: ImageMeta
    phase: str # "pre" | "execute"

class CallResultData(TypedDict):
    result_status: str # "OK" | "NG"
    ng_reason: Optional[str]
    defect_rects: Optional[List[Dict[str, Any]]]
    position_rects: Optional[List[Dict[str, Any]]]
    calibration_rects: Optional[List[Dict[str, Any]]]
    debug: Optional[Dict[str, Any]]

class CallResult(TypedDict):
    type: str # "result"
    phase: str
    status: str # "OK" | "ERROR"
    message: Optional[str]
    error_code: Optional[str]
    data: Optional[CallResultData]
