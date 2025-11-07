"""
System settings page for the industrial vision system.
"""

import logging
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class SystemPage(QFrame):
    """System settings page implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("systemPage")
        self.init_ui()
        
    def init_ui(self):
        """Initialize the system page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("systemHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("系统设置")
        title_label.setObjectName("systemTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header_frame)
        
        # Server configuration
        server_frame = QFrame()
        server_frame.setObjectName("serverFrame")
        
        server_layout = QVBoxLayout(server_frame)
        server_layout.setContentsMargins(20, 20, 20, 20)
        server_layout.setSpacing(15)
        
        server_title = QLabel("中心服务器配置")
        server_title.setObjectName("sectionTitle")
        
        # Server address
        addr_layout = QHBoxLayout()
        addr_label = QLabel("服务器地址:")
        addr_label.setObjectName("paramLabel")
        addr_input = QLineEdit("192.168.1.100")
        addr_input.setObjectName("paramInput")
        addr_layout.addWidget(addr_label)
        addr_layout.addWidget(addr_input)
        
        # Server port
        port_layout = QHBoxLayout()
        port_label = QLabel("服务器端口:")
        port_label.setObjectName("paramLabel")
        port_input = QLineEdit("8080")
        port_input.setObjectName("paramInput")
        port_layout.addWidget(port_label)
        port_layout.addWidget(port_input)
        
        server_layout.addWidget(server_title)
        server_layout.addLayout(addr_layout)
        server_layout.addLayout(port_layout)
        
        layout.addWidget(server_frame)
        
        # Image storage configuration
        image_frame = QFrame()
        image_frame.setObjectName("imageFrame")
        
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(20, 20, 20, 20)
        image_layout.setSpacing(15)
        
        image_title = QLabel("图像存储配置")
        image_title.setObjectName("sectionTitle")
        
        # Image save path
        img_path_layout = QHBoxLayout()
        img_path_label = QLabel("图像保存位置:")
        img_path_label.setObjectName("paramLabel")
        img_path_input = QLineEdit("C:\\VisionData\\Images")
        img_path_input.setObjectName("paramInput")
        # Removed fixed width to allow adaptive width
        img_browse_btn = QPushButton("浏览")
        img_browse_btn.setObjectName("browseButton")
        img_browse_btn.setFixedWidth(80)
        img_browse_btn.setFixedHeight(32)  # Increased button height
        img_path_layout.addWidget(img_path_label)
        img_path_layout.addWidget(img_path_input)
        img_path_layout.addWidget(img_browse_btn)
        
        # Image retention days
        img_retention_layout = QHBoxLayout()
        img_retention_label = QLabel("图像保留时间（天）:")
        img_retention_label.setObjectName("paramLabel")
        img_retention_input = QLineEdit("30")
        img_retention_input.setObjectName("paramInput")
        img_retention_layout.addWidget(img_retention_label)
        img_retention_layout.addWidget(img_retention_input)
        
        image_layout.addWidget(image_title)
        image_layout.addLayout(img_path_layout)
        image_layout.addLayout(img_retention_layout)
        
        layout.addWidget(image_frame)
        
        # Log storage configuration
        log_frame = QFrame()
        log_frame.setObjectName("logFrame")
        
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.setSpacing(15)
        
        log_title = QLabel("日志存储配置")
        log_title.setObjectName("sectionTitle")
        
        # Log save path
        log_path_layout = QHBoxLayout()
        log_path_label = QLabel("日志保存位置:")
        log_path_label.setObjectName("paramLabel")
        log_path_input = QLineEdit("C:\\VisionData\\Logs")
        log_path_input.setObjectName("paramInput")
        # Removed fixed width to allow adaptive width
        log_browse_btn = QPushButton("浏览")
        log_browse_btn.setObjectName("browseButton")
        log_browse_btn.setFixedWidth(80)
        log_browse_btn.setFixedHeight(32)  # Increased button height
        log_path_layout.addWidget(log_path_label)
        log_path_layout.addWidget(log_path_input)
        log_path_layout.addWidget(log_browse_btn)
        
        # Log retention days
        log_retention_layout = QHBoxLayout()
        log_retention_label = QLabel("日志保留时间（天）:")
        log_retention_label.setObjectName("paramLabel")
        log_retention_input = QLineEdit("90")
        log_retention_input.setObjectName("paramInput")
        log_retention_layout.addWidget(log_retention_label)
        log_retention_layout.addWidget(log_retention_input)
        
        log_layout.addWidget(log_title)
        log_layout.addLayout(log_path_layout)
        log_layout.addLayout(log_retention_layout)
        
        layout.addWidget(log_frame)
        
        # Save button - moved to bottom and adjusted width
        save_btn_layout = QHBoxLayout()
        save_btn_layout.addStretch()
        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("saveButton")
        save_btn.setFixedHeight(40)
        save_btn.setFixedWidth(120)  # Set normal width
        save_btn_layout.addWidget(save_btn)
        save_btn_layout.addStretch()
        
        layout.addLayout(save_btn_layout)
        layout.addStretch()