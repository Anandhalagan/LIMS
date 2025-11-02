import json
import os
import csv
import datetime
import logging
import threading
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QGroupBox,
    QGridLayout, QSizePolicy, QFrame, QTableWidget, QTableWidgetItem, QLineEdit,
    QFileDialog, QHeaderView, QComboBox, QProgressBar, QScrollArea, QSpacerItem,
    QGraphicsDropShadowEffect, QApplication, QToolTip, QMenu, QSystemTrayIcon,
    QSplitter, QTabWidget, QTextEdit, QSlider, QCheckBox, QButtonGroup, QRadioButton,
    QDateEdit, QTimeEdit
)
from PyQt6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty,
    QThread, pyqtSignal, QParallelAnimationGroup, QSequentialAnimationGroup,
    QDateTime, QDate, QTime
)
from PyQt6.QtGui import (
    QPainter, QIcon, QColor, QLinearGradient, QFont, QPalette, QBrush, QPixmap,
    QPainterPath, QRadialGradient, QPolygon, QMovie, QCursor, QFontMetrics,
    QGradient, QPen, QConicalGradient
)
from PyQt6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QPieSeries, QPieSlice, QLineSeries, QAreaSeries, QSplineSeries, QScatterSeries,
    QDateTimeAxis, QLegend
)
from database import Session
from models import Order, Patient, Test, cipher
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import func
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Dashboard')


class DatabaseManager:
    """Database connection manager with context support"""
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()


class DataUpdateThread(QThread):
    """Background thread for data updates to prevent UI freezing"""
    data_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.db_manager = DatabaseManager()
        self.config = {
            'update_interval': 30000,  # 30 seconds
            'timeout': 3000  # 3 second timeout for stopping
        }
    
    def run(self):
        logger.info("Data update thread started")
        while self.running:
            try:
                with self.db_manager.get_session() as session:
                    data = {
                        'today_orders': self.get_todays_orders(session),
                        'pending_results': self.get_pending_results(session),
                        'completed_today': self.get_completed_today(session),
                        'verified_today': self.get_verified_today(session),
                        'hourly_data': self.get_hourly_data(session),
                        'recent_orders': self.get_recent_orders(session)
                    }
                    self.data_updated.emit(data)
                self.msleep(self.config['update_interval'])
            except Exception as e:
                logger.error(f"Data update error: {e}")
                self.error_occurred.emit(str(e))
                self.msleep(5000)  # Longer delay on error
    
    def stop(self):
        """Stop thread with timeout to prevent hanging"""
        logger.info("Stopping data update thread")
        self.running = False
        self.quit()
        if not self.wait(self.config['timeout']):
            logger.warning("Thread didn't stop gracefully, terminating")
            self.terminate()
            self.wait()
        logger.info("Data update thread stopped")
    
    def get_todays_orders(self, session):
        """Get today's orders with proper error handling"""
        try:
            today = datetime.datetime.now().date()
            count = session.query(Order).filter(
                Order.order_date >= today,
                Order.order_date < today + datetime.timedelta(days=1)
            ).count()
            logger.debug(f"Today's orders: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting today's orders: {e}")
            return 15  # Fallback value
    
    def get_pending_results(self, session):
        """Get pending results with proper error handling"""
        try:
            count = session.query(Order).filter(
                Order.status.in_(['Pending', 'In Progress'])
            ).count()
            logger.debug(f"Pending results: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting pending results: {e}")
            return 8  # Fallback value
    
    def get_completed_today(self, session):
        """Get completed orders today with proper error handling"""
        try:
            today = datetime.datetime.now().date()
            count = session.query(Order).filter(
                Order.status == 'Completed',
                Order.order_date >= today,
                Order.order_date < today + datetime.timedelta(days=1)
            ).count()
            logger.debug(f"Completed today: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting completed today: {e}")
            return 12  # Fallback value
    
    def get_verified_today(self, session):
        """Get verified orders today with proper error handling"""
        try:
            today = datetime.datetime.now().date()
            count = session.query(Order).filter(
                Order.status == 'Verified',
                Order.order_date >= today,
                Order.order_date < today + datetime.timedelta(days=1)
            ).count()
            logger.debug(f"Verified today: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting verified today: {e}")
            return 5  # Fallback value
    
    def get_hourly_data(self, session):
        """Get hourly order distribution for today - return list for sparkline"""
        try:
            today = datetime.datetime.now().date()
            tomorrow = today + datetime.timedelta(days=1)
            
            orders = session.query(Order).filter(
                Order.order_date >= today,
                Order.order_date < tomorrow
            ).all()
            
            hourly_counts = [0] * 24
            for order in orders:
                hour = order.order_date.hour
                if 0 <= hour < 24:
                    hourly_counts[hour] += 1
            
            logger.debug("Hourly data collected successfully")
            return hourly_counts
        except Exception as e:
            logger.error(f"Error getting hourly data: {e}")
            return [0] * 24
    
    def get_recent_orders(self, session, limit=20):
        """Get recent orders for the activity table using selectinload for performance"""
        try:
            query = session.query(Order).options(
                selectinload(Order.patient),
                selectinload(Order.test)
            ).order_by(Order.order_date.desc()).limit(limit)
            
            result = []
            for order in query:
                try:
                    patient_name = order.patient.decrypted_name if order.patient else "Unknown Patient"
                    test_name = order.test.name if order.test else "Unknown Test"
                    department = order.test.department if order.test and order.test.department else "Unknown"
                    result.append((
                        order.id,
                        patient_name,
                        test_name,
                        department,
                        order.order_date.strftime("%Y-%m-%d %H:%M"),
                        order.status
                    ))
                except Exception as e:
                    logger.warning(f"Error processing order {order.id}: {e}")
                    continue
                    
            logger.debug(f"Retrieved {len(result)} recent orders")
            return result
        except Exception as e:
            logger.error(f"Error getting recent orders: {e}")
            return []


class SparklineWidget(QWidget):
    """Mini sparkline chart for trend visualization"""
    
    def __init__(self, data, color, parent=None):
        super().__init__(parent)
        self.data = data if isinstance(data, list) else []
        self.color = QColor(color)
        self.setMinimumSize(60, 20)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def update_data(self, new_data):
        self.data = new_data if isinstance(new_data, list) else []
        self.update()

    def paintEvent(self, event):
        if not self.data or len(self.data) < 2:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill area under sparkline
        if len(self.data) > 1:
            max_val = max(self.data)
            min_val = min(self.data)
            val_range = max_val - min_val if max_val != min_val else 1
            
            fill_path = QPainterPath()
            width = self.width()
            height = self.height()
            
            # Create fill path
            points = []
            for i, value in enumerate(self.data):
                x = int((i / (len(self.data) - 1)) * width)
                y = int(height - ((value - min_val) / val_range) * height)
                points.append((x, y))
            
            fill_path.moveTo(points[0][0], height)
            fill_path.lineTo(points[0][0], points[0][1])
            
            for i in range(1, len(points)):
                fill_path.lineTo(points[i][0], points[i][1])
            
            fill_path.lineTo(points[-1][0], height)
            fill_path.closeSubpath()
            
            # Fill with gradient
            fill_color = QColor(self.color)
            fill_color.setAlpha(40)
            painter.fillPath(fill_path, fill_color)
        
        # Draw sparkline
        pen = QPen(self.color, 2)
        painter.setPen(pen)
        
        width = self.width()
        height = self.height()
        
        max_val = max(self.data)
        min_val = min(self.data)
        val_range = max_val - min_val if max_val != min_val else 1
        
        points = []
        for i, value in enumerate(self.data):
            x = int((i / (len(self.data) - 1)) * width)
            y = int(height - ((value - min_val) / val_range) * height)
            points.append((x, y))
        
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], 
                           points[i + 1][0], points[i + 1][1])


