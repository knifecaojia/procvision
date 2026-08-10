"""Serial relay service for NG linkage and manual debugging."""

from __future__ import annotations

import logging
import threading

try:
    import serial  # type: ignore
    from serial.tools import list_ports  # type: ignore
except Exception:  # pragma: no cover - depends on environment
    serial = None
    list_ports = None


from src.core.config import get_config, reload_config

logger = logging.getLogger(__name__)


class RelayService:
    """Singleton wrapper around the USB serial single-channel relay."""

    _instance = None

    OPEN_COMMAND = bytes([0xA0, 0x01, 0x01, 0xA2])
    CLOSE_COMMAND = bytes([0xA0, 0x01, 0x00, 0xA1])

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RelayService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.RLock()
        self._serial_handle = None
        self._is_open = False
        self._config_enabled = True
        self._port_name = ""
        self._baud_rate = 9600
        self._load_from_config()

    def reload_config(self) -> None:
        """Reload relay settings from config.json and reset serial handle."""
        with self._lock:
            try:
                reload_config()
            except Exception:
                logger.exception("Failed to reload global config before refreshing relay settings")
            self._close_serial_locked()
            self._is_open = False
            self._load_from_config()

    def is_configured(self) -> bool:
        with self._lock:
            return bool(self._config_enabled and self._port_name)

    def is_open(self) -> bool:
        with self._lock:
            return self._is_open

    def is_connected(self) -> bool:
        with self._lock:
            return self._serial_handle is not None

    def list_available_ports(self):
        ports = []
        if list_ports is not None:
            try:
                ports = [str(item.device) for item in list_ports.comports() if getattr(item, "device", "")]
            except Exception:
                logger.exception("Failed to enumerate serial ports")
        with self._lock:
            if self._port_name and self._port_name not in ports:
                ports.append(self._port_name)
        return sorted(set(ports), key=lambda item: (len(item), item))

    def open_port(self, source: str = "") -> bool:
        with self._lock:
            if not self._config_enabled:
                logger.info("Relay port open skipped because relay.enabled is false (source=%s)", source or "unknown")
                return False
            if not self._port_name:
                logger.warning("Relay port open skipped because relay.port_name is empty (source=%s)", source or "unknown")
                return False
            return self._ensure_serial_locked() is not None

    def close_port(self, source: str = "") -> bool:
        with self._lock:
            if self._serial_handle is None:
                self._is_open = False
                return True
            if self._is_open:
                try:
                    self._serial_handle.write(self.CLOSE_COMMAND)
                    try:
                        self._serial_handle.flush()
                    except Exception:
                        pass
                except Exception:
                    logger.exception("Failed to send relay close command before closing port (source=%s)", source or "unknown")
            self._is_open = False
            self._close_serial_locked()
            logger.info("Relay serial port closed (source=%s)", source or "unknown")
            return True

    def turn_on(self, source: str = "") -> bool:
        return self._set_state(True, source=source)

    def turn_off(self, source: str = "") -> bool:
        return self._set_state(False, source=source)

    def sync_with_ng(self, active: bool, source: str = "") -> bool:
        return self._set_state(bool(active), source=source)

    def close(self) -> None:
        with self._lock:
            self._is_open = False
            self._close_serial_locked()

    def _set_state(self, target_open: bool, source: str = "") -> bool:
        with self._lock:
            if not self._config_enabled:
                logger.info("Relay command skipped because relay.enabled is false (source=%s)", source or "unknown")
                return False
            if not self._port_name:
                logger.warning("Relay command skipped because relay.port_name is empty (source=%s)", source or "unknown")
                return False
            if self._is_open == target_open:
                logger.debug(
                    "Relay already in target state=%s (source=%s)",
                    "open" if target_open else "closed",
                    source or "unknown",
                )
                return True
            handle = self._ensure_serial_locked()
            if handle is None:
                return False
            command = self.OPEN_COMMAND if target_open else self.CLOSE_COMMAND
            try:
                handle.write(command)
                try:
                    handle.flush()
                except Exception:
                    pass
                self._is_open = target_open
                logger.info(
                    "Relay switched %s on %s @ %s (source=%s)",
                    "open" if target_open else "closed",
                    self._port_name,
                    self._baud_rate,
                    source or "unknown",
                )
                return True
            except Exception as exc:
                logger.error("Failed to write relay command (source=%s): %s", source or "unknown", exc)
                self._close_serial_locked()
                self._is_open = False
                return False

    def _ensure_serial_locked(self):
        if self._serial_handle is not None:
            return self._serial_handle
        if serial is None:
            logger.error("pyserial is not available; relay control cannot start")
            return None
        try:
            self._serial_handle = serial.Serial(
                port=self._port_name,
                baudrate=int(self._baud_rate),
                timeout=0.5,
                write_timeout=0.5,
            )
            return self._serial_handle
        except Exception as exc:
            logger.error(
                "Failed to open relay serial port %s @ %s: %s",
                self._port_name,
                self._baud_rate,
                exc,
            )
            self._serial_handle = None
            return None

    def _close_serial_locked(self) -> None:
        handle = self._serial_handle
        self._serial_handle = None
        if handle is None:
            return
        try:
            handle.close()
        except Exception:
            logger.exception("Failed to close relay serial handle")

    def _load_from_config(self) -> None:
        cfg = getattr(get_config(), "relay", None)
        if cfg is None:
            self._config_enabled = True
            self._port_name = ""
            self._baud_rate = 9600
            return
        self._config_enabled = bool(getattr(cfg, "enabled", True))
        self._port_name = str(getattr(cfg, "port_name", "") or "").strip()
        try:
            self._baud_rate = int(getattr(cfg, "baud_rate", 9600) or 9600)
        except (TypeError, ValueError):
            self._baud_rate = 9600
