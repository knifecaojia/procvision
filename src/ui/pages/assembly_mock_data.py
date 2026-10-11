from typing import Any, Dict

from src.services.task_payload_mapper import normalize_material_list


def build_mock_process_data(
    operator_name: str,
    with_materials: bool = True,
    with_final_check: bool = True,
) -> Dict[str, Any]:
    task_no = "MOCK-TEST-001"
    material_list = normalize_material_list(build_mock_material_items(with_materials))
    steps_detail = [
        {
            "step_number": 1,
            "step_code": "MOCK-STEP-01",
            "step_name": "取料定位",
            "operation_guide": "放置测试件并确认定位区域，核对当前工单与物料。",
        },
        {
            "step_number": 2,
            "step_code": "MOCK-STEP-02",
            "step_name": "主件装配",
            "operation_guide": "根据引导完成主件装配，注意易错料方向。",
        },
        {
            "step_number": 3,
            "step_code": "MOCK-STEP-03",
            "step_name": "辅件复核",
            "operation_guide": "复核辅件数量、位号和方向，准备进入检测。",
        },
        {
            "step_number": 4,
            "step_code": "MOCK-STEP-04",
            "step_name": "外观检测",
            "operation_guide": "触发模拟检测，观察 PASS/FAIL 与步骤流转。",
        },
        {
            "step_number": 5,
            "step_code": "MOCK-STEP-05",
            "step_name": "完成确认",
            "operation_guide": "确认本轮任务完成，验证最终步骤可继续流转。",
        },
    ]
    if with_final_check:
        steps_detail.append({
            "step_number": 99,
            "step_code": "99",
            "step_name": "终检",
            "operation_guide": "执行终检，确认整单检测结果。",
        })
    final_check_flag = 1 if with_final_check else 0
    material_label = "有物料" if with_materials else "无物料"
    final_check_label = "有终检" if with_final_check else "无终检"
    raw_work_order = {
        "work_order_code": task_no,
        "craft_code": "MOCK",
        "craft_name": "隐藏测试流程",
        "process_code": "TEST",
        "process_name": "模拟检测",
        "process_desc": "用于本地验证启动前提醒、右侧物料信息和模拟检测流程。",
        "prod_order_no": "MOCK-PO-001",
        "algorithm_code": "SIM-HIDDEN-001",
        "algorithm_name": "模拟检测流程",
        "algorithm_version": "mock",
        "final_check_flag": final_check_flag,
        "step_infos": steps_detail,
        "material_list": material_list,
    }
    return {
        "name": task_no,
        "title": "隐藏测试流程（Mock）",
        "version": "mock",
        "steps": len(steps_detail),
        "work_order_code": task_no,
        "algorithm_name": "模拟检测流程",
        "algorithm_version": "mock",
        "operator_name": operator_name,
        "worker_name": operator_name,
        "summary": "Hidden Mock Launch",
        "step_infos": steps_detail,
        "steps_detail": steps_detail,
        "pid": "SIM-HIDDEN-001",
        "display_pid": "SIM-HIDDEN-001",
        "task_no": task_no,
        "craft_no": "MOCK",
        "craft_code": "MOCK",
        "craft_name": f"隐藏测试流程-{material_label}-{final_check_label}",
        "craft_version": "mock",
        "process_code": "TEST",
        "process_name": "模拟检测",
        "process_desc": "用于本地验证启动前提醒、右侧物料信息和模拟检测流程。",
        "prod_order_no": "MOCK-PO-001",
        "material_list": material_list,
        "final_check_flag": final_check_flag,
        "allow_mock_camera": True,
        "mock_camera_text": "MOCK CAM",
        "algorithm_code": "SIM-HIDDEN-001",
        "raw_work_order": raw_work_order,
    }


def build_mock_material_items(with_materials: bool) -> list[dict]:
    if not with_materials:
        return []
    return [
        {
            "assembly_number": "A01",
            "position_number": "U1",
            "model_no": "TX-MAIN-01",
            "polarity_direction": "缺口朝上",
            "material_no": "9000000929403",
            "material_name": "主控芯片",
            "material_quantity": 1,
            "material_unit": "件",
            "error_prevention_mark": "错",
        },
        {
            "assembly_number": "A02",
            "position_number": "C3/C4",
            "model_no": "CAP-10UF",
            "polarity_direction": "白线朝右",
            "material_no": "9000000929404",
            "material_name": "电解电容",
            "material_quantity": 2,
            "material_unit": "件",
            "error_prevention_mark": "",
        },
        {
            "assembly_number": "A03",
            "position_number": "R12/R13/R14",
            "model_no": "RES-4K7-1%-0603",
            "polarity_direction": "无方向要求",
            "material_no": "9000000929405",
            "material_name": "精密电阻组件",
            "material_quantity": 3,
            "material_unit": "件",
            "error_prevention_mark": "",
        },
        {
            "assembly_number": "A04",
            "position_number": "J1",
            "model_no": "CONN-USB-TYPEC-16P",
            "polarity_direction": "开口朝外壳右侧，注意贴合边缘",
            "material_no": "9000000929406",
            "material_name": "Type-C 接口座",
            "material_quantity": 1,
            "material_unit": "件",
            "error_prevention_mark": "方向易错",
        },
        {
            "assembly_number": "A05",
            "position_number": "D5",
            "model_no": "LED-RED-0603-HL",
            "polarity_direction": "三角丝印对应负极，灯珠缺口朝左上",
            "material_no": "9000000929407",
            "material_name": "状态指示灯",
            "material_quantity": 1,
            "material_unit": "件",
            "error_prevention_mark": "",
        },
        {
            "assembly_number": "A06",
            "position_number": "U7",
            "model_no": "DRV-MOTOR-48PIN-QFN",
            "polarity_direction": "1脚圆点朝右下，芯片文字正向可读",
            "material_no": "9000000929408",
            "material_name": "电机驱动控制芯片长名称测试项",
            "material_quantity": 1,
            "material_unit": "件",
            "error_prevention_mark": "错",
        },
        {
            "assembly_number": "A07",
            "position_number": "TP1/TP2/TP3/TP4",
            "model_no": "TEST-PAD-GOLD",
            "polarity_direction": "无方向要求",
            "material_no": "9000000929409",
            "material_name": "测试焊盘保护片",
            "material_quantity": 4,
            "material_unit": "片",
            "error_prevention_mark": "",
        },
        {
            "assembly_number": "A08",
            "position_number": "L2",
            "model_no": "IND-22UH-SMD-LARGE",
            "polarity_direction": "顶部丝印需与板上白框长边平行",
            "material_no": "9000000929410",
            "material_name": "功率电感",
            "material_quantity": 1,
            "material_unit": "件",
            "error_prevention_mark": "",
        },
        {
            "assembly_number": "A09",
            "position_number": "F1",
            "model_no": "FUSE-RESET-1A-1206",
            "polarity_direction": "保险丝文字朝上，靠近输入端一侧安装",
            "material_no": "9000000929411",
            "material_name": "可恢复保险丝",
            "material_quantity": 1,
            "material_unit": "件",
            "error_prevention_mark": "复核",
        },
        {
            "assembly_number": "A10",
            "position_number": "CN8-LEFT-SIDE-EXTENSION",
            "model_no": "CABLE-HARNESS-POWER-SIGNAL-MIXED",
            "polarity_direction": "线束卡扣朝外，红线靠板边，插入到底后轻拉确认锁止",
            "material_no": "9000000929412",
            "material_name": "外接电源与信号混合线束总成长文本滚动测试项",
            "material_quantity": 1,
            "material_unit": "套",
            "error_prevention_mark": "",
        },
    ]
