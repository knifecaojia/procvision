"""
Camera settings page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QGridLayout, QSizePolicy,
    QToolButton
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class CameraPage(QFrame):
    """Camera settings page implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cameraPage")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the camera page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("cameraHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("相机设置")
        title_label.setObjectName("cameraTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Main content - Vertical layout dividing top and bottom sections
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)
        
        # Top section - Horizontal layout with preview on left and parameters on right
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        
        # Left side - Camera preview and controls
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(10)
        
        # Camera control toolbar row
        controls_frame = QFrame()
        controls_frame.setObjectName("previewToolbar")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 0, 8, 0)
        controls_layout.setSpacing(2)
        controls_frame.setFixedHeight(45)

        control_specs = [
            ("connect", "连接相机", "⦿"),
            ("disconnect", "断开连接", "⦸"),
            ("startPreview", "开始预览", "▶"),
            ("stopPreview", "停止预览", "■"),
            ("screenshot", "截图", "⎙"),
            ("record", "录像", "●"),
        ]

        for control_id, tooltip, symbol in control_specs:
            button = QToolButton()
            button.setObjectName("previewToolButton")
            button.setProperty("controlId", control_id)
            button.setToolTip(tooltip)
            button.setText(symbol)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedSize(32, 32)
            button.setStyleSheet("font-size: 24px;")
            controls_layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)

        controls_layout.addStretch()
        
        # Camera preview area - Will expand to fill available space
        preview_label = QLabel("相机预览区域")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_label.setObjectName("previewLabel")
        preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        preview_layout.addWidget(controls_frame)
        preview_layout.addWidget(preview_label)
        
        # Right side - Camera parameters
        params_frame = QFrame()
        params_frame.setObjectName("paramsFrame")
        params_frame.setFixedWidth(300)  # Fixed width for parameter panel
        
        params_layout = QVBoxLayout(params_frame)
        params_layout.setContentsMargins(20, 20, 20, 20)
        params_layout.setSpacing(15)
        
        params_title = QLabel("相机参数")
        params_title.setObjectName("paramsTitle")
        
        # Exposure time
        exposure_layout = QHBoxLayout()
        exposure_label = QLabel("曝光时间 (μs):")
        exposure_label.setObjectName("paramLabel")
        exposure_input = QLineEdit("5000")
        exposure_input.setObjectName("paramInput")
        exposure_layout.addWidget(exposure_label)
        exposure_layout.addWidget(exposure_input)
        exposure_layout.addStretch()
        
        # Gain
        gain_layout = QHBoxLayout()
        gain_label = QLabel("增益:")
        gain_label.setObjectName("paramLabel")
        gain_input = QLineEdit("1.0")
        gain_input.setObjectName("paramInput")
        gain_layout.addWidget(gain_label)
        gain_layout.addWidget(gain_input)
        gain_layout.addStretch()
        
        # Resolution
        resolution_layout = QHBoxLayout()
        resolution_label = QLabel("分辨率:")
        resolution_label.setObjectName("paramLabel")
        resolution_combo = QComboBox()
        resolution_combo.addItems(["1920 × 1080", "1280 × 720", "640 × 480"])
        resolution_combo.setObjectName("paramCombo")
        resolution_layout.addWidget(resolution_label)
        resolution_layout.addWidget(resolution_combo)
        resolution_layout.addStretch()
        
        # FPS
        fps_layout = QHBoxLayout()
        fps_label = QLabel("帧率 (FPS):")
        fps_label.setObjectName("paramLabel")
        fps_input = QLineEdit("30")
        fps_input.setObjectName("paramInput")
        fps_layout.addWidget(fps_label)
        fps_layout.addWidget(fps_input)
        fps_layout.addStretch()
        
        # Apply button
        apply_btn = QPushButton("应用参数")
        apply_btn.setObjectName("applyButton")
        apply_btn.setFixedHeight(40)
        
        params_layout.addWidget(params_title)
        params_layout.addLayout(exposure_layout)
        params_layout.addLayout(gain_layout)
        params_layout.addLayout(resolution_layout)
        params_layout.addLayout(fps_layout)
        params_layout.addWidget(apply_btn)
        params_layout.addStretch()
        
        top_layout.addWidget(preview_frame)
        top_layout.addWidget(params_frame)
        
        # Bottom section - Camera status info
        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_frame.setFixedHeight(110)  # Fixed height for status panel (increased by 30px)
        
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 10, 15, 10)
        status_layout.setSpacing(8)
        
        status_title = QLabel("相机状态")
        status_title.setObjectName("paramsTitle")
        status_title.setFixedHeight(25)  # Increased height for better visibility
        
        # Status details
        status_grid = QGridLayout()
        status_grid.setSpacing(10)  # Increased spacing for better readability
        status_grid.setContentsMargins(0, 0, 0, 0)
        
        cam_model_label = QLabel("相机型号:")
        cam_model_label.setObjectName("paramLabel")
        cam_model_value = QLabel("MV-CE060-10GM")
        cam_model_value.setObjectName("paramValue")
        cam_model_value.setMinimumWidth(120)  # Ensure enough space for value
        
        cam_status_label = QLabel("连接状态:")
        cam_status_label.setObjectName("paramLabel")
        cam_status_value = QLabel("未连接")
        cam_status_value.setObjectName("paramValue")
        cam_status_value.setMinimumWidth(80)  # Ensure enough space for value
        
        cam_temp_label = QLabel("温度:")
        cam_temp_label.setObjectName("paramLabel")
        cam_temp_value = QLabel("38.5°C")
        cam_temp_value.setObjectName("paramValue")
        cam_temp_value.setMinimumWidth(60)  # Ensure enough space for value
        
        cam_fps_label = QLabel("实际帧率:")
        cam_fps_label.setObjectName("paramLabel")
        cam_fps_value = QLabel("0 FPS")
        cam_fps_value.setObjectName("paramValue")
        cam_fps_value.setMinimumWidth(60)  # Ensure enough space for value
        
        status_grid.addWidget(cam_model_label, 0, 0)
        status_grid.addWidget(cam_model_value, 0, 1)
        status_grid.addWidget(cam_status_label, 0, 2)
        status_grid.addWidget(cam_status_value, 0, 3)
        status_grid.addWidget(cam_temp_label, 1, 0)
        status_grid.addWidget(cam_temp_value, 1, 1)
        status_grid.addWidget(cam_fps_label, 1, 2)
        status_grid.addWidget(cam_fps_value, 1, 3)
        
        status_layout.addWidget(status_title)
        status_layout.addLayout(status_grid)
        status_layout.addStretch()
        
        main_layout.addLayout(top_layout)
        main_layout.addWidget(status_frame)
        
        layout.addLayout(main_layout)
