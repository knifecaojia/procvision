import os
import sys
import json
import struct
import time
import subprocess
import threading
import queue
import logging
from typing import Optional, Dict, Any, List

from .config import RunnerConfig
from .types import ProcessState
from .exceptions import RunnerError, TimeoutError

logger = logging.getLogger(__name__)

class AlgorithmProcess:
    def __init__(self, install_path: str, entry_point: str, config: RunnerConfig, python_rel_path: str = "", working_dir: str = ""):
        self.install_path = install_path
        self.entry_point = entry_point
        self.config = config
        self.python_rel_path = python_rel_path
        self.working_dir = working_dir
        
        self.process: Optional[subprocess.Popen] = None
        self.state = ProcessState.STOPPED
        self.lock = threading.RLock()
        
        self.msg_queue = queue.Queue() # For results/errors
        self._stop_event = threading.Event()
        self.last_pong_time = 0.0
        
        self._threads: List[threading.Thread] = []

    def start(self):
        if self.process and self.process.poll() is None:
            return

        with self.lock:
            self.state = ProcessState.STARTING
            self._stop_event.clear()
            
            # Resolve python executable
            # Prefer python_rel_path from registry if available (supports conda structure)
            if hasattr(self, 'python_rel_path') and self.python_rel_path:
                python_exe = os.path.join(self.install_path, self.python_rel_path)
            else:
                # Fallback to standard venv structure
                if os.name == 'nt':
                    python_exe = os.path.join(self.install_path, "venv", "Scripts", "python.exe")
                else:
                    python_exe = os.path.join(self.install_path, "venv", "bin", "python")

            if not os.path.exists(python_exe):
                # Try fallback for Windows Conda (if python_rel_path wasn't set but it is conda)
                # Conda on Windows puts python.exe in root of env
                python_exe_conda = os.path.join(self.install_path, "venv", "python.exe")
                if os.path.exists(python_exe_conda):
                     python_exe = python_exe_conda
                else:
                     raise RunnerError(f"Python interpreter not found at {python_exe}", "2003")

            env = os.environ.copy()
            env["PROC_ENV"] = "prod"
            env["PYTHONUNBUFFERED"] = "1"
            
            # Determine Working Directory (CWD)
            cwd = self.working_dir if self.working_dir else self.install_path
            
            # Look for manifest.json in subdirectories if not in root (only if working_dir not explicitly set)
            if not self.working_dir and not os.path.exists(os.path.join(cwd, "manifest.json")):
                for item in os.listdir(cwd):
                    subpath = os.path.join(cwd, item)
                    if os.path.isdir(subpath) and os.path.exists(os.path.join(subpath, "manifest.json")):
                        cwd = subpath
                        break
            
            env["PROC_ALGO_ROOT"] = cwd
            
            cmd = [
                python_exe,
                "-m", "procvision_algorithm_sdk.adapter",
                "--entry", self.entry_point
            ]

            logger.info(f"Starting process: {' '.join(cmd)} in {cwd}")
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd, # Use the detected CWD
                env=env,
                bufsize=0 # Unbuffered
            )

            # Start IO threads
            t_out = threading.Thread(target=self._stdout_loop, name="stdout_reader", daemon=True)
            t_err = threading.Thread(target=self._stderr_loop, name="stderr_reader", daemon=True)
            t_hb = threading.Thread(target=self._heartbeat_loop, name="heartbeat_loop", daemon=True)
            
            self._threads = [t_out, t_err, t_hb]
            for t in self._threads:
                t.start()
                
            # Wait for Hello
            try:
                msg = self.msg_queue.get(timeout=5)
                if msg.get("type") == "hello":
                    self.state = ProcessState.RUNNING
                    self.last_pong_time = time.time()
                    self._send_hello_response()
                    logger.info("Handshake successful")
                else:
                    self.stop()
                    raise RunnerError(f"Unexpected handshake message: {msg}")
            except queue.Empty:
                self.stop()
                raise RunnerError("Handshake timeout", "1005")

    def stop(self):
        self._stop_event.set()
        with self.lock:
            if self.process:
                logger.info("Stopping process...")
                try:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                except Exception:
                    pass
                self.process = None
            self.state = ProcessState.STOPPED

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def send_frame(self, data: Dict[str, Any]):
        if not self.is_alive():
            raise RunnerError("Process is not running")
        
        json_bytes = json.dumps(data).encode("utf-8")
        header = struct.pack(">I", len(json_bytes))
        
        try:
            with self.lock:
                self.process.stdin.write(header + json_bytes)
                self.process.stdin.flush()
        except OSError as e:
            logger.error(f"Failed to send frame: {e}")
            self.stop()
            raise RunnerError("Pipe broken", "9999")

    def call(self, req: Dict[str, Any], timeout_ms: int) -> Dict[str, Any]:
        """Blocking call to the algorithm."""
        with self.lock:
            if self.state != ProcessState.RUNNING:
                # If executing, we might want to wait or queue, but for now strict serialized
                # Actually, runner engine ensures serialization per pid.
                pass
            self.state = ProcessState.EXECUTING

        try:
            self.send_frame(req)
            
            # Wait for result
            # We need to filter for the specific result type if we had concurrent requests,
            # but protocol implies single active call per process.
            timeout_sec = timeout_ms / 1000.0
            start_t = time.time()
            
            while True:
                if time.time() - start_t > timeout_sec:
                    raise TimeoutError(f"Call timeout after {timeout_ms}ms")
                
                try:
                    # Check connection
                    if not self.is_alive():
                        raise RunnerError("Process died during execution")

                    msg = self.msg_queue.get(timeout=0.1)
                    if msg.get("type") == "result":
                        return msg
                    elif msg.get("type") == "error":
                         raise RunnerError(f"Algorithm error: {msg.get('message')}", msg.get("code", "9999"))
                    # Ignore pings/logs here (handled in loop)
                except queue.Empty:
                    continue

        finally:
            self.state = ProcessState.RUNNING

    def _send_hello_response(self):
        resp = {
            "type": "hello",
            "runner_version": "1.0.0",
            "heartbeat_interval_ms": self.config.heartbeat_interval_ms,
            "heartbeat_grace_ms": self.config.heartbeat_grace_ms
        }
        self.send_frame(resp)

    def _stdout_loop(self):
        """Reads length-prefixed JSON frames from stdout."""
        while not self._stop_event.is_set():
            if not self.process:
                 break
            try:
                # Read 4 bytes length
                raw_len = self.process.stdout.read(4)
                if not raw_len:
                    break
                if len(raw_len) < 4:
                    logger.warning(f"Incomplete length prefix: {raw_len}")
                    break
                
                length = struct.unpack(">I", raw_len)[0]
                
                # Read payload
                payload = b""
                while len(payload) < length:
                    chunk = self.process.stdout.read(length - len(payload))
                    if not chunk:
                        break
                    payload += chunk
                
                if len(payload) != length:
                    logger.warning(f"Incomplete payload: got {len(payload)} expected {length}")
                    break
                
                # Parse JSON
                try:
                    data = json.loads(payload.decode("utf-8"))
                    msg_type = data.get("type")
                    
                    if msg_type == "pong":
                        self.last_pong_time = time.time()
                    elif msg_type in ["hello", "result", "error"]:
                        if msg_type == "result":
                             logger.info(f"Received RESULT from algo: {json.dumps(data, ensure_ascii=False)}")
                        self.msg_queue.put(data)
                    else:
                        logger.warning(f"Unknown message type: {msg_type}")
                        
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON frame")
                    
            except ValueError: # file might be closed
                break
            except Exception as e:
                logger.error(f"Stdout loop error: {e}")
                break
        
        logger.info("Stdout loop exited")
        self.stop()

    def _stderr_loop(self):
        """Reads stderr for logs."""
        while not self._stop_event.is_set():
            if not self.process:
                 break
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                
                # Try parsing structured log
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    log_entry = json.loads(line_str)
                    # TODO: Forward to structured logging system
                    # For now just print formatted
                    logger.info(f"[ALGO] {log_entry.get('message', line_str)}")
                except json.JSONDecodeError:
                    logger.info(f"[ALGO-RAW] {line_str}")
                    
            except ValueError: # file might be closed
                break
            except Exception:
                break

    def _heartbeat_loop(self):
        interval = self.config.heartbeat_interval_ms / 1000.0
        grace = self.config.heartbeat_grace_ms / 1000.0
        
        while not self._stop_event.is_set():
            time.sleep(interval)
            if not self.is_alive():
                break
            
            # Check last pong
            if time.time() - self.last_pong_time > (interval + grace) and self.state == ProcessState.RUNNING:
                # Initial grace period handling could be added
                logger.warning("Heartbeat timeout, restarting...")
                self.stop()
                break
                
            try:
                self.send_frame({"type": "ping"})
            except Exception:
                pass
