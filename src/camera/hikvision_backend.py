"""
Hikvision backend integration built on top of the official MVS Python SDK.

This backend is optional: it is only used when the SDK runtime can be imported
successfully. When the SDK is not present the application falls back to mock mode.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import time
from ctypes import POINTER, byref, cast, memset, sizeof
from typing import Iterable, List, Optional

import numpy as np

from .backend import BackendDevice, CameraBackend, FrameData
from .exceptions import (
    CameraError,
    ConnectionError,
    ParameterError,
    StreamError,
)
from .types import CameraInfo, CameraParameter, CameraTransport

LOG = logging.getLogger(__name__)


class HikvisionBackend(CameraBackend):  # pragma: no cover - requires vendor SDK
    """Backend implementation that talks to the real Hikvision SDK."""

    name = "HikvisionMVS"

    def __init__(self, sdk_path: Optional[str] = None) -> None:
        self._logger = LOG.getChild("HikvisionBackend")
        self._load_sdk_modules(sdk_path)
        self._initialize_sdk()

    # ------------------------------------------------------------------
    def _load_sdk_modules(self, sdk_path: Optional[str]) -> None:
        search_paths = []
        env_path = os.getenv("MVCAM_COMMON_RUNENV")
        if env_path:
            # Add DLL path to system PATH for Windows
            if sys.platform == "win32":
                # Determine if we're running 64-bit or 32-bit Python
                dll_path = os.path.join(env_path, "Bin", "win64" if sys.maxsize > 2**32 else "win32")
                if os.path.exists(dll_path):
                    # Add to PATH environment variable
                    current_path = os.environ.get("PATH", "")
                    if dll_path not in current_path:
                        os.environ["PATH"] = current_path + ";" + dll_path
                        self._logger.debug("Added to PATH: %s", dll_path)

            search_paths.append(os.path.join(env_path, "Samples", "python", "MvImport"))

        if sdk_path:
            search_paths.append(sdk_path)

        for path in search_paths:
            if path and path not in sys.path:
                sys.path.append(path)
                self._logger.debug("Added to sys.path: %s", path)

        self._logger.debug("Attempting to import MVS SDK modules from paths: %s", search_paths)

        try:
            from MvCameraControl_class import (  # type: ignore
                MvCamera,
                MV_CC_DEVICE_INFO,
                MV_CC_DEVICE_INFO_LIST,
                MV_GIGE_DEVICE,
                MV_USB_DEVICE,
                MV_ACCESS_Exclusive,
            )
            from CameraParams_header import (  # type: ignore
                MVCC_ENUMVALUE,
                MVCC_FLOATVALUE,
                MVCC_INTVALUE,
                MV_FRAME_OUT,
                MV_FRAME_OUT_INFO_EX,
                MV_CC_PIXEL_CONVERT_PARAM,
            )
            from MvErrorDefine_const import MV_OK  # type: ignore
        except ImportError as exc:
            self._logger.error("Failed to import MVS SDK modules. Error: %s", exc)
            self._logger.error("Current sys.path: %s", sys.path)
            # Try individual imports to identify the problematic module
            modules_to_try = [
                "MvCameraControl_class",
                "CameraParams_header",
                "MvErrorDefine_const"
            ]
            for module in modules_to_try:
                try:
                    __import__(module)
                    self._logger.debug("Successfully imported %s", module)
                except ImportError as mod_exc:
                    self._logger.error("Failed to import %s: %s", module, mod_exc)
            raise RuntimeError(
                "Hikvision MVS SDK modules could not be imported. Ensure the SDK is "
                "installed and MVCAM_COMMON_RUNENV is set. Search paths: {}".format(search_paths)
            ) from exc

        # Stash imported names on the instance to avoid leaking them globally
        self._MvCamera = MvCamera
        self._MV_CC_DEVICE_INFO = MV_CC_DEVICE_INFO
        self._MV_CC_DEVICE_INFO_LIST = MV_CC_DEVICE_INFO_LIST
        self._MV_GIGE_DEVICE = MV_GIGE_DEVICE
        self._MV_USB_DEVICE = MV_USB_DEVICE
        self._MV_ACCESS_EXCLUSIVE = MV_ACCESS_Exclusive
        self._MVCC_ENUMVALUE = MVCC_ENUMVALUE
        self._MVCC_FLOATVALUE = MVCC_FLOATVALUE
        self._MVCC_INTVALUE = MVCC_INTVALUE
        self._MV_FRAME_OUT = MV_FRAME_OUT
        self._MV_FRAME_OUT_INFO_EX = MV_FRAME_OUT_INFO_EX
        self._MV_PIXEL_CONVERT_PARAM = MV_CC_PIXEL_CONVERT_PARAM
        self._MV_OK = MV_OK

        try:
            from MvCameraControl_class import PixelType_Gvsp_RGB8_Packed  # type: ignore
            from MvCameraControl_class import PixelType_Gvsp_Mono8  # type: ignore
        except ImportError:
            # Older SDK versions export PixelType definitions from a different module
            from PixelType import (  # type: ignore
                PixelType_Gvsp_RGB8_Packed,
                PixelType_Gvsp_Mono8,
            )

        self._PixelType_RGB = PixelType_Gvsp_RGB8_Packed
        self._PixelType_Mono = PixelType_Gvsp_Mono8

    # ------------------------------------------------------------------
    def _initialize_sdk(self) -> None:
        try:
            ret = self._MvCamera.MV_CC_Initialize()
        except AttributeError:
            self._logger.debug("MV_CC_Initialize not exposed by SDK version, skipping.")
            return

        if ret != self._MV_OK:
            raise RuntimeError(f"MV_CC_Initialize failed with code 0x{ret:08x}")

    # ------------------------------------------------------------------
    def discover(self) -> List[CameraInfo]:
        device_list = self._MV_CC_DEVICE_INFO_LIST()
        tlayer_types = self._MV_GIGE_DEVICE | self._MV_USB_DEVICE
        ret = self._MvCamera.MV_CC_EnumDevices(tlayer_types, device_list)
        if ret != self._MV_OK:
            raise CameraError(f"MV_CC_EnumDevices failed with code 0x{ret:08x}")

        cameras: List[CameraInfo] = []
        for index in range(device_list.nDeviceNum):
            device_ptr = cast(device_list.pDeviceInfo[index], POINTER(self._MV_CC_DEVICE_INFO))
            device_info = device_ptr.contents
            cameras.append(self._convert_device_info(index, device_info))
        return cameras

    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        try:
            ret = self._MvCamera.MV_CC_Finalize()
            if ret != self._MV_OK:
                self._logger.debug("MV_CC_Finalize returned 0x%08x", ret)
        except AttributeError:
            return
        except Exception as exc:
            self._logger.warning("Failed to finalize SDK cleanly: %s", exc)

    # ------------------------------------------------------------------
    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _convert_device_info(self, index: int, info) -> CameraInfo:
        transport = CameraTransport.UNKNOWN
        serial = None
        ip_address = None
        manufacturer = None
        model_name = None
        name = f"Camera {index}"

        def _decode(buffer) -> Optional[str]:
            if buffer is None:
                return None
            if isinstance(buffer, str):
                text = buffer.split("\0", 1)[0]
                return text or None

            raw: Optional[bytes] = None
            if isinstance(buffer, (bytes, bytearray, memoryview)):
                raw = bytes(buffer)
            elif isinstance(buffer, (tuple, list)):
                raw = bytes(buffer)
            else:
                value = getattr(buffer, "value", None)
                if isinstance(value, (bytes, bytearray)):
                    raw = bytes(value)
                elif isinstance(value, str):
                    text = value.split("\0", 1)[0]
                    return text or None

                if raw is None:
                    try:
                        raw = bytes(buffer)
                    except (TypeError, ValueError):
                        raw = None

            if not raw:
                return None

            raw = raw.split(b"\0", 1)[0]
            if not raw:
                return None

            for encoding in ("utf-8", "gb18030", "gbk", "latin-1"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="ignore")

        layer_type = info.nTLayerType
        if layer_type == self._MV_GIGE_DEVICE:
            transport = CameraTransport.GIGE
            gige = info.SpecialInfo.stGigEInfo
            manufacturer = _decode(gige.chManufacturerName)
            model_name = _decode(gige.chModelName)
            serial = _decode(gige.chSerialNumber)
            # Handle both old and new SDK versions
            if hasattr(gige, 'chCurrentIp'):
                ip_address = _decode(gige.chCurrentIp)
            elif hasattr(gige, 'nCurrentIp'):
                # Newer SDK versions use nCurrentIp (integer) instead of chCurrentIp (string)
                ip_address = str(gige.nCurrentIp)
            name = _decode(gige.chUserDefinedName) or _decode(gige.chModelName) or name
        elif layer_type == self._MV_USB_DEVICE:
            transport = CameraTransport.USB
            usb = info.SpecialInfo.stUsb3VInfo
            manufacturer = _decode(usb.chManufacturerName)
            model_name = _decode(usb.chModelName)
            serial = _decode(usb.chSerialNumber)
            name = _decode(usb.chUserDefinedName) or _decode(usb.chModelName) or name

        return CameraInfo(
            id=f"HIK-{serial or index}",
            name=name,
            transport=transport,
            serial_number=serial,
            ip_address=ip_address,
            manufacturer=manufacturer,
            model_name=model_name,
            backend_data={"backend": self.name, "index": index},
        )

    # ------------------------------------------------------------------
    def connect(self, info: CameraInfo) -> BackendDevice:
        index = info.backend_data.get("index", 0)
        device_list = self._MV_CC_DEVICE_INFO_LIST()
        ret = self._MvCamera.MV_CC_EnumDevices(
            self._MV_GIGE_DEVICE | self._MV_USB_DEVICE, device_list
        )
        if ret != self._MV_OK:
            raise ConnectionError(f"MV_CC_EnumDevices failed with code 0x{ret:08x}")

        if device_list.nDeviceNum <= index:
            raise ConnectionError(f"Device index {index} out of range.")

        device_ptr = cast(device_list.pDeviceInfo[index], POINTER(self._MV_CC_DEVICE_INFO))
        device_info = device_ptr.contents

        camera = self._MvCamera()
        ret = camera.MV_CC_CreateHandle(device_info)
        if ret != self._MV_OK:
            raise ConnectionError(f"MV_CC_CreateHandle failed with code 0x{ret:08x}")

        ret = camera.MV_CC_OpenDevice(self._MV_ACCESS_EXCLUSIVE, 0)
        if ret != self._MV_OK:
            camera.MV_CC_DestroyHandle()
            raise ConnectionError(f"MV_CC_OpenDevice failed with code 0x{ret:08x}")

        # Optimize packet size for GigE cameras where supported
        try:
            if info.transport == CameraTransport.GIGE:
                packet_size = camera.MV_CC_GetOptimalPacketSize()
                if int(packet_size) > 0:
                    camera.MV_CC_SetIntValue("GevSCPSPacketSize", packet_size)
        except Exception as exc:
            self._logger.debug("Packet size optimization not available: %s", exc)

        return HikvisionDevice(self, info, camera)


class HikvisionDevice(BackendDevice):  # pragma: no cover - requires vendor SDK
    """Concrete device wrapper around :class:`MvCamera`."""

    _PARAMETER_SPECS = {
        "exposure_time": CameraParameter(
            key="exposure_time",
            display_name="Exposure Time",
            unit="µs",
            min_value=10.0,
            max_value=1000000.0,
            step=10.0,
            value_type=float,
            group="Exposure",
        ),
        "gain": CameraParameter(
            key="gain",
            display_name="Gain",
            unit="dB",
            min_value=0.0,
            max_value=30.0,
            step=0.1,
            value_type=float,
            group="Exposure",
        ),
        "frame_rate": CameraParameter(
            key="frame_rate",
            display_name="Frame Rate",
            unit="fps",
            min_value=1.0,
            max_value=120.0,
            step=1.0,
            value_type=float,
            group="Acquisition",
        ),
        "gamma": CameraParameter(
            key="gamma",
            display_name="Gamma",
            min_value=0.1,
            max_value=4.0,
            step=0.1,
            value_type=float,
            group="Image",
        ),
        "black_level": CameraParameter(
            key="black_level",
            display_name="Black Level",
            min_value=0.0,
            max_value=255.0,
            step=1.0,
            value_type=float,
            group="Image",
        ),
        "brightness": CameraParameter(
            key="brightness",
            display_name="Brightness",
            min_value=-100.0,
            max_value=100.0,
            step=1.0,
            value_type=float,
            group="Image",
        ),
    }

    def __init__(self, backend: HikvisionBackend, info: CameraInfo, camera) -> None:
        super().__init__(info)
        self._backend = backend
        self._camera = camera
        self._streaming = False
        self._parameter_specs = dict(self._PARAMETER_SPECS)
        # Probe nodes and hide unsupported parameters
        node_map: dict[str, str] = {
            "exposure_time": "ExposureTime",
            "gain": "Gain",
            "frame_rate": "AcquisitionFrameRate",
            "gamma": "Gamma",
            "black_level": "BlackLevel",
            "brightness": "Brightness",
            "white_balance": "ColorTemperature",
            "saturation": "Saturation",
            "hue": "Hue",
        }
        available = {key: self._probe_float_node(node) for key, node in node_map.items()}
        for key, ok in available.items():
            if not ok and key in self._parameter_specs:
                self._parameter_specs.pop(key)
                self._backend._logger.debug(
                    "Node '%s' unavailable for %s; removed parameter '%s'", node_map[key], info.id, key
                )
        self._frame_buffer = backend._MV_FRAME_OUT()
        memset(byref(self._frame_buffer), 0, sizeof(self._frame_buffer))

    # ------------------------------------------------------------------
    def close(self) -> None:
        try:
            if self._streaming:
                self.stop_stream()
        finally:
            try:
                self._camera.MV_CC_CloseDevice()
            finally:
                self._camera.MV_CC_DestroyHandle()

    # ------------------------------------------------------------------
    def list_parameters(self) -> Iterable[CameraParameter]:
        return self._parameter_specs.values()

    # ------------------------------------------------------------------
    def get_parameter(self, key: str) -> object:
        spec = self._parameter_specs.get(key)
        if not spec:
            raise ParameterError(f"Unsupported parameter: {key}")

        if key == "white_balance":
            return self._get_color_temperature()
        if key == "saturation":
            return self._get_saturation()
        if key == "hue":
            return self._get_hue()

        sdk_key = self._map_parameter_key(key)
        value = self._backend._MVCC_FLOATVALUE()
        try:
            ret = self._camera.MV_CC_GetFloatValue(sdk_key, value)
        except TypeError:
            # Some SDK bindings require bytes for the key argument.
            ret = self._camera.MV_CC_GetFloatValue(sdk_key.encode("ascii"), value)
        if ret != self._backend._MV_OK:
            raise ParameterError(f"Failed to get {sdk_key}: 0x{ret:08x}")
        current = getattr(value, "fCurValue", None)
        if current is None and hasattr(value, "contents"):
            current = getattr(value.contents, "fCurValue", None)
        if current is None:
            raise ParameterError(f"{sdk_key} did not return a numeric value")
        return float(current)

    # ------------------------------------------------------------------
    def set_parameter(self, key: str, value: object) -> None:
        spec = self._parameter_specs.get(key)
        if not spec:
            raise ParameterError(f"Unsupported parameter: {key}")

        numeric_value = float(value)
        if spec.min_value is not None and numeric_value < spec.min_value:
            raise ParameterError(f"{key} below minimum {spec.min_value}")
        if spec.max_value is not None and numeric_value > spec.max_value:
            raise ParameterError(f"{key} above maximum {spec.max_value}")

        if key == "white_balance":
            self._set_color_temperature(numeric_value)
            return
        if key == "saturation":
            self._set_saturation(numeric_value)
            return
        if key == "hue":
            self._set_hue(numeric_value)
            return

        sdk_key = self._map_parameter_key(key)
        ret = self._camera.MV_CC_SetFloatValue(sdk_key, numeric_value)
        if ret != self._backend._MV_OK:
            raise ParameterError(f"Failed to set {sdk_key}: 0x{ret:08x}")

    # ------------------------------------------------------------------
    def _get_color_temperature(self) -> float:
        try:
            value = self._backend._MVCC_FLOATVALUE()
            try:
                ret = self._camera.MV_CC_GetFloatValue("ColorTemperature", value)
            except TypeError:
                ret = self._camera.MV_CC_GetFloatValue("ColorTemperature".encode("ascii"), value)
            if ret != self._backend._MV_OK:
                raise ParameterError(f"Get ColorTemperature failed: 0x{ret:08x}")
            current = getattr(value, "fCurValue", None)
            if current is None and hasattr(value, "contents"):
                current = getattr(value.contents, "fCurValue", None)
            if current is None:
                raise ParameterError("ColorTemperature did not return a numeric value")
            return float(current)
        except Exception as exc:
            raise ParameterError(f"Failed to read color temperature: {exc}") from exc

    # ------------------------------------------------------------------
    def _set_color_temperature(self, value: float) -> None:
        try:
            ret = self._camera.MV_CC_SetFloatValue("ColorTemperature", value)
            if ret != self._backend._MV_OK:
                raise ParameterError(f"Set ColorTemperature failed: 0x{ret:08x}")
        except Exception as exc:
            raise ParameterError(f"Failed to set color temperature: {exc}") from exc

    # ------------------------------------------------------------------
    def _get_saturation(self) -> float:
        try:
            value = self._backend._MVCC_FLOATVALUE()
            try:
                ret = self._camera.MV_CC_GetFloatValue("Saturation", value)
            except TypeError:
                ret = self._camera.MV_CC_GetFloatValue("Saturation".encode("ascii"), value)
            if ret != self._backend._MV_OK:
                raise ParameterError(f"Get Saturation failed: 0x{ret:08x}")
            current = getattr(value, "fCurValue", None)
            if current is None and hasattr(value, "contents"):
                current = getattr(value.contents, "fCurValue", None)
            if current is None:
                raise ParameterError("Saturation did not return a numeric value")
            return float(current)
        except Exception as exc:
            raise ParameterError(f"Failed to read saturation: {exc}") from exc

    # ------------------------------------------------------------------
    def _set_saturation(self, value: float) -> None:
        try:
            ret = self._camera.MV_CC_SetFloatValue("Saturation", value)
            if ret != self._backend._MV_OK:
                raise ParameterError(f"Set Saturation failed: 0x{ret:08x}")
        except Exception as exc:
            raise ParameterError(f"Failed to set saturation: {exc}") from exc

    # ------------------------------------------------------------------
    def _get_hue(self) -> float:
        try:
            value = self._backend._MVCC_FLOATVALUE()
            try:
                ret = self._camera.MV_CC_GetFloatValue("Hue", value)
            except TypeError:
                ret = self._camera.MV_CC_GetFloatValue("Hue".encode("ascii"), value)
            if ret != self._backend._MV_OK:
                raise ParameterError(f"Get Hue failed: 0x{ret:08x}")
            current = getattr(value, "fCurValue", None)
            if current is None and hasattr(value, "contents"):
                current = getattr(value.contents, "fCurValue", None)
            if current is None:
                raise ParameterError("Hue did not return a numeric value")
            return float(current)
        except Exception as exc:
            raise ParameterError(f"Failed to read hue: {exc}") from exc

    # ------------------------------------------------------------------
    def _set_hue(self, value: float) -> None:
        try:
            ret = self._camera.MV_CC_SetFloatValue("Hue", value)
            if ret != self._backend._MV_OK:
                raise ParameterError(f"Set Hue failed: 0x{ret:08x}")
        except Exception as exc:
            raise ParameterError(f"Failed to set hue: {exc}") from exc

    # ------------------------------------------------------------------
    @staticmethod
    def _map_parameter_key(key: str) -> str:
        mapping = {
            "exposure_time": "ExposureTime",
            "gain": "Gain",
            "frame_rate": "AcquisitionFrameRate",
            "gamma": "Gamma",
        }
        return mapping.get(key, key)

    # ------------------------------------------------------------------
    def _probe_float_node(self, node_name: str) -> bool:
        value = self._backend._MVCC_FLOATVALUE()
        try:
            ret = self._camera.MV_CC_GetFloatValue(node_name, value)
        except TypeError:
            ret = self._camera.MV_CC_GetFloatValue(node_name.encode("ascii"), value)
        if ret == self._backend._MV_OK:
            return True
        self._backend._logger.debug(
            "Float node %s unavailable (0x%08x) for %s", node_name, ret, self.info.id
        )
        return False

    # ------------------------------------------------------------------
    def start_stream(self) -> None:
        if self._streaming:
            return
        ret = self._camera.MV_CC_StartGrabbing()
        if ret != self._backend._MV_OK:
            raise StreamError(f"MV_CC_StartGrabbing failed: 0x{ret:08x}")
        self._streaming = True

    # ------------------------------------------------------------------
    def stop_stream(self) -> None:
        if not self._streaming:
            return
        ret = self._camera.MV_CC_StopGrabbing()
        if ret != self._backend._MV_OK:
            raise StreamError(f"MV_CC_StopGrabbing failed: 0x{ret:08x}")
        self._streaming = False

    # ------------------------------------------------------------------
    def get_frame(self, timeout_ms: int = 1000) -> Optional[FrameData]:
        if not self._streaming:
            raise StreamError("Stream not started")

        frame = self._backend._MV_FRAME_OUT()
        memset(byref(frame), 0, sizeof(frame))

        buffer_acquired = False
        last_error = None
        for attempt in range(2):
            try:
                ret = self._camera.MV_CC_GetImageBuffer(frame, timeout_ms)
            except TypeError:
                ret = self._camera.MV_CC_GetImageBuffer(byref(frame), timeout_ms)

            if ret == self._backend._MV_OK:
                buffer_acquired = True
                break

            last_error = ret
            if ret in (0x8000000d, 0x80000011):  # timeout codes
                return None
            if ret in (0x80000007,):  # MV_E_PARAMETER seen as transient during start-up
                self._backend._logger.debug(
                    "Transient MV_CC_GetImageBuffer failure 0x%08x on attempt %d for %s",
                    ret,
                    attempt + 1,
                    self.info.id,
                )
                time.sleep(0.01)
                continue
            raise StreamError(f"MV_CC_GetImageBuffer failed: 0x{ret:08x}")

        if not buffer_acquired:
            raise StreamError(f"MV_CC_GetImageBuffer failed: 0x{last_error:08x}")

        try:
            frame_info = frame.stFrameInfo
            width = frame_info.nWidth
            height = frame_info.nHeight
            pixel_type = frame_info.enPixelType
            frame_len = frame_info.nFrameLen

            buffer_ptr = ctypes.cast(frame.pBufAddr, ctypes.POINTER(ctypes.c_ubyte * frame_len))
            raw = np.frombuffer(buffer_ptr.contents, dtype=np.uint8).copy()

            if pixel_type == self._backend._PixelType_Mono:
                image = raw.reshape(height, width)
                image = np.stack([image] * 3, axis=-1)
            elif pixel_type == self._backend._PixelType_RGB:
                image = raw.reshape(height, width, 3)
            else:
                # Fallback conversion via MV_CC_ConvertPixelType
                image = self._convert_to_rgb(frame, raw)

            metadata = {
                "timestamp": frame_info.nDevTimeStampHigh << 32 | frame_info.nDevTimeStampLow,
                "frame_num": frame_info.nFrameNum,
                "exposure": self.get_parameter("exposure_time"),
                "gain": self.get_parameter("gain"),
            }
            return FrameData(image, **metadata)
        finally:
            if buffer_acquired:
                try:
                    self._camera.MV_CC_FreeImageBuffer(frame)
                except TypeError:
                    self._camera.MV_CC_FreeImageBuffer(byref(frame))

    # ------------------------------------------------------------------
    def _convert_to_rgb(self, frame, raw_buffer: np.ndarray) -> np.ndarray:
        convert_param = self._backend._MV_PIXEL_CONVERT_PARAM()
        frame_info = frame.stFrameInfo
        dst_buffer = np.empty(frame_info.nWidth * frame_info.nHeight * 3, dtype=np.uint8)
        convert_param.nWidth = frame_info.nWidth
        convert_param.nHeight = frame_info.nHeight
        convert_param.pSrcData = frame.pBufAddr
        convert_param.nSrcDataLen = frame_info.nFrameLen
        convert_param.enSrcPixelType = frame_info.enPixelType
        convert_param.enDstPixelType = self._backend._PixelType_RGB
        convert_param.pDstBuffer = dst_buffer.ctypes.data_as(ctypes.c_void_p)
        convert_param.nDstBufferSize = dst_buffer.size

        ret = self._camera.MV_CC_ConvertPixelType(convert_param)
        if ret != self._backend._MV_OK:
            raise StreamError(f"MV_CC_ConvertPixelType failed: 0x{ret:08x}")

        return dst_buffer.reshape(frame_info.nHeight, frame_info.nWidth, 3)