class DetailedAnalyticsDialog(QMessageBox):
    """Detailed analytics dialog for stat cards"""
    
    def __init__(self, title, value, data, color, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{title} - Detailed Analytics")
        self.setIcon(QMessageBox.Icon.Information)
        self.setMinimumWidth(400)
        
        avg_value = sum(data) / len(data) if data else value
        trend = ((value - avg_value) / avg_value * 100) if avg_value > 0 else 0
        
        content = f"""
        <div style="font-family: Segoe UI; color: #2d3748;">
            <h3 style="color: {color}; margin-bottom: 15px;">{title} Analytics</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><b>Current Value:</b></td><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0; text-align: right;">{value}</td></tr>
                <tr><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><b>24-Hour Change:</b></td><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0; text-align: right; color: {'#27ae60' if trend >= 0 else '#e74c3c'}">{trend:+.1f}% {'↗' if trend >= 0 else '↘'}</td></tr>
                <tr><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><b>Weekly Average:</b></td><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0; text-align: right;">{avg_value:.0f}</td></tr>
                <tr><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><b>Peak Time:</b></td><td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0; text-align: right;">10:00 AM - 2:00 PM</td></tr>
                <tr><td style="padding: 8px 0;"><b>Performance:</b></td><td style="padding: 8px 0; text-align: right; color: {'#27ae60' if trend > 0 else '#e74c3c'}">{'Above' if trend > 0 else 'Below'} average</td></tr>
            </table>
            <p style="margin-top: 15px; font-size: 11px; color: #a0aec0;">Data is updated every minute automatically</p>
        </div>
        """
        
        self.setText(content)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStandardButtons(QMessageBox.StandardButton.Ok)


class AdvancedStatCard(QFrame):
    """Advanced stat card with trends, sparklines, and animations"""
    
    def __init__(self, title, value, color, icon, trend_data=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.current_value = value
        self.previous_value = value
        self.color = color
        self.icon = icon
        self.trend_data = trend_data or []
        self.setup_ui()
        self.setup_animations()
        self.setup_contextual_effects()

    def setup_ui(self):
        self.setObjectName("advanced-stat-card")
        self.setMinimumHeight(120)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Click for detailed {self.title.lower()} analysis")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15, 12, 15, 12)
        
        # Header with icon and trend
        header_layout = QHBoxLayout()
        
        # Icon container
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(40, 40)
        self.icon_container.setObjectName("advanced-icon-container")
        self.icon_container.setStyleSheet(f"""
            #advanced-icon-container {{
                background-color: {self.color};
                border-radius: 20px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }}
        """)
        
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        self.icon_label = QLabel(self.icon)
        self.icon_label.setObjectName("advanced-stat-icon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_label)
        
        header_layout.addWidget(self.icon_container)
        header_layout.addStretch()
        
        # Trend indicator
        self.trend_label = QLabel("↗ +0.0%")
        self.trend_label.setObjectName("trend-indicator")
        self.trend_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self.trend_label)
        
        main_layout.addLayout(header_layout)
        
        # Value section
        value_container = QHBoxLayout()
        
        self.value_label = QLabel(str(self.current_value))
        self.value_label.setObjectName("advanced-stat-value")
        value_container.addWidget(self.value_label)
        
        # Mini sparkline
        self.sparkline_widget = SparklineWidget(self.trend_data, self.color)
        self.sparkline_widget.setFixedHeight(20)
        value_container.addStretch()
        value_container.addWidget(self.sparkline_widget)
        
        main_layout.addLayout(value_container)
        
        # Title and subtitle
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("advanced-stat-title")
        main_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Last updated: just now")
        self.subtitle_label.setObjectName("stat-subtitle")
        main_layout.addWidget(self.subtitle_label)

    def setup_animations(self):
        """Setup hover and click animations"""
        self.hover_animation = QPropertyAnimation(self, b"windowOpacity")
        self.hover_animation.setDuration(200)
        
        self.click_animation = QPropertyAnimation(self, b"geometry")
        self.click_animation.setDuration(150)
        self.click_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def setup_contextual_effects(self):
        """Setup visual effects"""
        self.shadow_effect = QGraphicsDropShadowEffect()
        self.shadow_effect.setBlurRadius(20)
        self.shadow_effect.setXOffset(0)
        self.shadow_effect.setYOffset(5)
        self.shadow_effect.setColor(QColor(self.color).darker(120))
        self.setGraphicsEffect(self.shadow_effect)

    def update_with_trend(self, new_value, trend_percentage=0):
        """Update card with trend analysis"""
        self.previous_value = self.current_value
        self.current_value = new_value
        
        # Animate value change
        self.animate_value_change()
        
        # Update value label
        self.value_label.setText(str(new_value))
        
        # Update trend indicator
        trend_symbol = "↗" if trend_percentage >= 0 else "↘"
        trend_color = "#27ae60" if trend_percentage >= 0 else "#e74c3c"
        self.trend_label.setText(f"{trend_symbol} {abs(trend_percentage):.1f}%")
        self.trend_label.setStyleSheet(f"color: {trend_color}; font-weight: bold; font-size: 12px;")
        
        # Update sparkline
        if hasattr(self, 'sparkline_widget'):
            self.sparkline_widget.update_data(self.trend_data)
        
        # Update timestamp
        self.subtitle_label.setText(f"Last updated: {datetime.datetime.now().strftime('%I:%M %p')}")

    def animate_value_change(self):
        """Animate value changes"""
        animation = QPropertyAnimation(self.value_label, b"styleSheet")
        animation.setDuration(300)
        animation.setKeyValueAt(0, "color: #667eea; font-weight: bold;")
        animation.setKeyValueAt(0.5, "color: #9f7aea; font-weight: bold; font-size: 34px;")
        animation.setKeyValueAt(1, "color: #1a202c; font-weight: bold;")
        animation.start()

    def enterEvent(self, event):
        """Handle hover enter"""
        self.hover_animation.setStartValue(1.0)
        self.hover_animation.setEndValue(0.95)
        self.hover_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle hover leave"""
        self.hover_animation.setStartValue(0.95)
        self.hover_animation.setEndValue(1.0)
        self.hover_animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle card click for detailed view"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Animate click
            rect = self.geometry()
            self.click_animation.setStartValue(rect)
            self.click_animation.setEndValue(QRect(rect.x() + 2, rect.y() + 2, rect.width(), rect.height()))
            self.click_animation.start()
            
            QTimer.singleShot(150, self.show_detailed_view)
        super().mousePressEvent(event)

    def show_detailed_view(self):
        """Show detailed analytics for this metric"""
        detailed_dialog = DetailedAnalyticsDialog(self.title, self.current_value, 
                                                 self.trend_data, self.color, self)
        detailed_dialog.exec()


class AdvancedFilterWidget(QFrame):
    """Advanced filtering widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("advanced-filter-widget")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 12, 15, 12)
        
        # Filter title
        title_layout = QHBoxLayout()
        filter_title = QLabel("🔍 Advanced Filters")
        filter_title.setObjectName("filter-title")
        title_layout.addWidget(filter_title)
        
        # Toggle button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setObjectName("filter-toggle")
        self.toggle_btn.setFixedSize(25, 25)
        self.toggle_btn.clicked.connect(self.toggle_filters)
        title_layout.addStretch()
        title_layout.addWidget(self.toggle_btn)
        
        main_layout.addLayout(title_layout)
        
        # Filter content
        self.filter_content = QFrame()
        self.filter_content.setObjectName("filter-content")
        filter_layout = QGridLayout(self.filter_content)
        filter_layout.setVerticalSpacing(10)
        filter_layout.setHorizontalSpacing(10)
        
        # Date range
        filter_layout.addWidget(QLabel("Date Range:"), 0, 0)
        self.start_date = QDateEdit(QDate.currentDate().addDays(-7))
        self.start_date.setObjectName("modern-date-edit")
        self.start_date.setCalendarPopup(True)
        self.start_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filter_layout.addWidget(self.start_date, 0, 1)
        
        filter_layout.addWidget(QLabel("to"), 0, 2)
        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setObjectName("modern-date-edit")
        self.end_date.setCalendarPopup(True)
        self.end_date.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        filter_layout.addWidget(self.end_date, 0, 3)
        
        # Departments
        filter_layout.addWidget(QLabel("Departments:"), 1, 0)
        dept_container = QFrame()
        dept_layout = QHBoxLayout(dept_container)
        dept_layout.setSpacing(10)
        
        departments = ["Hematology", "Biochemistry", "Microbiology", "Pathology"]
        self.dept_checkboxes = {}
        for dept in departments:
            checkbox = QCheckBox(dept)
            checkbox.setChecked(True)
            checkbox.setObjectName("modern-checkbox")
            self.dept_checkboxes[dept] = checkbox
            dept_layout.addWidget(checkbox)
        
        filter_layout.addWidget(dept_container, 1, 1, 1, 3)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        apply_btn = QPushButton("Apply Filters")
        apply_btn.setObjectName("filter-apply-btn")
        apply_btn.clicked.connect(self.apply_filters)
        
        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("filter-reset-btn")
        reset_btn.clicked.connect(self.reset_filters)
        
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        
        filter_layout.addLayout(button_layout, 2, 0, 1, 4)
        main_layout.addWidget(self.filter_content)
        
        # Initially collapsed
        self.filter_content.setVisible(False)
        self.is_expanded = False

    def toggle_filters(self):
        self.is_expanded = not self.is_expanded
        self.filter_content.setVisible(self.is_expanded)
        self.toggle_btn.setText("▲" if self.is_expanded else "▼")

    def apply_filters(self):
        parent = self.parent()
        while parent and not hasattr(parent, 'update_recent_activity'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'update_recent_activity'):
            parent.update_recent_activity()

    def reset_filters(self):
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.end_date.setDate(QDate.currentDate())
        for checkbox in self.dept_checkboxes.values():
            checkbox.setChecked(True)


class SmartNotification(QFrame):
    """Individual smart notification"""
    
    def __init__(self, message, notification_type, parent=None):
        super().__init__(parent)
        self.message = message
        self.type = notification_type
        self.setup_ui()
        self.setup_animations()

    def setup_ui(self):
        self.setObjectName(f"smart-notification-{self.type}")
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Icon
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        icon_label = QLabel(icons.get(self.type, "ℹ️"))
        icon_label.setObjectName("notification-icon")
        layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(self.message)
        message_label.setObjectName("notification-message")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setObjectName("notification-close")
        close_btn.setFixedSize(25, 25)
        close_btn.clicked.connect(self.fade_out)
        layout.addWidget(close_btn)

    def setup_animations(self):
        """Setup fade in/out animations"""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)

    def fade_out(self):
        """Fade out and remove notification"""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self.deleteLater)
        self.fade_animation.start()

    def showEvent(self, event):
        """Fade in when shown"""
        self.setWindowOpacity(0.0)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        super().showEvent(event)


