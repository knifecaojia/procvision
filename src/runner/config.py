import os
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RunnerConfig:
    """Configuration for the SDK Runner."""
    
    # Paths
    runner_root: str = "algorithms"
    zips_dir: str = field(init=False)
    deployed_dir: str = field(init=False)
    registry_path: str = field(init=False)
    active_dir: str = field(init=False)
    logs_dir: str = field(init=False)
    
    # Timeouts (ms)
    pre_execute_timeout_ms: int = 3000
    execute_timeout_ms: int = 5000
    heartbeat_interval_ms: int = 5000
    heartbeat_grace_ms: int = 2000
    
    # Retries
    max_retries: int = 2
    
    # Logging
    log_level: str = "info"
    save_debug_fields: List[str] = field(default_factory=lambda: ["latency_ms", "model_version"])
    
    # Shared Memory
    shared_memory_backend: str = "native"  # Implementation uses file-based for now
    image_encoding: str = "jpeg|array"
    color_space_default: str = "RGB"
    
    # Limits
    max_defects: int = 20
    
    # Package Management
    allow_local_import: bool = True
    local_store_path: str = field(init=False)

    def __post_init__(self):
        # Resolve absolute paths
        if not os.path.isabs(self.runner_root):
            self.runner_root = os.path.abspath(self.runner_root)
            
        self.zips_dir = os.path.join(self.runner_root, "zips")
        self.deployed_dir = os.path.join(self.runner_root, "deployed")
        self.registry_path = os.path.join(self.runner_root, "registry.json")
        self.active_dir = os.path.join(self.runner_root, "active")
        self.logs_dir = os.path.join(self.runner_root, "logs")
        self.local_store_path = os.path.join(self.runner_root, "local")

# Global default configuration
default_config = RunnerConfig()
