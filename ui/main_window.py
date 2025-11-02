from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QToolBar, QFileDialog,
    QStatusBar, QLabel, QInputDialog, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QSpacerItem, QSizePolicy, QStyle, QSystemTrayIcon, QMenu,
    QApplication, QDialog, QDialogButtonBox, QComboBox, QTextEdit,
    QListWidget, QListWidgetItem, QProgressBar, QSpinBox, QLineEdit,
    QCheckBox,
    QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtGui import QIcon, QFont, QAction, QKeySequence, QColor
from PyQt6.QtCore import Qt, QSize, QDateTime, QTimer, QEvent, pyqtSignal, QEasingCurve, QPropertyAnimation, QThread
from ui.tabs.dashboard import DashboardTab
from ui.tabs.patient import PatientTab
from ui.tabs.order import OrderTab
from ui.tabs.test import TestTab
from ui.tabs.result import ResultTab
from ui.tabs.user import UserTab
from ui.tabs.report import ReportTab
from ui.tabs.archive import ArchiveTab
from config import load_config, save_config
import csv
import os
import logging
from datetime import datetime
import atexit

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchDialog(QDialog):
    def __init__(self, parent, search_results):
        super().__init__(parent)
        self.setWindowTitle("Search Results")
        self.setModal(False)
        self.resize(700, 500)
        
        self.setStyleSheet("""
            QDialog {
                background: #e6f3ff;
                border-radius: 12px;
            }
            QListWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                padding: 5px;
                font-size: 14px;
                color: #2c3e50;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #2471a3);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Search Results")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 10px 0;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.results_list = QListWidget()
        for category, items in search_results.items():
            category_item = QListWidgetItem(f"📁 {category.upper()}")
            category_item.setBackground(QColor(52, 152, 219))
            category_item.setForeground(QColor(255, 255, 255))
            category_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results_list.addItem(category_item)
            
            for item in items:
                list_item = QListWidgetItem(f"   📄 {item}")
                list_item.setData(Qt.ItemDataRole.UserRole, (category, item))
                self.results_list.addItem(list_item)
        
        layout.addWidget(self.results_list)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

class GlassFrame(QFrame):
    # class-level flag to control glass vs solid styling
    use_glass = False

    GLASS_STYLE = """
        GlassFrame {
            background: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
        }
    """

    SOLID_STYLE = """
        GlassFrame {
            background-color: #ffffff;
            border: 1px solid #e0e4e7;
            border-radius: 12px;
        }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # apply the current global style
        self.setStyleSheet(self.get_style())

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    @classmethod
    def get_style(cls):
        return cls.GLASS_STYLE if cls.use_glass else cls.SOLID_STYLE

    @classmethod
    def set_use_glass(cls, enabled: bool):
        cls.use_glass = bool(enabled)
        # update existing instances
        try:
            for w in QApplication.allWidgets():
                if isinstance(w, GlassFrame):
                    w.setStyleSheet(cls.get_style())
        except Exception:
            pass

class MainWindow(QMainWindow):
    ICON_PATH = "icons/"

    TAB_CONFIG = [
        (DashboardTab, "dashboard_icon.png", "Dashboard", "dashboardTab", ["admin", "user"]),
        (PatientTab,   "patient_icon.png",   "Patients",  "patientTab",   ["admin", "user"]),
        (OrderTab,     "order_icon.png",     "Orders",    "orderTab",     ["admin", "user"]),
        (TestTab,      "test_icon.png",      "Tests",     "testTab",      ["admin"]),
        (ResultTab,    "result_icon.png",    "Results",   "resultTab",    ["admin", "user"]),
        (UserTab,      "user_icon.png",      "Users",     "userTab",      ["admin"]),
        (ArchiveTab,   "archive_icon.png",   "Archive",   "archiveTab",   ["admin"]),
        (ReportTab,    "report_icon.png",    "Reports",   "reportTab",    ["admin", "user"]),
    ]

    LIGHT_BLUE_STYLESHEET = """
    /* Light Blue Theme */
    QMainWindow, QDialog, QWidget {
        background: #e6f3ff;
        color: #000000;
    }
    
    QToolBar {
        background: #cce6ff;
        border: none;
        padding: 8px;
        spacing: 10px;
        border-bottom: 2px solid #007bff;
    }
    
    QPushButton {
        background: #007bff;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
    }
    
    QPushButton:hover {
        background: #0056b3;
    }
    
    QTabWidget::pane {
        border: 1px solid #b3d9ff;
        background: #ffffff;
        border-radius: 6px;
    }
    
    QTabBar::tab {
        background: #cce6ff;
        color: #000000;
        border: 1px solid #b3d9ff;
        padding: 8px 16px;
        margin: 2px;
        border-radius: 6px 6px 0 0;
    }
    
    QTabBar::tab:selected {
        background: #ffffff;
        border-bottom: none;
        color: #007bff;
    }
    
    QLineEdit, QTextEdit, QComboBox {
        background: #ffffff;
        border: 1px solid #b3d9ff;
        border-radius: 4px;
        padding: 6px;
        color: #000000;
    }
    
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
        border: 2px solid #007bff;
    }
    
    QLabel {
        color: #000000;
    }
    
    QTableWidget {
        background: #ffffff;
        border: 1px solid #b3d9ff;
        gridline-color: #e6f3ff;
    }
    
    QTableWidget::item:selected {
        background: #cce6ff;
        color: #000000;
    }
    
    QHeaderView::section {
        background: #cce6ff;
        color: #000000;
        border: none;
        padding: 6px;
    }
    
    QStatusBar {
        background: #cce6ff;
        color: #000000;
    }
    
    QMessageBox {
        background: #e6f3ff;
        color: #000000;
    }
    
    QToolBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1a237e, stop:1 #283593);
        border: none;
        padding: 8px;
        spacing: 10px;
        border-bottom: 3px solid #5c6bc0;
    }
    
    QToolBar::separator {
        background-color: #5c6bc0;
        width: 2px;
        margin: 5px 8px;
    }
    
    QToolButton, QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3949ab, stop:1 #3f51b5);
        color: #ffffff;
        border: 1px solid #5c6bc0;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 0 3px;
        font-weight: bold;
        font-size: 13px;
        min-height: 20px;
    }
    
    QToolButton:hover, QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #5c6bc0, stop:1 #7986cb);
        border: 1px solid #9fa8da;
        color: #ffffff;
    }
    
    QToolButton:pressed, QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2980b9, stop:1 #2471a3);
    }
    
    QStatusBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ecf0f1, stop:1 #d6dbdf);
        color: #2c3e50;
        border-top: 2px solid #3498db;
        padding: 5px;
    }
    
    QTabWidget::pane {
        border: none;
        background: #ffffff;
        border-radius: 12px;
        margin: 8px;
        border: 1px solid #e0e4e7;
    }
    
    QTabBar::tab {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #f8f9fa, stop:1 #e9ecef);
        color: #5a6c7d;
        border: none;
        border-bottom: 3px solid transparent;
        padding: 12px 20px;
        margin-right: 2px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        min-width: 100px;
    }
    
    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:1 #f8f9fa);
        color: #3498db;
        border-bottom: 3px solid #3498db;
    }
    
    QTabBar::tab:hover:!selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #e9ecef, stop:1 #dee2e6);
        color: #2c3e50;
    }
    
    QTabBar::tab[dashboardTab="true"]:selected { 
        border-bottom-color: #3498db;
        color: #3498db;
    }
    
    QTabBar::tab[patientTab="true"]:selected { 
        border-bottom-color: #2ecc71;
        color: #27ae60;
    }
    
    QTabBar::tab[orderTab="true"]:selected { 
        border-bottom-color: #e74c3c;
        color: #c0392b;
    }
    
    QTabBar::tab[testTab="true"]:selected { 
        border-bottom-color: #e67e22;
        color: #d35400;
    }
    
    QTabBar::tab[resultTab="true"]:selected { 
        border-bottom-color: #f1c40f;
        color: #f39c12;
    }
    
    QTabBar::tab[userTab="true"]:selected { 
        border-bottom-color: #9b59b6;
        color: #8e44ad;
    }
    
    QTabBar::tab[reportTab="true"]:selected { 
        border-bottom-color: #1abc9c;
        color: #16a085;
    }
    
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3498db, stop:1 #2980b9);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 13px;
    }
    
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2980b9, stop:1 #2471a3);
    }
    
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2471a3, stop:1 #1f618d);
    }
    
    QLineEdit {
        background: #ffffff;
        border: 2px solid #e0e4e7;
        border-radius: 8px;
        padding: 10px 15px;
        font-size: 14px;
        color: #2c3e50;
        selection-background-color: #3498db;
    }
    
    QLineEdit:focus {
        border: 2px solid #3498db;
        background: rgba(255, 255, 255, 0.95);
    }
    
    QLineEdit::placeholder {
        color: #95a5a6;
        font-style: italic;
    }
    
    QComboBox {
        background: rgba(255, 255, 255, 0.9);
        border: 2px solid #e0e4e7;
        border-radius: 8px;
        padding: 8px 15px;
        min-width: 6em;
        color: #2c3e50;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 30px;
    }
    
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #7f8c8d;
        width: 0px;
        height: 0px;
    }
    
    QComboBox QAbstractItemView {
        background: white;
        border: 1px solid #e0e4e7;
        border-radius: 8px;
        selection-background-color: #3498db;
        selection-color: white;
    }
    
    QProgressBar {
        border: 2px solid #e0e4e7;
        border-radius: 8px;
        text-align: center;
        color: #2c3e50;
        background: rgba(255, 255, 255, 0.9);
    }
    
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3498db, stop:1 #2980b9);
        border-radius: 6px;
    }
    
    QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus {
        outline: 2px solid #3498db;
        outline-offset: 2px;
    }
    
    GlassFrame {
        /* Non-transparent glass substitute for readability */
        background-color: #ffffff;
        border: 1px solid #e0e4e7;
        border-radius: 12px;
    }
    """

    PREMIUM_DARK_STYLESHEET = """
    /* Premium Dark Theme */
    QMainWindow {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460);
        color: #ecf0f1;
    }
    
    QToolBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0f3460, stop:1 #16213e);
        border: none;
        padding: 8px;
        spacing: 10px;
        border-bottom: 3px solid #3498db;
    }
    
    QToolBar::separator {
        background-color: rgba(255, 255, 255, 0.2);
        width: 1px;
        margin: 5px 8px;
    }
    
    QToolButton, QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(52, 152, 219, 0.3), stop:1 rgba(41, 128, 185, 0.2));
        color: #ecf0f1;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        padding: 8px 12px;
        margin: 0 3px;
        font-weight: 500;
        min-height: 20px;
    }
    
    QToolButton:hover, QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(52, 152, 219, 0.6), stop:1 rgba(41, 128, 185, 0.5));
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    QToolButton:pressed, QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2980b9, stop:1 #2471a3);
    }
    
    QStatusBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2c3e50, stop:1 #34495e);
        color: #ecf0f1;
        border-top: 2px solid #3498db;
        padding: 5px;
    }
    
    QTabWidget::pane {
        border: none;
        background: #2c3e50;
        border-radius: 12px;
        margin: 8px;
        border: 1px solid #34495e;
    }
    
    QTabBar::tab {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2c3e50, stop:1 #34495e);
        color: #bdc3c7;
        border: none;
        border-bottom: 3px solid transparent;
        padding: 12px 20px;
        margin-right: 2px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        min-width: 100px;
    }
    
    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3a506b, stop:1 #2c3e50);
        color: #3498db;
        border-bottom: 3px solid #3498db;
    }
    
    QTabBar::tab:hover:!selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #34495e, stop:1 #2c3e50);
        color: #ecf0f1;
    }
    
    QTabBar::tab[dashboardTab="true"]:selected { 
        border-bottom-color: #3498db;
        color: #3498db;
    }
    
    QTabBar::tab[patientTab="true"]:selected { 
        border-bottom-color: #2ecc71;
        color: #2ecc71;
    }
    
    QTabBar::tab[orderTab="true"]:selected { 
        border-bottom-color: #e74c3c;
        color: #e74c3c;
    }
    
    QTabBar::tab[testTab="true"]:selected { 
        border-bottom-color: #e67e22;
        color: #e67e22;
    }
    
    QTabBar::tab[resultTab="true"]:selected { 
        border-bottom-color: #f1c40f;
        color: #f1c40f;
    }
    
    QTabBar::tab[userTab="true"]:selected { 
        border-bottom-color: #9b59b6;
        color: #9b59b6;
    }
    
    QTabBar::tab[reportTab="true"]:selected { 
        border-bottom-color: #1abc9c;
        color: #1abc9c;
    }
    
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3498db, stop:1 #2980b9);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 13px;
    }
    
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2980b9, stop:1 #2471a3);
    }
    
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2471a3, stop:1 #1f618d);
    }
    
    QLineEdit {
        background: #2c3e50;
        border: 2px solid #34495e;
        border-radius: 8px;
        padding: 10px 15px;
        font-size: 14px;
        color: #ecf0f1;
        selection-background-color: #3498db;
    }
    
    QLineEdit:focus {
        border: 2px solid #3498db;
        background: rgba(44, 62, 80, 0.9);
    }
    
    QLineEdit::placeholder {
        color: #7f8c8d;
        font-style: italic;
    }
    
    QComboBox {
        background: rgba(44, 62, 80, 0.7);
        border: 2px solid #34495e;
        border-radius: 8px;
        padding: 8px 15px;
        min-width: 6em;
        color: #ecf0f1;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 30px;
    }
    
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #7f8c8d;
        width: 0px;
        height: 0px;
    }
    
    QComboBox QAbstractItemView {
        background: #2c3e50;
        border: 1px solid #34495e;
        border-radius: 8px;
        selection-background-color: #3498db;
        selection-color: white;
    }
    
    QProgressBar {
        border: 2px solid #34495e;
        border-radius: 8px;
        text-align: center;
        color: #ecf0f1;
        background: rgba(44, 62, 80, 0.7);
    }
    
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3498db, stop:1 #2980b9);
        border-radius: 6px;
    }
    
    QPushButton:focus, QToolButton:focus, QLineEdit:focus, QComboBox:focus {
        outline: 2px solid #3498db;
        outline-offset: 2px;
    }
    
    GlassFrame {
        background-color: #1f2a44;
        border: 1px solid #2b3b5a;
        border-radius: 12px;
    }
    """

    def __init__(self, user):
        super().__init__()
        self.current_user = user
        # Load persisted config (theme, glass preference, timeout)
        try:
            cfg = load_config()
        except Exception:
            cfg = {}

        self.setWindowTitle("AnandhLIMS")
        self.current_theme = cfg.get('theme', "Premium Light")
        self.use_glass = bool(cfg.get('use_glass', False))
        GlassFrame.set_use_glass(self.use_glass)
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.timeout.connect(self._auto_logout)
        self.inactivity_timeout = int(cfg.get('inactivity_timeout_minutes', 30)) * 60 * 1000
        self.last_activity = datetime.now()
        
        self.setWindowFlags(Qt.WindowType.Window | 
                            Qt.WindowType.WindowMinimizeButtonHint | 
                            Qt.WindowType.WindowMaximizeButtonHint | 
                            Qt.WindowType.WindowCloseButtonHint)
        
        self.tray_icon = None
        self.setup_system_tray()
        
        self.setMinimumSize(1000, 700)
        
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        initial_width = min(1600, screen_geometry.width() - 100)
        initial_height = min(1000, screen_geometry.height() - 100)
        self.resize(initial_width, initial_height)
        
        self._init_toolbar()
        self._init_tabs()
        self._init_status_bar()
        self._apply_styles()
        self._confirm_on_close = True
        
        self.center_on_screen()
        self.previous_width = self.width()
        
        self._reset_inactivity_timer()
        self.installEventFilter(self)
        
        self.session_data = {
            "start_time": datetime.now(),
            "active_tabs": [],
            "actions_performed": 0
        }
        # Ensure background threads are cleaned up on application quit
        try:
            app = QApplication.instance()
            if app is not None:
                try:
                    app.aboutToQuit.connect(self._cleanup_threads)
                except Exception:
                    pass
        except Exception:
            pass
        # Register atexit fallback to ensure threads are cleaned on interpreter shutdown
        try:
            atexit.register(self._cleanup_threads)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.KeyPress):
            self._reset_inactivity_timer()
            self.session_data["actions_performed"] += 1
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        # For standard key sequences
        if event.matches(QKeySequence.StandardKey.New):
            self.on_new_action()
        elif event.matches(QKeySequence.StandardKey.Open):
            self.on_open_action()
        elif event.matches(QKeySequence.StandardKey.Save):
            self.on_save_action()
        # For custom key sequences using manual checking
        elif (event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and 
              event.key() == Qt.Key.Key_T):
            self._toggle_theme()
        else:
            super().keyPressEvent(event)

    def on_new_action(self):
        """Placeholder for New action - can be implemented later"""
        pass

    def on_open_action(self):
        """Placeholder for Open action - can be implemented later"""
        pass

    def on_save_action(self):
        """Placeholder for Save action - can be implemented later"""
        pass

    def _reset_inactivity_timer(self):
        self.last_activity = datetime.now()
        self.inactivity_timer.stop()
        self.inactivity_timer.start(self.inactivity_timeout)

    def _auto_logout(self):
        reply = QMessageBox.question(
            self, "Inactivity Detected",
            "You have been inactive for 30 minutes. Logout now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._on_logout()

    def center_on_screen(self):
        frame_geometry = self.frameGeometry()
        center_point = QApplication.primaryScreen().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def setup_system_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
            tray_menu = QMenu()
            restore_action = tray_menu.addAction("Restore")
            restore_action.triggered.connect(self.show_normal)
            
            stats_action = tray_menu.addAction("Session Stats")
            stats_action.triggered.connect(self._show_session_stats)
            
            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(self.quit_application)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
    def show_normal(self):
        self.show()
        self.activateWindow()
        self.raise_()
        
    def quit_application(self):
        self._confirm_on_close = False
        QApplication.quit()
        
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_normal()
            
    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and self.tray_icon:
                self.hide()
                self.tray_icon.show()
                self.tray_icon.showMessage(
                    "AnandhLIMS",
                    "Application minimized to system tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        super().changeEvent(event)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        current_width = self.width()
        
        toolbar = self.findChild(QToolBar, "Main Toolbar")
        if toolbar:
            for action in toolbar.actions():
                widget = toolbar.widgetForAction(action)
                if widget and isinstance(widget, QPushButton):
                    if current_width < 1200:
                        widget.setText("")
                        widget.setToolTip(action.toolTip())
                    else:
                        widget.setText(action.text())
                        widget.setToolTip(action.toolTip())
        
        if self.tabs:
            screen_width = QApplication.primaryScreen().availableGeometry().width()
            scale_factor = self.width() / screen_width
            if scale_factor < 0.6:
                self.tabs.tabBar().setStyleSheet("QTabBar::tab { padding: 8px 12px; min-width: 70px; font-size: 11px; }")
            elif scale_factor < 0.8:
                self.tabs.tabBar().setStyleSheet("QTabBar::tab { padding: 10px 16px; min-width: 85px; font-size: 12px; }")
            else:
                self.tabs.tabBar().setStyleSheet("QTabBar::tab { padding: 12px 20px; min-width: 100px; font-size: 13px; }")
        
        self.previous_width = current_width

    def load_icon(self, icon_file, fallback=QStyle.StandardPixmap.SP_FileIcon):
        icon_path = os.path.join(self.ICON_PATH, icon_file)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        logger.warning(f"Icon {icon_file} not found at {icon_path}. Using fallback icon.")
        fallbacks = {
            "help_icon.png": QStyle.StandardPixmap.SP_MessageBoxInformation,
            "settings_icon.png": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "export_icon.png": QStyle.StandardPixmap.SP_DriveFDIcon,
            "refresh_icon.png": QStyle.StandardPixmap.SP_BrowserReload,
            "logout_icon.png": QStyle.StandardPixmap.SP_DialogCloseButton,
            "dashboard_icon.png": QStyle.StandardPixmap.SP_ComputerIcon,
            "patient_icon.png": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "order_icon.png": QStyle.StandardPixmap.SP_FileDialogListView,
            "test_icon.png": QStyle.StandardPixmap.SP_FileDialogToParent,
            "result_icon.png": QStyle.StandardPixmap.SP_FileDialogNewFolder,
            "user_icon.png": QStyle.StandardPixmap.SP_FileDialogStart,
            "report_icon.png": QStyle.StandardPixmap.SP_FileDialogEnd,
            "search_icon.png": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "stats_icon.png": QStyle.StandardPixmap.SP_FileDialogInfoView,
            "theme_icon.png": QStyle.StandardPixmap.SP_DesktopIcon,
        }
        return self.style().standardIcon(fallbacks.get(icon_file, fallback))

    def _init_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar_container = GlassFrame()
        toolbar_container.setStyleSheet("""
            GlassFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a237e, stop:1 #283593);
                border: none;
                border-bottom: 3px solid #5c6bc0;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(15, 8, 15, 8)
        toolbar_layout.setSpacing(20)
        
        title_container = QHBoxLayout()
        title_container.setSpacing(10)
        
        logo_label = QLabel("🔬")
        logo_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                padding: 5px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
        """)
        title_container.addWidget(logo_label)
        
        title_widget = QLabel("AnandhLIMS")
        title_widget.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
            }
        """)
        title_container.addWidget(title_widget)
        toolbar_layout.addLayout(title_container)
        
        toolbar_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        actions_container = QWidget()
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        
        premium_actions = [
            ("stats_icon.png", "Stats", self._show_session_stats, "Ctrl+I", "View session statistics"),
            ("help_icon.png", "Help", self._show_help, QKeySequence.StandardKey.HelpContents, "View help guide"),
            ("settings_icon.png", "Settings", self._show_settings, QKeySequence.StandardKey.Preferences, "Configure settings"),
            ("export_icon.png", "Export", self._export_data, QKeySequence("Ctrl+E"), "Export data"),
            ("refresh_icon.png", "Refresh", self._refresh_all_tabs, QKeySequence.StandardKey.Refresh, "Refresh all data"),
            ("logout_icon.png", "Logout", self._on_logout, QKeySequence.StandardKey.Quit, "Logout"),
        ]
        
        for icon_file, text, callback, shortcut, tooltip in premium_actions:
            btn = QPushButton(text)
            btn.setIcon(self.load_icon(icon_file))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(callback)
            if shortcut:
                btn.setShortcut(shortcut)
            btn.setToolTip(f"<b>{text}</b><br>{tooltip}")
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3949ab, stop:1 #3f51b5);
                    color: #ffffff;
                    border: 1px solid #5c6bc0;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5c6bc0, stop:1 #7986cb);
                    border: 1px solid #9fa8da;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3f51b5, stop:1 #3949ab);
                }
            """)
            actions_layout.addWidget(btn)
        
        toolbar_layout.addWidget(actions_container)
        
        search_container = GlassFrame()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 5, 10, 5)
        
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("🔍 Search across system...")
        search_bar.setMaximumWidth(250)
        search_bar.returnPressed.connect(lambda: self._perform_search(search_bar.text()))
        search_bar.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ecf0f1;
                font-size: 13px;
                padding: 5px;
            }
            QLineEdit::placeholder {
                color: rgba(236, 240, 241, 0.7);
            }
        """)
        search_layout.addWidget(search_bar)
        
        toolbar_layout.addWidget(search_container)
        
        toolbar.addWidget(toolbar_container)

    def _init_tabs(self):
        main_container = GlassFrame()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setUsesScrollButtons(True)
        
        tab_shadow = QGraphicsDropShadowEffect()
        tab_shadow.setBlurRadius(15)
        tab_shadow.setColor(QColor(0, 0, 0, 60))
        tab_shadow.setOffset(0, 3)
        self.tabs.setGraphicsEffect(tab_shadow)
        
        main_layout.addWidget(self.tabs)
        self.setCentralWidget(main_container)

        self.tab_instances = {}
        self.previous_tab_index = -1
        
        for idx, (TabClass, icon_file, label, obj_name, roles) in enumerate(self.TAB_CONFIG):
            try:
                if TabClass.__init__.__code__.co_argcount > 1:
                    tab_widget = TabClass(self.current_user)
                else:
                    tab_widget = TabClass()
                    
                tab_container = GlassFrame()
                tab_layout = QVBoxLayout(tab_container)
                tab_layout.addWidget(tab_widget)
                
            except Exception as e:
                logger.error(f"Error creating {label} tab: {e}")
                tab_container = GlassFrame()
                tab_layout = QVBoxLayout(tab_container)
                
                error_label = QLabel(f"🚫 Failed to load {label} tab\n\nError: {str(e)}\n\nPlease contact support.")
                error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                error_label.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-size: 16px;
                        font-weight: bold;
                        padding: 40px;
                        background: rgba(231, 76, 60, 0.1);
                        border-radius: 10px;
                    }
                """)
                tab_layout.addWidget(error_label)
            
            icon = self.load_icon(icon_file)
            self.tabs.addTab(tab_container, icon, f"  {label}  ")
            tab_container.setObjectName(obj_name)
            
            tab_bar = self.tabs.tabBar()
            tab_bar.setProperty(obj_name, True)
            
            enabled = self.current_user.role in roles
            self.tabs.setTabEnabled(idx, enabled)
            
            self.tab_instances[obj_name] = tab_widget
        
        # Connect cross-tab signals: when patients are changed notify order tab to reload
        try:
            patient_tab = self.tab_instances.get('patientTab')
            order_tab = self.tab_instances.get('orderTab')
            if patient_tab and order_tab and hasattr(patient_tab, 'patient_saved'):
                # patient_saved now emits an int patient_id; reload combos and auto-select the new patient if provided
                patient_tab.patient_saved.connect(lambda pid, ot=order_tab: (ot.load_combos(), ot.select_patient_by_id(pid) if pid else None))
            # Connect patient_open_in_order to switch to Orders tab and select the patient
            if patient_tab and order_tab and hasattr(patient_tab, 'patient_open_in_order'):
                def _open_orders_for_patient(pid, ot=order_tab):
                    try:
                        idx = [i for i, (_, _, _, obj_name, _) in enumerate(self.TAB_CONFIG) if obj_name == 'orderTab'][0]
                        self.tabs.setCurrentIndex(idx)
                        # Ensure combos are up-to-date and select the patient
                        try:
                            ot.load_combos()
                        except Exception:
                            pass
                        if pid:
                            ot.select_patient_by_id(pid)
                    except Exception:
                        logger.exception('Failed to open Orders tab for patient')
                patient_tab.patient_open_in_order.connect(_open_orders_for_patient)
        except Exception:
            # Non-fatal: if connection fails, continue without breaking UI
            logger.exception('Failed to connect patient_saved signal to order tab')

        self.tabs.currentChanged.connect(self._animate_tab_change)
        
        if self.tabs.count() > 0:
            self.tabs.setCurrentIndex(0)
        
        corner_widget = GlassFrame()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(5, 2, 5, 2)
        
        search_btn = QPushButton("🔍")
        search_btn.setToolTip("Advanced Search (Ctrl+F)")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFlat(True)
        search_btn.clicked.connect(self._show_search_dialog)
        search_btn.setShortcut(QKeySequence.StandardKey.Find)
        search_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
                padding: 5px;
                color: #7f8c8d;
            }
            QPushButton:hover {
                color: #3498db;
                background: rgba(52, 152, 219, 0.1);
                border-radius: 4px;
            }
        """)
        corner_layout.addWidget(search_btn)
        
        self.tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)

    def _next_tab(self):
        current = self.tabs.currentIndex()
        next_idx = (current + 1) % self.tabs.count()
        while not self.tabs.isTabEnabled(next_idx):
            next_idx = (next_idx + 1) % self.tabs.count()
        self.tabs.setCurrentIndex(next_idx)

    def _previous_tab(self):
        current = self.tabs.currentIndex()
        prev_idx = (current - 1) % self.tabs.count()
        while not self.tabs.isTabEnabled(prev_idx):
            prev_idx = (prev_idx - 1) % self.tabs.count()
        self.tabs.setCurrentIndex(prev_idx)

    def _animate_tab_change(self, index):
        if index == self.previous_tab_index:
            return
            
        new_tab = self.tabs.widget(index)
        if new_tab:
            try:
                anim = QPropertyAnimation(new_tab, b"windowOpacity")
                anim.setDuration(400)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.start()
            except Exception as e:
                logger.warning(f"Failed to animate tab change: {e}")
                
        self.previous_tab_index = index

    def _show_search_dialog(self):
        search_text, ok = QInputDialog.getText(
            self, "Advanced Search", "Enter search term:",
            QLineEdit.EchoMode.Normal, ""
        )
        if ok and search_text.strip():
            self._perform_search(search_text.strip())

    def _perform_search(self, query):
        if not query.strip():
            self.statusBar().showMessage("🔍 Search query cannot be empty", 3000)
            return
            
        self.statusBar().showMessage("🔍 Searching...", 2000)
        
        search_results = {}
        for tab_name, tab in self.tab_instances.items():
            if hasattr(tab, 'get_search_results'):
                try:
                    results = tab.get_search_results(query)
                    if results:
                        search_results[tab_name] = results
                except Exception as e:
                    logger.error(f"Error searching in {tab_name}: {e}")
                    
        if search_results:
            dialog = SearchDialog(self, search_results)
            dialog.results_list.itemDoubleClicked.connect(lambda item: self._navigate_to_result(item, search_results))
            dialog.show()
            total_results = sum(len(items) for items in search_results.values())
            self.statusBar().showMessage(f"✅ Found {total_results} results for '{query}'", 5000)
        else:
            self.statusBar().showMessage(f"❌ No results found for '{query}'", 3000)
            QMessageBox.information(self, "Search Complete", f"No results found for '{query}'.")

    def _navigate_to_result(self, item, search_results):
        try:
            if not item.text().startswith("📁"):
                category, item_text = item.text().split(": ", 1)
                category = category.replace("📄 ", "").strip()
                tab_name = [name for name, results in search_results.items() if item_text in results][0]
                tab_index = [i for i, (_, _, _, name, _) in enumerate(self.TAB_CONFIG) if name == tab_name][0]
                self.tabs.setCurrentIndex(tab_index)
                tab = self.tab_instances[tab_name]
                if hasattr(tab, 'highlight_result'):
                    tab.highlight_result(item_text)
        except Exception as e:
            logger.error(f"Error navigating to search result: {e}")
            self.statusBar().showMessage("⚠️ Error navigating to result", 3000)

    def _init_status_bar(self):
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        user_container = GlassFrame()
        user_layout = QHBoxLayout(user_container)
        user_layout.setContentsMargins(8, 3, 8, 3)
        
        user_label = QLabel(f"👤 {self.current_user.username} | {self.current_user.role}")
        user_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        user_layout.addWidget(user_label)
        status_bar.addWidget(user_container)
        
        status_container = GlassFrame()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(8, 3, 8, 3)
        
        self.status_indicator = QLabel("🟢 System Operational")
        self.status_indicator.setStyleSheet("color: #27ae60; font-weight: bold;")
        status_layout.addWidget(self.status_indicator)
        status_bar.addWidget(status_container)
        
        session_container = GlassFrame()
        session_layout = QHBoxLayout(session_container)
        session_layout.setContentsMargins(8, 3, 8, 3)
        
        self.session_timer = QLabel("🕐 00:00:00")
        self.session_timer.setStyleSheet("color: #3498db; font-weight: bold;")
        session_layout.addWidget(self.session_timer)
        status_bar.addWidget(session_container)
        
        datetime_container = GlassFrame()
        datetime_layout = QHBoxLayout(datetime_container)
        datetime_layout.setContentsMargins(8, 3, 8, 3)
        
        self.datetime_label = QLabel()
        self._update_datetime()
        self.datetime_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        datetime_layout.addWidget(self.datetime_label)
        status_bar.addPermanentWidget(datetime_container)
        
        self.session_start = datetime.now()
        self.session_timer_update = QTimer(self)
        self.session_timer_update.timeout.connect(self._update_session_timer)
        self.session_timer_update.start(1000)
        
        self.datetime_timer = QTimer(self)
        self.datetime_timer.timeout.connect(self._update_datetime)
        self.datetime_timer.start(30000)

    def _update_datetime(self):
        current_datetime = QDateTime.currentDateTime().toString("📅 ddd, MMM d, yyyy | 🕐 h:mm AP")
        self.datetime_label.setText(current_datetime)

    def _update_session_timer(self):
        elapsed = datetime.now() - self.session_start
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.session_timer.setText(f"🕐 {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _apply_styles(self):
        # Set Calibri size 12 as default font
        app_font = QFont("Calibri", 12)
        app_font.setWeight(QFont.Weight.Normal)
        QApplication.setFont(app_font)
        
        # Apply consistent light blue theme
        self.setStyleSheet(self.LIGHT_BLUE_STYLESHEET)

    def _toggle_theme(self):
        if self.current_theme == "Premium Light":
            self.current_theme = "Premium Dark"
        else:
            self.current_theme = "Premium Light"
        
        self._apply_styles()
        self.statusBar().showMessage(f"🎨 Switched to {self.current_theme} theme", 3000)

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._confirm_on_close = False
            self.close()

    def _export_data(self):
        items = ["All Data", "Patients", "Orders", "Tests", "Results", "Users", "Session Data"]
        item, ok = QInputDialog.getItem(self, "Export Data", "Select data to export:", items, 0, False)
        if not ok:
            return

        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle(f"Preview {item} Export")
        preview_dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
                border-radius: 12px;
            }
            QLabel {
                color: white;
            }
            QTextEdit {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout()
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        sample_data = self._get_sample_data(item.lower())
        preview_text.setText("\n".join([",".join(row) for row in sample_data[:5]]))
        layout.addWidget(QLabel(f"Preview of {item} (first 5 rows):"))
        layout.addWidget(preview_text)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(preview_dialog.accept)
        button_box.rejected.connect(preview_dialog.reject)
        layout.addWidget(button_box)
        preview_dialog.setLayout(layout)
        
        if not preview_dialog.exec():
            return

        default_name = f"lab_export_{QDateTime.currentDateTime().toString('yyyyMMdd_hhmmss')}"
        path, _ = QFileDialog.getSaveFileName(self, f"Export {item}", default_name, "CSV Files (*.csv)")
        if path:
            self.progress_bar = QProgressBar(self.statusBar())
            self.progress_bar.setMaximum(100)
            self.statusBar().addPermanentWidget(self.progress_bar)
            try:
                if item == "All Data":
                    self._export_all_data(path)
                else:
                    self._export_specific_data(item.lower(), path)
                QMessageBox.information(self, "Export Successful", f"{item} exported successfully!")
            except Exception as e:
                logger.error(f"Export failed: {e}")
                QMessageBox.critical(self, "Export Failed", f"Error during export: {str(e)}")
            finally:
                self.progress_bar.setValue(100)
                QTimer.singleShot(1000, lambda: self.statusBar().removeWidget(self.progress_bar))

    def _get_sample_data(self, data_type):
        sample_data = {
            "patients": [["ID", "Name", "DOB", "Gender"], ["1", "John Doe", "1980-01-01", "Male"]],
            "orders": [["Order ID", "Patient ID", "Test ID", "Date"], ["1001", "1", "5", "2023-05-01"]],
            "tests": [["Test ID", "Name", "Category", "Price"], ["5", "Blood Test", "Hematology", "50.00"]],
            "results": [["Result ID", "Order ID", "Value", "Unit"], ["5001", "1001", "5.2", "mg/dL"]],
            "users": [["User ID", "Username", "Role", "Email"], ["1", "admin", "admin", "admin@example.com"]],
            "session data": [["Metric", "Value"], ["Session Start", self.session_start.strftime('%Y-%m-%d %H:%M:%S')]]
        }
        return sample_data.get(data_type, [["No preview available"]])

    class ExportThread(QThread):
        progress = pyqtSignal(int)
        finished = pyqtSignal(str)
        error = pyqtSignal(str)

        def __init__(self, data_type, path, data):
            super().__init__()
            self.data_type = data_type
            self.path = path
            self.data = data

        def run(self):
            try:
                with open(self.path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    total_rows = len(self.data)
                    for i, row in enumerate(self.data):
                        writer.writerow(row)
                        self.progress.emit(int((i + 1) / total_rows * 100) if total_rows > 0 else 100)
                    self.finished.emit(f"{self.data_type} exported successfully")
            except Exception as e:
                self.error.emit(str(e))

    def _export_all_data(self, path):
        base_name = os.path.splitext(path)[0]
        data_types = ["patients", "orders", "tests", "results", "users"]
        total = len(data_types)
        for i, data_type in enumerate(data_types):
            file_path = f"{base_name}_{data_type}.csv"
            self._export_specific_data(data_type, file_path)
            self.progress_bar.setValue(int((i + 1) / total * 100))

    def _export_specific_data(self, data_type, path):
        sample_data = {
            "patients": [["ID", "Name", "DOB", "Gender"], ["1", "John Doe", "1980-01-01", "Male"]],
            "orders": [["Order ID", "Patient ID", "Test ID", "Date"], ["1001", "1", "5", "2023-05-01"]],
            "tests": [["Test ID", "Name", "Category", "Price"], ["5", "Blood Test", "Hematology", "50.00"]],
            "results": [["Result ID", "Order ID", "Value", "Unit"], ["5001", "1001", "5.2", "mg/dL"]],
            "users": [["User ID", "Username", "Role", "Email"], ["1", "admin", "admin", "admin@example.com"]],
            "session data": [["Metric", "Value"], ["Session Start", self.session_start.strftime('%Y-%m-%d %H:%M:%S')]]
        }
        data = sample_data.get(data_type, [])
        self.export_thread = self.ExportThread(data_type, path, data)
        self.export_thread.progress.connect(self.progress_bar.setValue)
        self.export_thread.finished.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
        self.export_thread.error.connect(lambda err: QMessageBox.critical(self, "Export Failed", err))
        self.export_thread.start()

    def _show_settings(self):
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Application Settings")
        settings_dialog.setModal(True)
        settings_dialog.resize(400, 300)
        settings_dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
                border-radius: 12px;
            }
            QLabel {
                color: white;
            }
            QComboBox, QSpinBox {
                background: rgba(255, 255, 255, 0.9);
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        
        layout = QVBoxLayout()
        settings_dialog.setLayout(layout)
        
        theme_label = QLabel("Interface Theme:")
        layout.addWidget(theme_label)
        
        theme_combo = QComboBox()
        theme_combo.addItems(["Premium Light", "Premium Dark"])
        theme_combo.setCurrentText(self.current_theme)
        layout.addWidget(theme_combo)
        
        auto_logout_label = QLabel("Auto-logout after inactivity (minutes):")
        layout.addWidget(auto_logout_label)
        
        auto_logout_spin = QSpinBox(settings_dialog)
        auto_logout_spin.setRange(5, 120)
        auto_logout_spin.setValue(self.inactivity_timeout // 60000)
        layout.addWidget(auto_logout_spin)

        # Transparency / glass toggle
        use_glass_chk = QCheckBox("Enable glass/transparency UI")
        try:
            use_glass_chk.setChecked(bool(self.use_glass))
        except Exception:
            use_glass_chk.setChecked(False)
        layout.addWidget(use_glass_chk)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        def apply_settings():
            self.current_theme = theme_combo.currentText()
            # apply stylesheet changes
            self._apply_styles()
            # update inactivity timeout
            self.inactivity_timeout = auto_logout_spin.value() * 60 * 1000
            self._reset_inactivity_timer()
            # update glass setting and persist
            try:
                self.use_glass = bool(use_glass_chk.isChecked())
                GlassFrame.set_use_glass(self.use_glass)
                cfg = load_config()
                cfg['use_glass'] = bool(self.use_glass)
                cfg['theme'] = self.current_theme
                cfg['inactivity_timeout_minutes'] = int(self.inactivity_timeout // 60000)
                save_config(cfg)
            except Exception:
                pass
            settings_dialog.accept()
        button_box.accepted.connect(apply_settings)
        button_box.rejected.connect(settings_dialog.reject)
        layout.addWidget(button_box)
        
        settings_dialog.exec()

    def _show_help(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help & Documentation")
        help_dialog.setModal(True)
        help_dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        help_dialog.setLayout(layout)
        
        help_tabs = QTabWidget()
        
        quick_start = QTextEdit()
        quick_start.setReadOnly(True)
        quick_start.setHtml("""
        <h2>Quick Start Guide</h2>
        <p>Welcome to AnandhLIMS.</p>
        <ul>
            <li>Use the tabs to navigate between different sections</li>
            <li>Press Ctrl+Shift+T to toggle between light and dark themes</li>
            <li>Use advanced search with Ctrl+F</li>
            <li>View session statistics with Ctrl+I</li>
            <li>Export data with multiple options</li>
        </ul>
        """)
        help_tabs.addTab(quick_start, "Quick Start")
        
        manual = QTextEdit()
        manual.setReadOnly(True)
        manual.setHtml("""
        <h2>Premium Features</h2>
        <p>Enhanced with glass morphism effects, smooth animations, and premium styling.</p>
        <p>New features: Theme switching, session analytics, advanced search, enhanced export.</p>
        """)
        help_tabs.addTab(manual, "Features")
        
        layout.addWidget(help_tabs)
        help_dialog.exec()

    def _show_session_stats(self):
        stats_dialog = QDialog(self)
        stats_dialog.setWindowTitle("Session Statistics")
        stats_dialog.setModal(True)
        stats_dialog.resize(400, 300)
        stats_dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
                border-radius: 12px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                padding: 5px;
            }
            QTextEdit {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(stats_dialog)
        
        title = QLabel("Session Analytics")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        stats_text = QTextEdit()
        stats_text.setReadOnly(True)
        
        session_duration = datetime.now() - self.session_start
        hours, remainder = divmod(int(session_duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        stats_content = f"""
        <h3>Session Overview</h3>
        <p><b>User:</b> {self.current_user.username}</p>
        <p><b>Role:</b> {self.current_user.role}</p>
        <p><b>Session Start:</b> {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><b>Duration:</b> {hours:02d}:{minutes:02d}:{seconds:02d}</p>
        <p><b>Actions:</b> {self.session_data['actions_performed']}</p>
        <p><b>Current Theme:</b> {self.current_theme}</p>
        """
        
        stats_text.setHtml(stats_content)
        layout.addWidget(stats_text)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(stats_dialog.accept)
        layout.addWidget(button_box)
        
        stats_dialog.exec()

    def _refresh_all_tabs(self):
        refresh_animation = QPropertyAnimation(self, b"windowOpacity")
        refresh_animation.setDuration(300)
        refresh_animation.setStartValue(1.0)
        refresh_animation.setEndValue(0.7)
        refresh_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        refresh_animation.finished.connect(lambda: self._complete_refresh(refresh_animation))
        refresh_animation.start()
        
        self.statusBar().showMessage("🔄 Refreshing all data...", 2000)

    def _complete_refresh(self, animation):
        refresh_count = 0
        for tab_name, tab_instance in self.tab_instances.items():
            if hasattr(tab_instance, 'refresh_data'):
                try:
                    count = tab_instance.refresh_data() or 0
                    refresh_count += count
                except Exception as e:
                    logger.error(f"Error refreshing {tab_name}: {e}")
        
        reverse_animation = QPropertyAnimation(self, b"windowOpacity")
        reverse_animation.setDuration(300)
        reverse_animation.setStartValue(0.7)
        reverse_animation.setEndValue(1.0)
        reverse_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        reverse_animation.start()
        
        self.statusBar().showMessage(f"✅ Refreshed {refresh_count} records across all tabs", 3000)
        self.status_indicator.setText("🟢 System Operational")

    def closeEvent(self, event):
        try:
            # Reuse same cleanup logic to stop background threads
            self._cleanup_threads()
        except Exception as e:
            logger.error(f"Error during tab cleanup: {e}")
        
        if self._confirm_on_close:
            minimize_option = QMessageBox.StandardButton.Yes if QSystemTrayIcon.isSystemTrayAvailable() else QMessageBox.StandardButton.No
            
            reply = QMessageBox.question(
                self, "Exit Application",
                "Do you really want to exit the application?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | minimize_option,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            elif reply == minimize_option and QSystemTrayIcon.isSystemTrayAvailable():
                self.hide()
                event.ignore()
            else:
                event.ignore()
        else:
            event.accept()

    def _cleanup_threads(self):
        """Stop/cleanup any background threads or long-running tasks owned by tabs.

        This method is safe to call multiple times and is connected to
        QApplication.aboutToQuit so threads are stopped before process exit.
        """
        try:
            def _safe_hasattr(obj, name):
                try:
                    return hasattr(obj, name)
                except RuntimeError:
                    return False

            def _safe_getattr(obj, name, default=None):
                try:
                    return getattr(obj, name)
                except RuntimeError:
                    return default
                except Exception:
                    return default

            for tab_name, tab in list(getattr(self, 'tab_instances', {}).items()):
                try:
                    # Preferred explicit cleanup hooks on tabs
                    if _safe_hasattr(tab, 'cleanup'):
                        try:
                            fn = _safe_getattr(tab, 'cleanup')
                            if callable(fn):
                                fn()
                        except Exception:
                            pass
                    if _safe_hasattr(tab, 'stop_thread'):
                        try:
                            fn = _safe_getattr(tab, 'stop_thread')
                            if callable(fn):
                                fn()
                        except Exception:
                            pass

                    # Common thread attribute names used in tabs (data_thread, export_thread, etc.)
                    for common_name in ('data_thread', 'export_thread', 'worker_thread', 'thread'):
                        th = _safe_getattr(tab, common_name, None)
                        if th is None:
                            continue
                        try:
                            # If the thread exposes a stop() method prefer that
                            if _safe_hasattr(th, 'stop'):
                                try:
                                    fn = _safe_getattr(th, 'stop')
                                    if callable(fn):
                                        fn()
                                except Exception:
                                    pass

                            # Then attempt a graceful quit/wait for QThread-like objects
                            if _safe_hasattr(th, 'isRunning'):
                                try:
                                    is_running = _safe_getattr(th, 'isRunning')
                                    if callable(is_running) and is_running():
                                        if _safe_hasattr(th, 'quit'):
                                            try:
                                                fn = _safe_getattr(th, 'quit')
                                                if callable(fn):
                                                    fn()
                                            except Exception:
                                                pass
                                        if _safe_hasattr(th, 'wait'):
                                            try:
                                                fn = _safe_getattr(th, 'wait')
                                                if callable(fn):
                                                    fn(2000)
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                        except Exception:
                            pass

                    # As a last resort, scan attributes on the tab for any QThread-like instances
                    for attr_name in dir(tab):
                        try:
                            attr = _safe_getattr(tab, attr_name, None)
                            if attr is None:
                                continue
                            if _safe_hasattr(attr, 'isRunning') and callable(_safe_getattr(attr, 'isRunning')):
                                try:
                                    if _safe_getattr(attr, 'isRunning')():
                                        if _safe_hasattr(attr, 'stop'):
                                            try:
                                                fn = _safe_getattr(attr, 'stop')
                                                if callable(fn):
                                                    fn()
                                            except Exception:
                                                pass
                                        if _safe_hasattr(attr, 'quit'):
                                            try:
                                                fn = _safe_getattr(attr, 'quit')
                                                if callable(fn):
                                                    fn()
                                            except Exception:
                                                pass
                                        if _safe_hasattr(attr, 'wait'):
                                            try:
                                                fn = _safe_getattr(attr, 'wait')
                                                if callable(fn):
                                                    fn(2000)
                                            except Exception:
                                                pass
                                except Exception:
                                    pass
                        except Exception:
                            # ignore attribute access exceptions
                            pass
                except Exception:
                    logger.exception(f"Error cleaning tab {tab_name}")
        except Exception:
            logger.exception("Failed to cleanup threads in MainWindow")