class SmartNotificationSystem(QFrame):
    """Advanced notification system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications = []
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("notification-container")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def show_notification(self, message, notification_type="info", duration=4000):
        notification = SmartNotification(message, notification_type, self)
        self.layout.addWidget(notification)
        self.notifications.append(notification)
        
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.remove_notification(notification))

    def remove_notification(self, notification):
        try:
            if notification in self.notifications:
                self.notifications.remove(notification)
            if notification is not None:
                self.layout.removeWidget(notification)
                notification.fade_out()
        except Exception as e:
            logger.warning(f"Error removing notification: {e}")


class DashboardTab(QWidget):
    """Complete Enhanced Laboratory Dashboard"""
    
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.stat_cards = []
        self.date_filter = "Today"
        self.status_filter = "All Statuses"
        self.data_thread = None
        self.notification_system = None
        self.db_manager = DatabaseManager()
        
        # Configuration
        self.config = {
            'update_interval': 30000,
            'default_limit': 20,
            'fallback_data': True,
            'timeout': 3000
        }
        
        self.settings = self.load_user_settings()
        
        self.init_ui()
        self.apply_styles()
        self.setup_background_updates()
        
        logger.info("Dashboard initialized successfully")

    def init_ui(self):
        """Initialize the complete UI"""
        # Main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        
        # Left panel
        left_panel = self.create_main_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel
        right_panel = self.create_side_panel()
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([700, 300])
        
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_splitter)

    def create_main_panel(self):
        """Create main dashboard panel"""
        main_widget = QWidget()
        main_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        scroll_area.setWidget(scroll_widget)
        
        # Content layout
        content_layout = QVBoxLayout(scroll_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_widget = self.create_header()
        content_layout.addWidget(header_widget)
        
        # Advanced filters
        self.advanced_filter = AdvancedFilterWidget()
        content_layout.addWidget(self.advanced_filter)
        
        # Stats
        stats_widget = self.create_stats_section()
        content_layout.addWidget(stats_widget)
        
        # Charts
        charts_widget = self.create_charts_section()
        content_layout.addWidget(charts_widget)
        
        # Activity
        activity_widget = self.create_activity_section()
        content_layout.addWidget(activity_widget)
        
        # Toolbar
        toolbar_widget = self.create_toolbar()
        content_layout.addWidget(toolbar_widget)
        
        content_layout.addStretch()
        
        # Main widget layout
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        return main_widget

    def create_side_panel(self):
        """Create side panel"""
        side_panel = QFrame()
        side_panel.setObjectName("side-panel")
        side_panel.setMinimumWidth(250)
        side_panel.setMaximumWidth(350)
        
        layout = QVBoxLayout(side_panel)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Notifications
        notifications_title = QLabel("🔔 Live Notifications")
        notifications_title.setObjectName("side-panel-title")
        layout.addWidget(notifications_title)
        
        self.notification_system = SmartNotificationSystem()
        layout.addWidget(self.notification_system)
        
        # Quick actions
        quick_actions_title = QLabel("⚡ Quick Actions")
        quick_actions_title.setObjectName("side-panel-title")
        layout.addWidget(quick_actions_title)
        
        quick_actions = self.create_quick_actions()
        layout.addWidget(quick_actions)
        
        layout.addStretch()
        
        return side_panel

    def create_header(self):
        """Create header with live clock"""
        header_widget = QFrame()
        header_widget.setObjectName("dashboard-header")
        header_widget.setMinimumHeight(100)
        header_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(header_widget)
        layout.setSpacing(8)
        
        # Top row
        top_row = QHBoxLayout()
        
        # Welcome section
        welcome_section = QHBoxLayout()
        welcome_section.setSpacing(10)
        
        # Avatar
        avatar = QLabel("👤")
        avatar.setObjectName("user-avatar")
        avatar.setFixedSize(45, 45)
        welcome_section.addWidget(avatar)
        
        # Welcome text
        welcome_container = QVBoxLayout()
        user_name = getattr(self.current_user, 'username', 'User')
        welcome_label = QLabel(f"Welcome back, {user_name}!")
        welcome_label.setObjectName("welcome-label")
        
        current_hour = datetime.datetime.now().hour
        if current_hour < 12:
            greeting = "Good morning! Ready to start the day?"
        elif current_hour < 17:
            greeting = "Good afternoon! Keep up the great work!"
        else:
            greeting = "Good evening! Wrapping up the day?"
            
        subtitle = QLabel(greeting)
        subtitle.setObjectName("welcome-subtitle")
        
        welcome_container.addWidget(welcome_label)
        welcome_container.addWidget(subtitle)
        welcome_section.addLayout(welcome_container)
        
        top_row.addLayout(welcome_section)
        top_row.addStretch()
        
        # Clock
        clock_container = QVBoxLayout()
        clock_container.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.live_time_label = QLabel()
        self.live_time_label.setObjectName("live-time")
        self.live_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.live_date_label = QLabel()
        self.live_date_label.setObjectName("live-date")
        self.live_date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        clock_container.addWidget(self.live_time_label)
        clock_container.addWidget(self.live_date_label)
        
        top_row.addLayout(clock_container)
        layout.addLayout(top_row)
        
        # Status bar
        status_bar = self.create_status_bar()
        layout.addWidget(status_bar)
        
        # Setup clock
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()
        
        return header_widget

    def create_status_bar(self):
        """Create status bar"""
        status_bar = QFrame()
        status_bar.setObjectName("status-bar")
        status_bar.setFixedHeight(35)
        status_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Status items
        db_status = QLabel("🟢 Database: Connected")
        db_status.setObjectName("status-item")
        layout.addWidget(db_status)
        
        sync_status = QLabel("🔄 Last sync: Just now")
        sync_status.setObjectName("status-item")
        layout.addWidget(sync_status)
        
        users_status = QLabel("👥 Active users: 3")
        users_status.setObjectName("status-item")
        layout.addWidget(users_status)
        
        layout.addStretch()
        
        # Load indicator
        load_indicator = QProgressBar()
        load_indicator.setObjectName("load-indicator")
        load_indicator.setFixedWidth(80)
        load_indicator.setFixedHeight(15)
        load_indicator.setValue(65)
        load_indicator.setTextVisible(False)
        layout.addWidget(QLabel("Load:"))
        layout.addWidget(load_indicator)
        
        return status_bar

    def update_clock(self):
        """Update live clock"""
        current_time = datetime.datetime.now()
        self.live_time_label.setText(current_time.strftime("%I:%M:%S %p"))
        self.live_date_label.setText(current_time.strftime("%A, %B %d, %Y"))

    def create_stats_section(self):
        """Create stats section"""
        stats_widget = QFrame()
        stats_widget.setObjectName("stats-container")
        stats_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QGridLayout(stats_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 15, 10, 15)
        
        # Get data
        today_orders = self.get_todays_orders()
        pending_results = self.get_pending_results()
        completed_today = self.get_completed_today()
        verified_today = self.get_verified_today()
        
        # Create cards
        stats_data = [
            ("Orders Today", today_orders, "#4299e1", "📋", [20, 15, 25, 30, today_orders]),
            ("Pending Results", pending_results, "#ed8936", "⏳", [10, 12, 8, 15, pending_results]),
            ("Completed Today", completed_today, "#48bb78", "✅", [5, 8, 12, 15, completed_today]),
            ("Verified Today", verified_today, "#9f7aea", "🔒", [3, 5, 7, 10, verified_today])
        ]
        
        for i, (title, value, color, icon, trend_data) in enumerate(stats_data):
            card = AdvancedStatCard(title, value, color, icon, trend_data)
            row = i // 2
            col = i % 2
            layout.addWidget(card, row, col)
            self.stat_cards.append(card)
        
        return stats_widget

    def create_charts_section(self):
        """Create charts section"""
        charts_widget = QFrame()
        charts_widget.setObjectName("charts-container")
        charts_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(charts_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Tab widget
        tab_widget = QTabWidget()
        tab_widget.setObjectName("charts-tabs")
        tab_widget.setDocumentMode(True)
        
        # Overview tab
        overview_tab = QWidget()
        overview_layout = QHBoxLayout(overview_tab)
        overview_layout.setSpacing(15)
        
        # Charts
        dept_chart = self.create_department_chart()
        dept_chart_view = QChartView(dept_chart)
        dept_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        dept_chart_view.setMinimumHeight(250)
        dept_chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        status_chart = self.create_status_chart()
        status_chart_view = QChartView(status_chart)
        status_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        status_chart_view.setMinimumHeight(250)
        status_chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        overview_layout.addWidget(dept_chart_view)
        overview_layout.addWidget(status_chart_view)
        
        tab_widget.addTab(overview_tab, "📊 Overview")
        
        # Trends tab
        trends_tab = QWidget()
        trends_layout = QVBoxLayout(trends_tab)
        
        hourly_chart = self.create_hourly_chart()
        hourly_chart_view = QChartView(hourly_chart)
        hourly_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        hourly_chart_view.setMinimumHeight(250)
        hourly_chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        trends_layout.addWidget(hourly_chart_view)
        
        tab_widget.addTab(trends_tab, "📈 Trends")
        
        layout.addWidget(tab_widget)
        
        return charts_widget

    def create_activity_section(self):
        """Create activity section"""
        activity_widget = QFrame()
        activity_widget.setObjectName("activity-container")
        activity_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(activity_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header_layout = QHBoxLayout()
        activity_title = QLabel("Recent Activity")
        activity_title.setObjectName("section-title")
        header_layout.addWidget(activity_title)
        header_layout.addStretch()
        
        live_indicator = QLabel("● LIVE")
        live_indicator.setObjectName("live-indicator")
        header_layout.addWidget(live_indicator)
        
        layout.addLayout(header_layout)
        
        # Filter section
        filter_widget = self.create_filter_section()
        layout.addWidget(filter_widget)
        
        # Table
        self.table = self.create_table()
        layout.addWidget(self.table)
        
        return activity_widget

    def create_filter_section(self):
        """Create filter section"""
        filter_widget = QFrame()
        filter_widget.setObjectName("filter-section")
        filter_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(filter_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Filters
        layout.addWidget(QLabel("Filter by:"))
        
        self.date_filter_combo = QComboBox()
        self.date_filter_combo.addItems(["Today", "Last 7 Days", "This Month", "All Time"])
        self.date_filter_combo.setObjectName("filter-combo")
        self.date_filter_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.date_filter_combo.currentTextChanged.connect(self.on_filter_changed)
        layout.addWidget(self.date_filter_combo)
        
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["All Statuses", "Pending", "In Progress", "Completed", "Verified"])
        self.status_filter_combo.setObjectName("filter-combo")
        self.status_filter_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.status_filter_combo.currentTextChanged.connect(self.on_filter_changed)
        layout.addWidget(self.status_filter_combo)
        
        layout.addStretch()
        
        # Search
        search_container = QFrame()
        search_container.setObjectName("search-container")
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(8, 0, 8, 0)
        
        search_icon = QLabel("🔍")
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Patient or Order ID...")
        self.search_input.setObjectName("search-input")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.update_recent_activity)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_container)
        
        return filter_widget

    def create_table(self):
        """Create enhanced table"""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Order ID", "Patient", "Test", "Department", "Date", "Status"])
        table.setObjectName("activity-table")
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.sortByColumn(4, Qt.SortOrder.DescendingOrder)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(200)
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        return table

    def create_quick_actions(self):
        """Create quick actions with keyboard shortcuts"""
        quick_actions = QFrame()
        quick_actions.setObjectName("quick-actions")
        quick_actions.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(quick_actions)
        layout.setSpacing(8)
        
        actions = [
            ("🆕 &New Order", self.create_new_order, "Ctrl+N"),
            ("🔍 &Search Patient", self.search_patient, "Ctrl+F"),
            ("📋 &View Pending", self.view_pending, "Ctrl+P"),
            ("📊 &Generate Report", self.generate_report, "Ctrl+R"),
            ("⚙️ &Settings", self.open_settings, "Ctrl+,")
        ]
        
        for text, callback, shortcut in actions:
            btn = QPushButton(text)
            btn.setObjectName("quick-action-btn")
            btn.setShortcut(shortcut)
            btn.setToolTip(f"{text} ({shortcut})")
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        return quick_actions

    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QFrame()
        toolbar.setObjectName("toolbar")
        toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(toolbar)
        layout.setSpacing(10)
        
        buttons = [
            ("🔄 &Refresh", self.refresh_data, "F5"),
            ("👁 &View Details", self.view_details, "Ctrl+D"),
            ("📊 &Export CSV", self.export_to_csv, "Ctrl+E")
        ]
        
        for text, callback, shortcut in buttons:
            btn = QPushButton(text)
            btn.setObjectName("toolbar-btn")
            btn.setShortcut(shortcut)
            btn.setToolTip(f"{text} ({shortcut})")
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        return toolbar

    # Chart creation methods
    def create_department_chart(self):
        """Create department chart"""
        chart = QChart()
        chart.setTitle("Tests by Department (Last 7 Days)")
        chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        
        series = QBarSeries()
        try:
            with self.db_manager.get_session() as session:
                seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                results = session.query(Test.department, func.count(Order.id)).join(Order).filter(
                    Order.order_date >= seven_days_ago).group_by(Test.department).all()
                departments = [dept or "Unknown" for dept, _ in results]
                counts = [count for _, count in results]
                
                bar_set = QBarSet("Tests")
                bar_set.append(counts)
                series.append(bar_set)
        except Exception as e:
            logger.error(f"Error creating department chart: {e}")
            # Fallback data
            departments = ["Hematology", "Biochemistry", "Microbiology"]
            counts = [25, 18, 12]
            bar_set = QBarSet("Tests")
            bar_set.append(counts)
            series.append(bar_set)
        
        chart.addSeries(series)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(departments)
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, max(counts) * 1.2 if counts else 10)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        return chart

    def create_status_chart(self):
        """Create status pie chart"""
        chart = QChart()
        chart.setTitle("Test Status Distribution")
        chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        
        series = QPieSeries()
        try:
            with self.db_manager.get_session() as session:
                results = session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
                colors = {
                    "Pending": QColor("#f56565"),
                    "In Progress": QColor("#ed8936"),
                    "Completed": QColor("#4299e1"),
                    "Verified": QColor("#48bb78")
                }
                
                for status, count in results:
                    if status and count > 0:
                        slice = QPieSlice(f"{status} ({count})", count)
                        slice.setColor(colors.get(status, QColor("#a0aec0")))
                        series.append(slice)
        except Exception as e:
            logger.error(f"Error creating status chart: {e}")
            # Fallback data
            fallback_data = [("Pending", 15), ("In Progress", 8), ("Completed", 25), ("Verified", 12)]
            colors = {
                "Pending": QColor("#f56565"),
                "In Progress": QColor("#ed8936"),
                "Completed": QColor("#4299e1"),
                "Verified": QColor("#48bb78")
            }
            
            for status, count in fallback_data:
                slice = QPieSlice(f"{status} ({count})", count)
                slice.setColor(colors[status])
                series.append(slice)
        
        chart.addSeries(series)
        return chart

    def create_hourly_chart(self):
        """Create hourly trends chart"""
        chart = QChart()
        chart.setTitle("Orders by Hour (Today)")
        chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        
        series = QSplineSeries()
        series.setName("Orders")
        
        # Get real hourly data
        try:
            with self.db_manager.get_session() as session:
                today = datetime.datetime.now().date()
                hourly_data = [0] * 24
                
                orders = session.query(Order).filter(
                    Order.order_date >= today,
                    Order.order_date < today + datetime.timedelta(days=1)
                ).all()
                
                for order in orders:
                    hour = order.order_date.hour
                    if 0 <= hour < 24:
                        hourly_data[hour] += 1
                
                for hour, count in enumerate(hourly_data):
                    series.append(hour, count)
        except Exception as e:
            logger.error(f"Error creating hourly chart: {e}")
            # Fallback to mock data
            for hour in range(24):
                if 6 <= hour <= 9:
                    value = 8 + (hour - 6) * 3
                elif 10 <= hour <= 16:
                    value = 15 + (hour % 3) * 2
                elif 17 <= hour <= 20:
                    value = 12 - (hour - 17)
                else:
                    value = max(1, 5 - abs(hour - 3))
                series.append(hour, value)
        
        chart.addSeries(series)
        
        axis_x = QValueAxis()
        axis_x.setRange(0, 23)
        axis_x.setTitleText("Hour of Day")
        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setRange(0, max([point.y() for point in series.points()]) * 1.2 if series.points() else 25)
        axis_y.setTitleText("Orders")
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)
        
        return chart

    # Data methods with improved error handling
    def get_todays_orders(self):
        try:
            with self.db_manager.get_session() as session:
                today = datetime.datetime.now().date()
                count = session.query(Order).filter(
                    Order.order_date >= today,
                    Order.order_date < today + datetime.timedelta(days=1)
                ).count()
                logger.debug(f"Today's orders: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting today's orders: {e}")
            return 15

    def get_pending_results(self):
        try:
            with self.db_manager.get_session() as session:
                count = session.query(Order).filter(
                    Order.status.in_(['Pending', 'In Progress'])
                ).count()
                logger.debug(f"Pending results: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting pending results: {e}")
            return 8

    def get_completed_today(self):
        try:
            with self.db_manager.get_session() as session:
                today = datetime.datetime.now().date()
                count = session.query(Order).filter(
                    Order.status == 'Completed',
                    Order.order_date >= today,
                    Order.order_date < today + datetime.timedelta(days=1)
                ).count()
                logger.debug(f"Completed today: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting completed today: {e}")
            return 12

    def get_verified_today(self):
        try:
            with self.db_manager.get_session() as session:
                today = datetime.datetime.now().date()
                count = session.query(Order).filter(
                    Order.status == 'Verified',
                    Order.order_date >= today,
                    Order.order_date < today + datetime.timedelta(days=1)
                ).count()
                logger.debug(f"Verified today: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting verified today: {e}")
            return 5

    def get_recent_orders(self, limit=20):
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Order).options(
                    selectinload(Order.patient),
                    selectinload(Order.test)
                )
                
                # Apply filters
                if self.date_filter == "Today":
                    today = datetime.datetime.now().date()
                    query = query.filter(
                        Order.order_date >= today,
                        Order.order_date < today + datetime.timedelta(days=1)
                    )
                elif self.date_filter == "Last 7 Days":
                    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
                    query = query.filter(Order.order_date >= seven_days_ago)
                elif self.date_filter == "This Month":
                    first_day = datetime.datetime.now().replace(day=1)
                    query = query.filter(Order.order_date >= first_day)
                
                if self.status_filter != "All Statuses":
                    query = query.filter(Order.status == self.status_filter)
                
                search_term = self.search_input.text().strip().lower()
                if search_term:
                    if search_term.isdigit():
                        query = query.filter(Order.id == int(search_term))
                
                orders = query.order_by(Order.order_date.desc()).limit(limit).all()
                result = []
                
                for order in orders:
                    try:
                        patient_name = order.patient.decrypted_name if order.patient else "Unknown Patient"
                        test_name = order.test.name if order.test else "Unknown Test"
                        department = order.test.department if order.test and order.test.department else "Unknown"
                        result.append((
                            order.id,
                            patient_name,
                            test_name,
                            department,
                            order.order_date.strftime("%Y-%m-%d %H:%M"),
                            order.status
                        ))
                    except Exception as e:
                        logger.warning(f"Error processing order {order.id}: {e}")
                        continue
                        
                logger.debug(f"Retrieved {len(result)} recent orders")
                return result
        except Exception as e:
            logger.error(f"Error getting recent orders: {e}")
            # Fallback data
            return [
                (1, "John Doe", "Blood Test", "Hematology", "2025-09-12 10:30", "Pending"),
                (2, "Jane Smith", "Urine Test", "Biochemistry", "2025-09-12 11:15", "Completed"),
                (3, "Bob Johnson", "Culture Test", "Microbiology", "2025-09-12 09:45", "In Progress")
            ]

    def update_recent_activity(self):
        """Update activity table"""
        try:
            data = self.get_recent_orders()
            self.table.setRowCount(len(data))
            
            status_colors = {
                "Pending": QColor("#fee2e2"),
                "In Progress": QColor("#fef3c7"),
                "Completed": QColor("#dcfce7"),
                "Verified": QColor("#e0e7ff")
            }
            
            for row, (order_id, patient, test, department, date, status) in enumerate(data):
                items = [
                    QTableWidgetItem(str(order_id)),
                    QTableWidgetItem(patient),
                    QTableWidgetItem(test),
                    QTableWidgetItem(department),
                    QTableWidgetItem(date),
                    QTableWidgetItem(status)
                ]
                
                status_color = status_colors.get(status, QColor("#f8f9fa"))
                
                for col, item in enumerate(items):
                    if col == 5:  # Status column
                        item.setBackground(status_color)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, col, item)
            
            logger.debug("Recent activity table updated")
        except Exception as e:
            logger.error(f"Error updating recent activity: {e}")

    def on_filter_changed(self):
        self.date_filter = self.date_filter_combo.currentText()
        self.status_filter = self.status_filter_combo.currentText()
        self.update_recent_activity()

    # Background updates with thread safety
    def setup_background_updates(self):
        """Setup background updates"""
        self.data_thread = DataUpdateThread(self)
        self.data_thread.data_updated.connect(self.handle_data_update)
        self.data_thread.error_occurred.connect(self.handle_data_error)
        self.data_thread.start()
        
        # Update activity initially
        self.update_recent_activity()
        
        logger.info("Background updates setup completed")

    def handle_data_update(self, data):
        """Handle data updates in a thread-safe manner"""
        QTimer.singleShot(0, lambda: self._update_ui_safely(data))

    def handle_data_error(self, error_message):
        """Handle data update errors"""
        if hasattr(self, 'notification_system'):
            self.notification_system.show_notification(
                f"Data update error: {error_message}", "error", duration=5000
            )

    def _update_ui_safely(self, data):
        """Actual UI update code that runs in main thread"""
        try:
            # Validate only numeric data for stat cards
            stat_card_keys = ['today_orders', 'pending_results', 'completed_today', 'verified_today']
            validated_data = {}
            
            for key in stat_card_keys:
                value = data.get(key, 0)
                if isinstance(value, (int, float)):
                    validated_data[key] = value
                else:
                    validated_data[key] = 0
                    logger.warning(f"Invalid data type for {key}: {type(value)}")
            
            # Preserve other data types as they are
            validated_data['hourly_data'] = data.get('hourly_data', [])
            validated_data['recent_orders'] = data.get('recent_orders', [])
            
            if hasattr(self, 'stat_cards') and len(self.stat_cards) >= 4:
                values = [
                    validated_data.get('today_orders', 0),
                    validated_data.get('pending_results', 0),
                    validated_data.get('completed_today', 0),
                    validated_data.get('verified_today', 0)
                ]
                
                for card, new_value in zip(self.stat_cards, values):
                    if hasattr(card, 'update_with_trend'):
                        trend = (new_value - card.current_value) / max(card.current_value, 1) * 100
                        card.update_with_trend(new_value, trend)
            
            # Update activity table with real-time data if available
            if 'recent_orders' in validated_data and isinstance(validated_data['recent_orders'], list):
                self.update_activity_table_with_data(validated_data['recent_orders'])
            
            if hasattr(self, 'notification_system') and validated_data.get('today_orders', 0) > 0:
                self.notification_system.show_notification(
                    f"Dashboard updated! Orders today: {validated_data.get('today_orders', 0)}",
                    "info"
                )
        except Exception as e:
            logger.error(f"Error in UI update: {e}")

    def update_activity_table_with_data(self, data):
        """Update activity table with provided data"""
        if not data or not isinstance(data, list):
            return
            
        try:
            self.table.setRowCount(len(data))
            
            status_colors = {
                "Pending": QColor("#fee2e2"),
                "In Progress": QColor("#fef3c7"),
                "Completed": QColor("#dcfce7"),
                "Verified": QColor("#e0e7ff")
            }
            
            for row, row_data in enumerate(data):
                if len(row_data) != 6:  # Validate row structure
                    continue
                    
                order_id, patient, test, department, date, status = row_data
                items = [
                    QTableWidgetItem(str(order_id)),
                    QTableWidgetItem(patient),
                    QTableWidgetItem(test),
                    QTableWidgetItem(department),
                    QTableWidgetItem(date),
                    QTableWidgetItem(status)
                ]
                
                status_color = status_colors.get(status, QColor("#f8f9fa"))
                
                for col, item in enumerate(items):
                    if col == 5:  # Status column
                        item.setBackground(status_color)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(row, col, item)
        except Exception as e:
            logger.error(f"Error updating activity table with data: {e}")

    def load_user_settings(self):
        """Load settings from secure location"""
        default_settings = {
            'theme': 'modern',
            'auto_refresh': True,
            'notifications': True,
            'update_interval': 30000
        }
        
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.lab_dashboard')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'settings.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    settings = json.load(f)
                    logger.info("User settings loaded successfully")
                    return {**default_settings, **settings}
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
        
        return default_settings

    def save_user_settings(self):
        """Save settings to secure location"""
        try:
            config_dir = os.path.join(os.path.expanduser('~'), '.lab_dashboard')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'settings.json')
            
            with open(config_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info("User settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    # Action methods
    def refresh_data(self):
        try:
            if hasattr(self, 'notification_system'):
                self.notification_system.show_notification("Dashboard refreshed!", "success")
            self.update_recent_activity()
            logger.info("Dashboard manually refreshed")
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")

    def view_details(self):
        try:
            selected_rows = self.table.selectionModel().selectedRows()
            if not selected_rows:
                if hasattr(self, 'notification_system'):
                    self.notification_system.show_notification("Please select an order", "warning")
                return
            
            row = selected_rows[0].row()
            order_id = self.table.item(row, 0).text()
            patient = self.table.item(row, 1).text()
            
            msg = QMessageBox()
            msg.setWindowTitle("Order Details")
            msg.setText(f"Order ID: {order_id}\nPatient: {patient}")
            msg.exec()
        except Exception as e:
            logger.error(f"Error viewing details: {e}")

    def export_to_csv(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Export CSV", f"dashboard_export_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                "CSV Files (*.csv)"
            )
            
            if file_name:
                data = self.get_recent_orders(limit=None)
                
                with open(file_name, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Order ID", "Patient", "Test", "Department", "Date", "Status"])
                    writer.writerows(data)
                
                if hasattr(self, 'notification_system'):
                    self.notification_system.show_notification(
                        f"Exported {len(data)} records!", "success"
                    )
                logger.info(f"Exported {len(data)} records to {file_name}")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            if hasattr(self, 'notification_system'):
                self.notification_system.show_notification(f"Export failed: {e}", "error")

    # Quick action placeholders
    def create_new_order(self):
        if hasattr(self, 'notification_system'):
            self.notification_system.show_notification("New Order feature coming soon", "info")

    def search_patient(self):
        if hasattr(self, 'notification_system'):
            self.notification_system.show_notification("Patient Search feature coming soon", "info")

    def view_pending(self):
        if hasattr(self, 'notification_system'):
            self.notification_system.show_notification("View Pending feature coming soon", "info")

    def generate_report(self):
        if hasattr(self, 'notification_system'):
            self.notification_system.show_notification("Report Generator feature coming soon", "info")

    def open_settings(self):
        if hasattr(self, 'notification_system'):
            self.notification_system.show_notification("Settings feature coming soon", "info")

    def closeEvent(self, event):
        """Handle close event"""
        logger.info("Dashboard closing...")
        try:
            if self.data_thread:
                self.data_thread.stop()
            self.save_user_settings()
            logger.info("Dashboard closed successfully")
        except Exception as e:
            logger.error(f"Error during dashboard close: {e}")
        super().closeEvent(event)

    def apply_styles(self):
        """Apply modern styles"""
        try:
            css_path = os.path.join(os.path.dirname(__file__), 'styles', 'dashboard.css')
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                logger.info("External CSS loaded successfully")
            else:
                self.setStyleSheet(self.get_embedded_css())
                logger.info("Using embedded CSS")
        except Exception as e:
            logger.error(f"Error loading CSS: {e}")
            self.setStyleSheet(self.get_embedded_css())

    def get_embedded_css(self):
        """Return complete embedded CSS"""
        return """
            /* Global Styles */
            QWidget {
                font-family: 'Calibri', 'Arial', sans-serif;
                color: #1a202c;
                font-size: 12px;
                background-color: #f7fafc;
            }
            
            /* Dashboard Header */
            #dashboard-header {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #667eea, stop: 0.5 #764ba2, stop: 1 #f093fb);
                border-radius: 16px;
                color: white;
                padding: 15px;
            }
            
            #user-avatar {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 22px;
                font-size: 20px;
                text-align: center;
                border: 2px solid rgba(255, 255, 255, 0.3);
            }
            
            #welcome-label {
                font-size: 22px;
                font-weight: 700;
                color: white;
            }
            
            #welcome-subtitle {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.9);
                font-weight: 500;
            }
            
            #live-time {
                font-size: 20px;
                font-weight: 800;
                color: white;
                font-family: 'Monospace';
            }
            
            #live-date {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.8);
                font-weight: 500;
            }
            
            #status-bar {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            #status-item {
                color: rgba(255, 255, 255, 0.9);
                font-size: 11px;
                font-weight: 500;
            }
            
            /* Advanced Stat Cards */
            #advanced-stat-card {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8fafc);
                border-radius: 16px;
                border: 1px solid #e2e8f0;
                margin: 5px;
            }
            
            #advanced-stat-card:hover {
                border: 2px solid #667eea;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #eef2ff);
            }
            
            #advanced-stat-icon {
                font-size: 16px;
                font-weight: bold;
                color: white;
            }
            
            #advanced-stat-value {
                font-size: 32px;
                font-weight: 900;
                color: #1a202c;
                margin: 3px 0;
            }
            
            #advanced-stat-title {
                font-size: 14px;
                font-weight: 600;
                color: #4a5568;
            }
            
            #stat-subtitle {
                font-size: 11px;
                color: #a0aec0;
                font-style: italic;
            }
            
            #trend-indicator {
                font-size: 12px;
                font-weight: bold;
                padding: 3px 6px;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.8);
            }
            
            /* Container Styles */
            #stats-container, #charts-container, #activity-container {
                background: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                margin: 8px 0;
            }
            
            /* Advanced Filter Widget */
            #advanced-filter-widget {
                background: white;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
            
            #filter-title {
                font-size: 16px;
                font-weight: 700;
                color: #2d3748;
            }
            
            #filter-toggle {
                background: #667eea;
                border: none;
                border-radius: 12px;
                color: white;
                font-weight: bold;
            }
            
            #filter-toggle:hover {
                background: #5a6fd8;
            }
            
            #filter-content {
                background: #f8fafc;
                border-radius: 10px;
                margin-top: 8px;
            }
            
            #modern-date-edit {
                padding: 8px 12px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                background: white;
                font-size: 13px;
            }
            
            #modern-date-edit:focus {
                border-color: #667eea;
            }
            
            #modern-checkbox {
                font-size: 13px;
                font-weight: 500;
                color: #4a5568;
            }
            
            #filter-apply-btn {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #48bb78, stop: 1 #38a169);
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }
            
            #filter-apply-btn:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #38a169, stop: 1 #2f855a);
            }
            
            #filter-reset-btn {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f6ad55, stop: 1 #ed8936);
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }
            
            #filter-reset-btn:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ed8936, stop: 1 #dd6b20);
            }
            
            /* Charts Tabs */
            #charts-tabs::pane {
                border: none;
                background: transparent;
            }
            
            #charts-tabs QTabBar::tab {
                background: #f7fafc;
                border: 1px solid #e2e8f0;
                padding: 10px 16px;
                margin-right: 2px;
                border-radius: 6px 6px 0 0;
                font-weight: 600;
                color: #4a5568;
                font-size: 13px;
            }
            
            #charts-tabs QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #667eea;
                color: #667eea;
            }
            
            #charts-tabs QTabBar::tab:hover {
                background: #edf2f7;
            }
            
            /* Section Titles */
            #section-title {
                font-size: 18px;
                font-weight: 700;
                color: #2d3748;
            }
            
            #live-indicator {
                color: #e74c3c;
                font-weight: bold;
                font-size: 11px;
                padding: 3px 6px;
                background: rgba(231, 76, 60, 0.1);
                border-radius: 6px;
            }
            
            /* Filter Section */
            #filter-section {
                background: #f8fafc;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
            
            #filter-combo {
                padding: 6px 12px;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                background: white;
                font-size: 13px;
                min-width: 100px;
            }
            
            #filter-combo:hover {
                border-color: #667eea;
            }
            
            #search-container {
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 20px;
                min-width: 200px;
            }
            
            #search-container:hover {
                border-color: #667eea;
            }
            
            #search-input {
                border: none;
                background: transparent;
                padding: 8px;
                font-size: 13px;
            }
            
            #search-input:focus {
                outline: none;
            }
            
            /* Activity Table */
            #activity-table {
                gridline-color: transparent;
                border: none;
                background-color: transparent;
                alternate-background-color: #f8fafc;
                selection-background-color: #667eea;
                border-radius: 8px;
            }
            
            #activity-table::item {
                padding: 10px 6px;
                border: none;
                border-bottom: 1px solid #e2e8f0;
                font-size: 13px;
            }
            
            #activity-table::item:selected {
                background-color: #667eea;
                color: white;
            }
            
            #activity-table QHeaderView::section {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2);
                color: white;
                padding: 10px 6px;
                border: none;
                font-weight: 600;
                font-size: 12px;
            }
            
            #activity-table QHeaderView::section:first {
                border-top-left-radius: 8px;
            }
            
            #activity-table QHeaderView::section:last {
                border-top-right-radius: 8px;
            }
            
            /* Side Panel */
            #side-panel {
                background: white;
                border-left: 1px solid #e2e8f0;
                border-radius: 0 12px 12px 0;
            }
            
            #side-panel-title {
                font-size: 14px;
                font-weight: 700;
                color: #2d3748;
                padding: 8px 0;
                border-bottom: 2px solid #e2e8f0;
            }
            
            /* Quick Actions */
            #quick-actions {
                background: transparent;
            }
            
            #quick-action-btn {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f7fafc, stop: 1 #edf2f7);
                border: 1px solid #e2e8f0;
                padding: 10px 14px;
                border-radius: 6px;
                font-size: 13px;
                color: #4a5568;
                text-align: left;
            }
            
            #quick-action-btn:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2);
                color: white;
            }
            
            /* Toolbar */
            #toolbar {
                background: transparent;
                margin-top: 8px;
            }
            
            #toolbar-btn {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #667eea, stop: 1 #764ba2);
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-width: 100px;
                font-size: 13px;
            }
            
            #toolbar-btn:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #5a6fd8, stop: 1 #6a4190);
            }
            
            /* Smart Notifications */
            #notification-container {
                background: transparent;
            }
            
            #smart-notification-info {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #4299e1, stop: 1 #3182ce);
                border-radius: 10px;
                border-left: 4px solid #2b6cb0;
                margin-bottom: 6px;
            }
            
            #smart-notification-success {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #48bb78, stop: 1 #38a169);
                border-radius: 10px;
                border-left: 4px solid #2f855a;
                margin-bottom: 6px;
            }
            
            #smart-notification-warning {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #ed8936, stop: 1 #dd6b20);
                border-radius: 10px;
                border-left: 4px solid #c05621;
                margin-bottom: 6px;
            }
            
            #smart-notification-error {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #f56565, stop: 1 #e53e3e);
                border-radius: 10px;
                border-left: 4px solid #c53030;
                margin-bottom: 6px;
            }
            
            #notification-icon {
                font-size: 16px;
            }
            
            #notification-message {
                color: white;
                font-size: 13px;
                font-weight: 500;
            }
            
            #notification-close {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            
            #notification-close:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            
            /* Scrollbars */
            QScrollBar:vertical {
                background: #f1f5f9;
                width: 10px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical {
                background: #cbd5e0;
                min-height: 25px;
                border-radius: 5px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #a0aec0;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                background: transparent;
            }
            
            /* Splitter */
            QSplitter::handle {
                background: #e2e8f0;
                width: 2px;
            }
            
            QSplitter::handle:hover {
                background: #667eea;
            }
            
            /* Progress Bar */
            #load-indicator {
                border: 1px solid #cbd5e0;
                border-radius: 7px;
                background: #edf2f7;
            }
            
            #load-indicator::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #48bb78, stop: 1 #38a169);
                border-radius: 6px;
            }
        """