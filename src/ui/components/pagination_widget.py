
import logging
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFrame
)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Signal, Qt

logger = logging.getLogger(__name__)

class PaginationWidget(QWidget):
    """
    Custom pagination widget with numbered buttons and jump-to-page functionality.
    """
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_pages = 1
        self.current_page = 1
        self.max_visible_buttons = 5
        
        self.init_ui()

    def init_ui(self):
        """Initialize the layout and components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Container for pagination buttons
        self.buttons_container = QWidget()
        self.buttons_layout = QHBoxLayout(self.buttons_container)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(5)
        
        layout.addWidget(self.buttons_container)
        
        self.update_ui()

    def set_total_pages(self, total: int):
        """Set total pages and refresh UI."""
        self.total_pages = max(1, total)
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        self.update_ui()

    def set_current_page(self, page: int):
        """Set current page (without emitting signal) and refresh UI."""
        self.current_page = max(1, min(page, self.total_pages))
        self.update_ui()

    def _on_page_clicked(self, page):
        """Handle page number button click."""
        if page != self.current_page:
            self.current_page = page
            self.page_changed.emit(self.current_page)
            self.update_ui()

    def _on_prev_clicked(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.page_changed.emit(self.current_page)
            self.update_ui()

    def _on_next_clicked(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.page_changed.emit(self.current_page)
            self.update_ui()
            
    def update_ui(self):
        """Re-render the pagination buttons."""
        # Clear existing buttons
        while self.buttons_layout.count():
            item = self.buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Prev Button
        prev_btn = QPushButton("<")
        prev_btn.setFixedSize(30, 30)
        prev_btn.setEnabled(self.current_page > 1)
        prev_btn.clicked.connect(self._on_prev_clicked)
        self.buttons_layout.addWidget(prev_btn)

        # Logic to show range of pages
        # e.g., 1 ... 4 5 [6] 7 8 ... 20
        start_page = max(1, self.current_page - self.max_visible_buttons // 2)
        end_page = min(self.total_pages, start_page + self.max_visible_buttons - 1)
        
        if end_page - start_page + 1 < self.max_visible_buttons:
            start_page = max(1, end_page - self.max_visible_buttons + 1)

        # First Page
        if start_page > 1:
            self._add_page_button(1)
            if start_page > 2:
                self._add_ellipsis()

        # Middle Pages
        for page in range(start_page, end_page + 1):
            self._add_page_button(page)

        # Last Page
        if end_page < self.total_pages:
            if end_page < self.total_pages - 1:
                self._add_ellipsis()
            self._add_page_button(self.total_pages)

        # Next Button
        next_btn = QPushButton(">")
        next_btn.setFixedSize(30, 30)
        next_btn.setEnabled(self.current_page < self.total_pages)
        next_btn.clicked.connect(self._on_next_clicked)
        self.buttons_layout.addWidget(next_btn)

    def _add_page_button(self, page):
        btn = QPushButton(str(page))
        btn.setFixedSize(30, 30)
        btn.setCheckable(True)
        btn.setChecked(page == self.current_page)
        
        # Style for active/inactive
        if page == self.current_page:
            btn.setObjectName("activePageButton")
        else:
            btn.setObjectName("pageButton")
            
        btn.clicked.connect(lambda checked=False, p=page: self._on_page_clicked(p))
        self.buttons_layout.addWidget(btn)

    def _add_ellipsis(self):
        label = QLabel("...")
        label.setFixedSize(30, 30)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.buttons_layout.addWidget(label)
