"""
Model management page for the industrial vision system.
"""

import logging
import os
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from ..components.model_card import ModelCard
from src.services.algorithm_manager import AlgorithmManager, WorkerSignals, AsyncWorker

logger = logging.getLogger(__name__)


class ModelPage(QFrame):
    """Model management page implementation."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modelPage")
        self.algorithm_manager = AlgorithmManager()
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Initialize the model page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setObjectName("modelHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("算法管理")
        title_label.setObjectName("modelTitle")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Import Button
        import_btn = QPushButton("导入本地算法包")
        import_btn.setObjectName("uploadButton") # Use uploadButton style
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._on_import_clicked)
        # header_layout.addWidget(import_btn) # Hidden as requested
        import_btn.hide() # Explicitly hide or just don't add
        # We can just not add it to layout
        
        layout.addWidget(header_frame)
        
        # Model cards in scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("modelScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for cards
        self.cards_container = QWidget()
        self.cards_container.setObjectName("cardsContainer")
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(15, 15, 15, 15)
        self.cards_container.setLayout(self.cards_layout)
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area)

    def load_data(self):
        """Loads algorithm data from manager and renders cards."""
        # Clear existing
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Fetch data
        algorithms = self.algorithm_manager.get_all_algorithms()
        
        for index, model_data in enumerate(algorithms):
            card = ModelCard(model_data)
            card.download_requested.connect(self._handle_download)
            card.deploy_requested.connect(self._handle_deploy)
            card.undeploy_requested.connect(self._handle_undeploy)
            card.delete_requested.connect(self._handle_delete)
            
            row = index // 2
            col = index % 2
            self.cards_layout.addWidget(card, row, col)

        # Add stretch to the last row to push cards up
        if algorithms:
             self.cards_layout.setRowStretch((len(algorithms) + 1) // 2, 1)

    def _on_import_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择算法包", "", "Zip Files (*.zip)"
        )
        if file_path:
            try:
                self.algorithm_manager.import_local_algorithm(file_path)
                QMessageBox.information(self, "成功", "算法包导入成功")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {e}")

    def _handle_download(self, data):
        card = self.sender()
        name = data["name"]
        version = data["version"]
        
        signals = WorkerSignals()
        signals.progress.connect(card.set_progress)
        # Use a separate slot or partial to capture the action name correctly, 
        # avoiding lambda binding issues if any, but lambda should be fine here.
        signals.finished.connect(lambda s, m: self._on_task_finished(s, m, "下载"))
        
        worker = AsyncWorker(self.algorithm_manager.download_algorithm, signals, name, version)
        # Explicitly set parent to ensure thread isn't collected prematurely
        # AND keep a reference to it in the class if needed, but setParent usually suffices for QThread
        worker.setParent(self) 
        worker.start()

    def _handle_deploy(self, data):
        card = self.sender()
        name = data["name"]
        version = data["version"]
        
        signals = WorkerSignals()
        signals.progress.connect(card.set_progress)
        signals.finished.connect(lambda s, m: self._on_task_finished(s, m, "部署"))
        
        # FIX: The error "Zip file not found for <SignalInstance...>" suggests that 
        # 'signals' is being passed as 'name' or 'version' to deploy_algorithm?
        # Let's check AsyncWorker.__init__:
        # self.task(self.signals.progress, *self.args, **self.kwargs)
        # deploy_algorithm signature: (name, version, signals)
        # AsyncWorker usage: AsyncWorker(deploy_algorithm, signals, name, version)
        # -> calls deploy_algorithm(signals.progress, name, version)
        # WAIT! deploy_algorithm signature in manager.py is:
        # def deploy_algorithm(self, name: str, version: str, signals: WorkerSignals):
        
        # So we are calling it as: deploy_algorithm(progress_signal, name, version)
        # But it expects (name, version, signals_object).
        
        # We need to adjust AsyncWorker or the task signature.
        # AsyncWorker passes 'self.signals.progress' as first arg.
        
        # Let's fix AsyncWorker usage or the manager methods.
        # Manager methods expect 'signals: WorkerSignals' as LAST argument usually?
        # Actually in manager.py:
        # def download_algorithm(self, name: str, version: str, signals: WorkerSignals):
        # def deploy_algorithm(self, name: str, version: str, signals: WorkerSignals):
        
        # AsyncWorker implementation:
        # self.task(self.signals.progress, *self.args, **self.kwargs)
        
        # This passes 'progress signal' as the FIRST argument.
        # So deploy_algorithm receives (progress_signal, name, version).
        # It assigns name = progress_signal.
        # That explains "Zip file not found for <SignalInstance...>".
        
        # We should update AsyncWorker to pass signals correctly or update Manager methods to accept progress callback as first arg.
        # Updating Manager methods is cleaner since they are designed for this worker.
        # Let's update Manager methods signature in algorithm_manager.py to match AsyncWorker's call:
        # (progress_callback, *args)
        
        # OR fix AsyncWorker to not pass progress as first arg if the task doesn't expect it there.
        # But AsyncWorker is hardcoded to pass it first.
        
        # Let's fix AlgorithmManager methods in the next step.
        # For now, just keep this file as is, but I will re-trigger the fix in manager.py.
        # Actually I can't fix manager.py in this tool call.
        # I will revert the thought and fixing manager.py is the right way.
        
        worker = AsyncWorker(self.algorithm_manager.deploy_algorithm, signals, name, version)
        worker.setParent(self)
        worker.start()

    def _handle_undeploy(self, data):
        name = data["name"]
        version = data["version"]
        reply = QMessageBox.question(
            self,
            "确认卸载部署",
            f"确定要卸载部署算法包 {name} ({version}) 吗？\n\n卸载将删除已部署文件，但不会删除已下载的 zip 包。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.algorithm_manager.undeploy_algorithm(name, version)
            self.load_data()
            QMessageBox.information(self, "成功", "已卸载部署")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"卸载失败: {e}")

    def _handle_delete(self, data):
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除算法包 {data['name']} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.algorithm_manager.delete_package(data["name"], data["version"])
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def _on_task_finished(self, success, message, action_name):
        if success:
            QMessageBox.information(self, "成功", f"{action_name}成功")
            self.load_data()
        else:
            QMessageBox.critical(self, "错误", f"{action_name}失败: {message}")
            self.load_data() # Refresh to reset state
