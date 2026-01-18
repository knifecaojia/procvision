
from typing import Any, Dict

from procvision_algorithm_sdk import BaseAlgorithm, Session, read_image_from_shared_memory


class PvSampleAlgorithm(BaseAlgorithm):
    def __init__(self) -> None:
        super().__init__()
        # TODO: 修改为你的 PID 列表，并确保与 manifest.json 中的 supported_pids 保持一致
        self._supported_pids = ['PID_TO_FILL']
        # TODO: 如需加载模型与重资源，请在 setup() 中实现，并设置 self._model_version

    def get_info(self) -> Dict[str, Any]:
        # 必须返回与 manifest.json 一致的 name/version/supported_pids/steps
        # TODO: 如需增加步骤与参数，请在 steps 中定义 schema（type: int/float/rect/enum/bool/string）
        return {
            "name": "pv_sample",
            "version": "1.0.0",
            "description": "pv_sample 算法包",
            "supported_pids": self._supported_pids,
            "steps": [
                {
                    "index": 0,
                    "name": "示例步骤",
                    "params": [
                        {"key": "threshold", "type": "float", "default": 0.5, "min": 0.0, "max": 1.0}
                    ],
                }
            ],
        }

    def pre_execute(
        self,
        step_index: int,
        pid: str,
        session: Session,
        user_params: Dict[str, Any],
        shared_mem_id: str,
        image_meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        # TODO: 在此实现准备逻辑（如光照检查、模板读取等）
        # 返回结构：{"status":"OK|ERROR","message":"提示信息","debug":{...}}
        if pid not in self._supported_pids:
            return {"status": "ERROR", "message": f"不支持的产品型号: {pid}", "error_code": "1001"}
        img = read_image_from_shared_memory(shared_mem_id, image_meta)
        if img is None:
            return {"status": "ERROR", "message": "图像数据为空", "error_code": "1002"}
        return {"status": "OK", "message": "准备就绪", "debug": {"latency_ms": 0.0}}

    def execute(
        self,
        step_index: int,
        pid: str,
        session: Session,
        user_params: Dict[str, Any],
        shared_mem_id: str,
        image_meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        # TODO: 在此实现核心检测逻辑，并按规范返回 OK/ERROR；业务判定在 data.result_status（OK/NG）
        # NG 时需要提供 data.ng_reason 与 data.defect_rects（最多 20 个）
        img = read_image_from_shared_memory(shared_mem_id, image_meta)
        if img is None:
            return {"status": "ERROR", "message": "图像数据为空", "error_code": "1002"}
        return {"status": "OK", "data": {"result_status": "OK", "defect_rects": [], "debug": {"latency_ms": 0.0}}}
