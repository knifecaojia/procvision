"""
Assembly guidance and inspection page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
import json
from pathlib import Path
import importlib.util
import sys
from ..components.process_card import ProcessCard
from ..windows.process_execution_window import ProcessExecutionWindow

logger = logging.getLogger(__name__)


class ProcessPage(QFrame):
    """Assembly guidance and inspection page implementation."""

    def __init__(self, parent=None, camera_service=None):
        super().__init__(parent)
        self.setObjectName("processPage")
        self.camera_service = camera_service
        self.init_ui()
        
    def init_ui(self):
        """Initialize the process page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("processHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("装配引导与检测")
        title_label.setObjectName("processTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Process cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("processScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for cards
        cards_container = QWidget()
        cards_container.setObjectName("cardsContainer")
        # cards_layout will be created later as QGridLayout
        
        base_dir = Path(__file__).resolve().parents[3] / "3rd" / "assembly_direction_checker"
        excel_dir = base_dir / "data" / "process_excel"
        external_infos = []
        try:
            pids = sorted([p.stem for p in excel_dir.glob("*.xlsx")] + [p.stem for p in excel_dir.glob("*.xls")])
            pids = [pid for pid in pids if not pid.startswith("~$")]
            if pids:
                logger.info(f"Discovered external pids: {', '.join(pids)}")
                sys.path.insert(0, str(base_dir))
                third_src = base_dir / "src"
                if third_src.exists():
                    sys.path.insert(0, str(third_src))
                    try:
                        pkg = sys.modules.get("src")
                        if pkg is not None and hasattr(pkg, "__path__"):
                            if str(third_src) not in pkg.__path__:
                                pkg.__path__.insert(0, str(third_src))
                    except Exception:
                        pass
                inner_dir = base_dir / "assembly_direction_checker"
                if inner_dir.exists():
                    sys.path.insert(0, str(inner_dir))
                spec = importlib.util.spec_from_file_location("main_findal", str(base_dir / "main_findal.py"))
                module = importlib.util.module_from_spec(spec)
                assert spec is not None and spec.loader is not None
                spec.loader.exec_module(module)
                for pid in pids:
                    try:
                        info = module.get_info(pid)
                        info["pid"] = pid
                        external_infos.append(info)
                    except Exception as e2:
                        logger.error(f"Failed to load external info for pid {pid}: {e2}")
        except Exception as e:
            logger.error(f"Failed to load external process info: {e}")
            try:
                candidates = [base_dir / f"process_info_{pid}.json" for pid in pids] if 'pids' in locals() else []
                for candidate in candidates:
                    if candidate.exists():
                        info = json.loads(candidate.read_text(encoding="utf-8"))
                        info["pid"] = candidate.stem.split("_")[-1]
                        external_infos.append(info)
                        logger.info(f"Loaded external process info from JSON: {candidate.name}")
            except Exception as e2:
                logger.error(f"Failed to fallback load external JSON: {e2}")

        processes_data_simulated = [
            {
                "algorithm_name": "视觉装配引导与质检算法（模拟）",
                "algorithm_version": "v1.0.1",
                "summary": "本算法用于10287产品的装配引导与关键步骤的缺陷检测。",
                "pid": "SIM-10287",
                "steps": [
                    {
                        "step_number": 1,
                        "step_name": "安装连接器",
                        "operation_guide": "开始第 1 步：请装配『连接器』，方向为：下",
                        "quality_standard": "方向为：下",
                        "object": "连接器",
                        "direction": "下"
                    },
                    {
                        "step_number": 2,
                        "step_name": "安装航向铭牌",
                        "operation_guide": "开始第 2 步：请装配『航向铭牌』，方向为：左",
                        "quality_standard": "方向为：左",
                        "object": "航向铭牌",
                        "direction": "左"
                    },
                    {
                        "step_number": 3,
                        "step_name": "安装铭牌",
                        "operation_guide": "开始第 3 步：请装配『铭牌』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "铭牌",
                        "direction": "正"
                    },
                    {
                        "step_number": 4,
                        "step_name": "安装X1铭牌",
                        "operation_guide": "开始第 4 步：请装配『X1铭牌』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "X1铭牌",
                        "direction": "正"
                    }
                ]
            },
            {
                "algorithm_name": "PCB 装配引导算法（模拟）",
                "algorithm_version": "v1.2.0",
                "summary": "用于 PCB 装配过程中的元件放置引导与方向确认。",
                "pid": "SIM-PCB-001",
                "steps": [
                    {
                        "step_number": 1,
                        "step_name": "安装电容 C101",
                        "operation_guide": "开始第 1 步：请装配『电容 C101』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "电容 C101",
                        "direction": "正"
                    },
                    {
                        "step_number": 2,
                        "step_name": "安装连接器 J101",
                        "operation_guide": "开始第 2 步：请装配『连接器 J101』，方向为：下",
                        "quality_standard": "方向为：下",
                        "object": "连接器 J101",
                        "direction": "下"
                    }
                ]
            },
            {
                "algorithm_name": "机械总成装配算法（模拟）",
                "algorithm_version": "v0.9.4",
                "summary": "用于机械总成的装配引导，含方向与紧固标准。",
                "pid": "SIM-MECH-001",
                "steps": [
                    {
                        "step_number": 1,
                        "step_name": "安装支架",
                        "operation_guide": "开始第 1 步：请装配『支架』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "支架",
                        "direction": "正"
                    },
                    {
                        "step_number": 2,
                        "step_name": "压入轴承",
                        "operation_guide": "开始第 2 步：请装配『轴承』，方向为：下",
                        "quality_standard": "方向为：下",
                        "object": "轴承",
                        "direction": "下"
                    },
                    {
                        "step_number": 3,
                        "step_name": "紧固螺钉",
                        "operation_guide": "开始第 3 步：请装配『螺钉』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "螺钉",
                        "direction": "正"
                    }
                ]
            },
            {
                "algorithm_name": "包装与打码检测算法（模拟）",
                "algorithm_version": "v1.3.2",
                "summary": "用于包装流程的标签、打码与扫码校验。",
                "pid": "SIM-PKG-001",
                "steps": [
                    {
                        "step_number": 1,
                        "step_name": "贴标签",
                        "operation_guide": "开始第 1 步：请装配『标签』，方向为：左",
                        "quality_standard": "方向为：左",
                        "object": "标签",
                        "direction": "左"
                    },
                    {
                        "step_number": 2,
                        "step_name": "打码",
                        "operation_guide": "开始第 2 步：请进行『打码』，方向为：正",
                        "quality_standard": "字符清晰完整",
                        "object": "打码",
                        "direction": "正"
                    },
                    {
                        "step_number": 3,
                        "step_name": "扫描校验",
                        "operation_guide": "开始第 3 步：请执行『扫码校验』",
                        "quality_standard": "扫码通过",
                        "object": "二维码",
                        "direction": "正"
                    }
                ]
            },
            {
                "algorithm_name": "航电组件装配引导算法（模拟）",
                "algorithm_version": "v2.0.0",
                "summary": "用于航电组件的装配与线缆连接引导。",
                "pid": "SIM-AVN-001",
                "steps": [
                    {
                        "step_number": 1,
                        "step_name": "安装航电板",
                        "operation_guide": "开始第 1 步：请装配『航电板』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "航电板",
                        "direction": "正"
                    },
                    {
                        "step_number": 2,
                        "step_name": "连接排线",
                        "operation_guide": "开始第 2 步：请装配『排线』，方向为：右",
                        "quality_standard": "方向为：右",
                        "object": "排线",
                        "direction": "右"
                    },
                    {
                        "step_number": 3,
                        "step_name": "紧固螺钉",
                        "operation_guide": "开始第 3 步：请装配『螺钉』，方向为：正",
                        "quality_standard": "方向为：正",
                        "object": "螺钉",
                        "direction": "正"
                    }
                ]
            }
        ]
        processes_data = external_infos + processes_data_simulated
        
        # Create and add cards in single column
        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)
        cards_layout.setContentsMargins(20, 20, 20, 20)

        for index, process_data in enumerate(processes_data):
            card = ProcessCard(process_data)
            card.start_process_clicked.connect(self.on_start_process)
            cards_layout.addWidget(card, index, 0)

        # Add stretch to push cards up
        cards_layout.setRowStretch(len(processes_data), 1)

        cards_container.setLayout(cards_layout)

        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area)

    def on_start_process(self, process_data: dict):
        """Handle start process signal from process card."""
        logger.info(f"Launching process execution window for: {process_data['name']}")

        # Create and show process execution window with camera service
        self.execution_window = ProcessExecutionWindow(
            process_data,
            None,
            camera_service=self.camera_service
        )
        self.execution_window.show_centered()

        logger.info("Process execution window launched")
