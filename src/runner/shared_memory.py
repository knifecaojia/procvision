import os
import re
import tempfile
import numpy as np
from typing import Union, Optional

# Match the SDK's default logic
def _get_shm_dir() -> str:
    d = os.environ.get("PROC_SHM_DIR") or os.path.join(tempfile.gettempdir(), "procvision_dev_shm")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d

def _safe_name(shared_mem_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", shared_mem_id)

def write_image_to_shared_memory(shared_mem_id: str, image: Union[bytes, np.ndarray]) -> None:
    """
    Writes image data to shared memory (file-based implementation compatible with SDK).
    
    Args:
        shared_mem_id: Unique ID for the shared memory slot.
        image: Image data as bytes (JPEG/PNG) or numpy array (HWC RGB/BGR).
    """
    base_dir = _get_shm_dir()
    safe_id = _safe_name(shared_mem_id)
    base_path = os.path.join(base_dir, safe_id)
    
    # Clean up previous files for this ID to avoid ambiguity
    try:
        if os.path.exists(base_path + ".bin"):
            os.remove(base_path + ".bin")
        if os.path.exists(base_path + ".npy"):
            os.remove(base_path + ".npy")
    except OSError:
        pass

    if isinstance(image, bytes):
        file_path = base_path + ".bin"
        with open(file_path, "wb") as f:
            f.write(image)
    elif isinstance(image, np.ndarray):
        file_path = base_path + ".npy"
        np.save(file_path, image)
    else:
        raise ValueError(f"Unsupported image type: {type(image)}")

def clear_shared_memory(shared_mem_id: str) -> None:
    """Cleans up the shared memory files for a given ID."""
    base_dir = _get_shm_dir()
    safe_id = _safe_name(shared_mem_id)
    base_path = os.path.join(base_dir, safe_id)
    
    try:
        if os.path.exists(base_path + ".bin"):
            os.remove(base_path + ".bin")
        if os.path.exists(base_path + ".npy"):
            os.remove(base_path + ".npy")
    except OSError:
        pass
