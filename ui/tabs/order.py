from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QToolTip,
    QLabel, QMessageBox, QDateTimeEdit, QListWidget, QListWidgetItem,
    QScrollArea, QLineEdit, QSizePolicy, QGridLayout, QGroupBox,
    QFrame, QTabWidget, QStatusBar, QProgressBar, QToolButton,
    QTextEdit, QSpacerItem, QDialog, QDialogButtonBox, QFormLayout,
    QCheckBox, QMenu,QFileDialog, QToolBar, QApplication,
    QInputDialog, QTableWidget, QHeaderView, QDateEdit, QTableWidgetItem
)
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QTextDocument, QTextCursor, QDoubleValidator,QAction
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal, QTimer, QSettings, QSize, QDate
from ui.components.test_table import TestTable
from database import Session
from models import Order, Patient, Test, Result, Package, OrderComment, cipher
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import and_, func
import re
import csv
from datetime import datetime, timedelta
import logging
import os
from reports.invoice_generator import generate_invoice

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestSelectionDialog(QDialog):
    """Dialog for selecting multiple tests"""
    def __init__(self, parent=None, selected_test_ids=None):
        super().__init__(parent)
        self.selected_test_ids = selected_test_ids or []
        self.setWindowTitle("Select Tests")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QLineEdit, QComboBox, QListWidget {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QLineEdit:hover, QComboBox:hover, QListWidget:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus, QComboBox:focus, QListWidget:focus {
                border: 2px solid #4a90e2; outline: none;
            }
            QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5aa0; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2d3748;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #e2e8f0;
            }
        """)
        self.setup_ui()
        self.load_tests()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Tests:"))
        self.test_search = QLineEdit()
        self.test_search.setPlaceholderText("Search by test name or code...")
        self.test_search.textChanged.connect(self.filter_tests)
        search_layout.addWidget(self.test_search)
        search_layout.addWidget(QLabel("Department:"))
        self.department_filter = QComboBox()
        self.department_filter.addItem("All Departments", "")
        self.department_filter.currentIndexChanged.connect(self.filter_tests_by_department)
        search_layout.addWidget(self.department_filter)
        layout.addLayout(search_layout)
        self.test_list = QListWidget()
        self.test_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.test_list)
        test_actions = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_tests)
        test_actions.addWidget(self.select_all_btn)
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_test_selection)
        test_actions.addWidget(self.clear_selection_btn)
        layout.addLayout(test_actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_tests(self):
        self.test_list.clear()
        try:
            with Session() as session:
                tests = session.query(Test).all()
                departments = set(t.department for t in tests if t.department)
                self.department_filter.clear()
                self.department_filter.addItem("All Departments", "")
                for dept in sorted(departments):
                    self.department_filter.addItem(dept, dept)
                for t in tests:
                    item = QListWidgetItem(f"{t.code} - {t.name} ({t.department})")
                    item.setData(Qt.ItemDataRole.UserRole, t.id)
                    item.setData(Qt.ItemDataRole.UserRole + 1, t.department)
                    if t.id in self.selected_test_ids:
                        item.setSelected(True)
                    self.test_list.addItem(item)
        except Exception as e:
            logger.error(f"Error loading tests: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load tests: {str(e)}")

    def filter_tests(self):
        search_text = self.test_search.text().lower()
        department = self.department_filter.currentData()
        for i in range(self.test_list.count()):
            item = self.test_list.item(i)
            test_text = item.text().lower()
            matches_search = search_text in test_text or not search_text
            matches_department = not department or department == item.data(Qt.ItemDataRole.UserRole + 1)
            item.setHidden(not (matches_search and matches_department))

    def filter_tests_by_department(self):
        self.filter_tests()

    def select_all_tests(self):
        for i in range(self.test_list.count()):
            self.test_list.item(i).setSelected(True)

    def clear_test_selection(self):
        self.test_list.clearSelection()

    def get_selected_test_ids(self):
        return [self.test_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.test_list.count())
                if self.test_list.item(i).isSelected()]

class PaymentDialog(QDialog):
    """Dialog for handling payment details with percent and amount discounts"""
    def __init__(self, subtotal, parent=None):
        super().__init__(parent)
        self.subtotal = subtotal
        self.setWindowTitle("Payment Details")
        self.setModal(True)
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QLineEdit:hover, QComboBox:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #4a90e2; outline: none;
            }
            QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5aa0; }
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #e2e8f0;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f7fafc;
                border: 1px solid #e2e8f0;
                padding: 4px;
                font-weight: bold;
                color: #4a5568;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Subtotal: ₹{self.subtotal:.2f}"))

        # Discount section
        discount_group = QGroupBox("Discount")
        discount_layout = QFormLayout(discount_group)
        self.discount_type = QComboBox()
        self.discount_type.addItems(["Percent", "Amount"])
        self.discount_type.currentIndexChanged.connect(self.update_discount_display)
        discount_layout.addRow("Discount Type:", self.discount_type)
        self.discount_input = QLineEdit()
        self.discount_input.setValidator(QDoubleValidator(0.0, 100.0, 2) if self.discount_type.currentText() == "Percent" else QDoubleValidator(0.0, self.subtotal, 2))
        self.discount_input.textChanged.connect(self.update_discount_display)
        discount_layout.addRow("Discount Value:", self.discount_input)
        self.discount_amount_label = QLabel("Discount Amount: ₹0.00")
        discount_layout.addRow(self.discount_amount_label)
        self.total_label = QLabel(f"Total: ₹{self.subtotal:.2f}")
        discount_layout.addRow(self.total_label)
        layout.addWidget(discount_group)

        # Payment methods section
        payment_group = QGroupBox("Payment Methods")
        payment_layout = QVBoxLayout(payment_group)
        self.payment_table = QTableWidget()
        self.payment_table.setColumnCount(3)
        self.payment_table.setHorizontalHeaderLabels(["Method", "Amount", ""])
        self.payment_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.payment_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.payment_table.setColumnWidth(2, 50)
        self.payment_table.setRowCount(0)
        payment_layout.addWidget(self.payment_table)
        add_payment_layout = QHBoxLayout()
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["Cash", "E-Wallet", "Card", "UPI", "Bank Transfer"])
        add_payment_layout.addWidget(self.payment_method_combo)
        self.payment_amount = QLineEdit()
        self.payment_amount.setValidator(QDoubleValidator(0.0, self.subtotal, 2))
        add_payment_layout.addWidget(self.payment_amount)
        self.add_payment_btn = QPushButton("Add Payment")
        self.add_payment_btn.clicked.connect(self.add_payment)
        add_payment_layout.addWidget(self.add_payment_btn)
        payment_layout.addLayout(add_payment_layout)
        layout.addWidget(payment_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_discount_display()

    def update_discount_display(self):
        try:
            discount_value = float(self.discount_input.text() or 0)
            if self.discount_type.currentText() == "Percent":
                if discount_value > 100:
                    self.discount_input.setText("100")
                    discount_value = 100
                discount_amount = self.subtotal * (discount_value / 100)
            else:
                if discount_value > self.subtotal:
                    self.discount_input.setText(str(self.subtotal))
                    discount_amount = self.subtotal
                else:
                    discount_amount = discount_value
            self.discount_amount_label.setText(f"Discount Amount: ₹{discount_amount:.2f}")
            total = self.subtotal - discount_amount
            self.total_label.setText(f"Total: ₹{total:.2f}")
            self.payment_amount.setValidator(QDoubleValidator(0.0, total, 2))
        except ValueError:
            self.discount_amount_label.setText("Discount Amount: ₹0.00")
            self.total_label.setText(f"Total: ₹{self.subtotal:.2f}")
            self.payment_amount.setValidator(QDoubleValidator(0.0, self.subtotal, 2))

    def add_payment(self):
        try:
            amount = float(self.payment_amount.text())
            total_paid = sum(float(self.payment_table.item(i, 1).text()) for i in range(self.payment_table.rowCount()))
            total_due = self.subtotal - float(self.discount_amount_label.text().split('₹')[1])
            if total_paid + amount > total_due:
                QMessageBox.warning(self, "Error", f"Total payment ({total_paid + amount:.2f}) exceeds amount due (₹{total_due:.2f}).")
                return
            row = self.payment_table.rowCount()
            self.payment_table.insertRow(row)
            self.payment_table.setItem(row, 0, QTableWidgetItem(self.payment_method_combo.currentText()))
            self.payment_table.setItem(row, 1, QTableWidgetItem(f"{amount:.2f}"))
            remove_btn = QPushButton("X")
            remove_btn.setStyleSheet("background-color: #e53e3e; color: white; border-radius: 5px;")
            remove_btn.clicked.connect(lambda: self.remove_payment(row))
            self.payment_table.setCellWidget(row, 2, remove_btn)
            self.payment_amount.clear()
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid payment amount.")

    def remove_payment(self, row):
        self.payment_table.removeRow(row)

    def validate_and_accept(self):
        total_paid = sum(float(self.payment_table.item(i, 1).text()) for i in range(self.payment_table.rowCount()))
        total_due = self.subtotal - float(self.discount_amount_label.text().split('₹')[1])
        if total_paid != total_due:
            QMessageBox.warning(self, "Error", f"Total payment (₹{total_paid:.2f}) does not match amount due (₹{total_due:.2f}).")
            return
        self.accept()

    def get_data(self):
        discount_value = float(self.discount_input.text() or 0)
        if self.discount_type.currentText() == "Percent":
            discount_perc = discount_value
        else:
            discount_perc = (discount_value / self.subtotal) * 100 if self.subtotal > 0 else 0
        payments = []
        for i in range(self.payment_table.rowCount()):
            method = self.payment_table.item(i, 0).text()
            amount = self.payment_table.item(i, 1).text()
            payments.append(f"{method}:{amount}")
        payments_str = ";".join(payments)
        return discount_perc, payments_str

class CommentDialog(QDialog):
    """Dialog for adding order comments"""
    def __init__(self, order_id, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.setWindowTitle(f"Comments for Order #{order_id}")
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #FAF9F6;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QTextEdit {
                background-color: #FAF9F6; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QTextEdit:focus {
                border: 2px solid #4a90e2; outline: none;
            }
            QDialogButtonBox QPushButton {
                background-color: #4a90e2; color: #FAF9F6; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                
            }
            QDialogButtonBox QPushButton:pressed { background-color: #2c5aa0; }
            QComboBox QAbstractItemView {
                background-color: #FAF9F6;
                color: #2d3748;
                selection-background-color: #4a90e2;
                selection-color: #FAF9F6;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: #FAF9F6;
            }
        """)
        self.setup_ui()
        self.load_comments()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.comments_display = QTextEdit()
        self.comments_display.setReadOnly(True)
        layout.addWidget(QLabel("Existing Comments:"))
        layout.addWidget(self.comments_display)
        layout.addWidget(QLabel("Add New Comment:"))
        self.new_comment = QTextEdit()
        self.new_comment.setMaximumHeight(100)
        layout.addWidget(self.new_comment)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_comment)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def load_comments(self):
        try:
            with Session() as session:
                comments = session.query(OrderComment).filter_by(order_id=self.order_id)\
                             .order_by(OrderComment.timestamp.desc()).all()
                html = ""
                for comment in comments:
                    html += f"<p><b>{comment.timestamp.strftime('%Y-%m-%d %H:%M')}:</b> {comment.comment}</p>"
                self.comments_display.setHtml(html or "No comments yet.")
        except Exception as e:
            logger.error(f"Error loading comments: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load comments: {str(e)}")
    
    def save_comment(self):
        comment_text = self.new_comment.toPlainText().strip()
        if not comment_text:
            QMessageBox.warning(self, "Warning", "Comment cannot be empty.")
            return
        try:
            with Session() as session:
                new_comment = OrderComment(
                    order_id=self.order_id,
                    comment=comment_text,
                    timestamp=datetime.now()
                )
                session.add(new_comment)
                session.commit()
            self.load_comments()
            self.new_comment.clear()
            QMessageBox.information(self, "Success", "Comment added successfully.")
            logger.info(f"Added comment to order #{self.order_id}")
        except Exception as e:
            logger.error(f"Error saving comment: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save comment: {str(e)}")

class OrderSearchDialog(QDialog):
    """Dialog for searching and viewing orders"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Orders")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QLineEdit, QDateTimeEdit, QComboBox {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QLineEdit:hover, QDateTimeEdit:hover, QComboBox:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus, QDateTimeEdit:focus, QComboBox:focus {
                border: 2px solid #4a90e2; outline: none;
            }
            QDialogButtonBox QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                
            }
            QDialogButtonBox QPushButton:pressed { background-color: #2c5aa0; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2d3748;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #e2e8f0;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f7fafc;
                border: 1px solid #e2e8f0;
                padding: 4px;
                font-weight: bold;
                color: #4a5568;
            }
        """)
        self.setup_ui()
        self.load_orders_dialog()
        # Connect to parent's order_placed signal if available
        if hasattr(parent, 'order_placed'):
            parent.order_placed.connect(self.load_orders_dialog)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Patient name, phone, PID, or ID...")
        self.search_edit.setToolTip("Search orders by patient name, contact, PID, or order ID")
        self.search_edit.setAccessibleDescription("Search field for filtering orders")
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_orders_dialog)
        self.search_edit.textChanged.connect(self.start_search_timer)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(QLabel("From:"))
        # Set default date range to include today
        self.date_from = QDateTimeEdit(QDateTime.currentDateTime().addDays(-30))  # Extended to 30 days
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setCalendarPopup(True)
        self.date_from.setToolTip("Select start date for order search")
        self.date_from.dateTimeChanged.connect(self.load_orders_dialog)
        self.date_from.setMaximumWidth(120)
        search_layout.addWidget(self.date_from)
        search_layout.addWidget(QLabel("To:"))
        self.date_to = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))  # Include tomorrow
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setCalendarPopup(True)
        self.date_to.setToolTip("Select end date for order search")
        self.date_to.dateTimeChanged.connect(self.load_orders_dialog)
        self.date_to.setMaximumWidth(120)
        search_layout.addWidget(self.date_to)
        search_layout.addStretch()
        layout.addLayout(search_layout)
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All", "")
        self.status_combo.addItems(["Pending", "In Progress", "Completed", "Cancelled"])
        self.status_combo.setToolTip("Filter orders by status")
        self.status_combo.setAccessibleDescription("Dropdown to filter orders by status")
        self.status_combo.currentIndexChanged.connect(self.load_orders_dialog)
        status_layout.addWidget(self.status_combo)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        self.orders_table = TestTable([], ["ID", "PID", "Patient", "Test", "Referring Physician", "Date", "Status"], parent=self)
        self.orders_table.table.setSortingEnabled(True)
        self.orders_table.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.orders_table.table.setToolTip("Table of orders, right-click for options")
        self.orders_table.table.setAccessibleDescription("Table displaying search results for orders")
        self.orders_table.table.customContextMenuRequested.connect(self.show_orders_context_menu)
        layout.addWidget(self.orders_table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.export_btn = buttons.addButton("Export", QDialogButtonBox.ButtonRole.ActionRole)
        self.export_btn.clicked.connect(self.export_orders)
        self.export_btn.setToolTip("Export order table to CSV")
        # Add delete, cancel, and reprint buttons
        button_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected Order")
        self.delete_btn.clicked.connect(self.delete_order)
        button_layout.addWidget(self.delete_btn)
        self.cancel_btn = QPushButton("Cancel Selected Order")
        self.cancel_btn.clicked.connect(self.cancel_order)
        button_layout.addWidget(self.cancel_btn)
        self.reprint_btn = QPushButton("Reprint Invoice")
        self.reprint_btn.clicked.connect(self.reprint_invoice)
        button_layout.addWidget(self.reprint_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def start_search_timer(self):
        self.search_timer.start(300)

    def load_orders_dialog(self):
        status_filter = self.status_combo.currentData()
        date_from = self.date_from.dateTime().toPyDateTime()
        date_to = self.date_to.dateTime().toPyDateTime()
        search_text = self.search_edit.text().lower()
        try:
            with Session() as session:
                query = session.query(Order).options(
                    joinedload(Order.patient), joinedload(Order.test)
                ).filter(
                    Order.order_date >= date_from,
                    Order.order_date <= date_to
                )
                if status_filter:
                    query = query.filter(Order.status == status_filter)
                orders = query.order_by(Order.order_date.desc()).all()
                logger.info(f"Queried {len(orders)} orders from {date_from} to {date_to}")
                filtered_orders = []
                for o in orders:
                    if search_text:
                        patient_name = getattr(o.patient, 'decrypted_name', '').lower() if o.patient else ""
                        patient_contact = getattr(o.patient, 'decrypted_contact', '').lower() if o.patient and o.patient.contact else ""
                        patient_pid = o.patient.pid.lower() if o.patient and o.patient.pid else ""
                        order_id_str = str(o.id).lower()
                        if not (search_text in patient_name or search_text in patient_contact or search_text in patient_pid or search_text in order_id_str):
                            continue
                    filtered_orders.append(o)
                logger.info(f"Filtered to {len(filtered_orders)} orders after applying search text: '{search_text}'")
                rows = []
                for o in filtered_orders:
                    try:
                        patient_name = o.patient.decrypted_name
                        patient_pid = o.patient.pid if o.patient.pid else "N/A"
                    except Exception as e:
                        logger.warning(f"Decryption failed for patient in order {o.id}: {str(e)}")
                        patient_name = "Decryption failed"
                        patient_pid = "N/A"
                    test_desc = f"{o.test.code} - {o.test.name}" if o.test else "Unknown"
                    rows.append((
                        o.id,
                        patient_pid,
                        patient_name,
                        test_desc,
                        o.referring_physician or "N/A",
                        o.order_date.strftime("%Y-%m-%d %H:%M") if o.order_date else "",
                        o.status
                    ))
                self.orders_table.update_data(rows)
                logger.info(f"Updated table with {len(rows)} rows")
                for row in range(self.orders_table.table.rowCount()):
                    status_item = self.orders_table.table.item(row, 6)
                    if status_item:
                        status = status_item.text()
                        if status == "Pending":
                            status_item.setBackground(QColor(254, 243, 199))
                            status_item.setForeground(QColor(146, 64, 14))
                        elif status == "In Progress":
                            status_item.setBackground(QColor(219, 234, 254))
                            status_item.setForeground(QColor(30, 64, 175))
                        elif status == "Completed":
                            status_item.setBackground(QColor(209, 250, 229))
                            status_item.setForeground(QColor(6, 95, 70))
                        elif status == "Cancelled":
                            status_item.setBackground(QColor(254, 202, 202))
                            status_item.setForeground(QColor(153, 27, 27))
        except Exception as e:
            logger.error(f"Error loading orders in dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load orders: {str(e)}")

    def show_orders_context_menu(self, position):
        menu = QMenu()
        view_comments = menu.addAction("View/Add Comments")
        view_comments.triggered.connect(self.view_order_comments)
        view_history = menu.addAction("View Patient History")
        view_history.triggered.connect(self.view_patient_history)
        delete_order = menu.addAction("Delete Order")
        delete_order.triggered.connect(self.delete_order)
        cancel_order = menu.addAction("Cancel Order")
        cancel_order.triggered.connect(self.cancel_order)
        menu.exec(self.orders_table.table.viewport().mapToGlobal(position))

    def cancel_order(self):
        row = self.orders_table.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an order to cancel.")
            return
        order_id = int(self.orders_table.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Confirm Cancel", "Are you sure you want to cancel this order?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with Session() as session:
                    order = session.get(Order, order_id)
                    if order:
                        order.status = "Cancelled"
                        session.commit()
                        QMessageBox.information(self, "Success", "Order cancelled successfully.")
                        logger.info(f"Cancelled order #{order_id}")
                        self.load_orders_dialog()
                    else:
                        QMessageBox.warning(self, "Warning", "Order not found.")
            except Exception as e:
                logger.error(f"Error cancelling order: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to cancel order: {str(e)}")

    def delete_order(self):
        row = self.orders_table.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an order to delete.")
            return
        order_id = int(self.orders_table.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this order?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with Session() as session:
                    order = session.get(Order, order_id)
                    if order:
                        session.delete(order)
                        session.commit()
                        QMessageBox.information(self, "Success", "Order deleted successfully.")
                        logger.info(f"Deleted order #{order_id}")
                        self.load_orders_dialog()
                    else:
                        QMessageBox.warning(self, "Warning", "Order not found.")
            except Exception as e:
                logger.error(f"Error deleting order: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to delete order: {str(e)}")

    def view_order_comments(self):
        row = self.orders_table.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an order to view comments.")
            return
        order_id = int(self.orders_table.table.item(row, 0).text())
        dialog = CommentDialog(order_id, self)
        dialog.exec()

    def view_patient_history(self):
        row = self.orders_table.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an order to view patient history.")
            return
        order_id = int(self.orders_table.table.item(row, 0).text())
        try:
            with Session() as session:
                order = session.get(Order, order_id)
                if order:
                    patient_id = order.patient_id
                    patient_orders = session.query(Order).filter_by(patient_id=patient_id)\
                                         .order_by(Order.order_date.desc()).all()
                    history_text = f"<h3>Order History for Patient</h3>"
                    history_text += f"<p><b>Patient:</b> {order.patient.decrypted_name if order.patient else 'N/A'}</p>"
                    history_text += f"<p><b>PID:</b> {order.patient.pid if order.patient and order.patient.pid else 'N/A'}</p>"
                    history_text += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
                    history_text += "<tr><th>Order ID</th><th>Test</th><th>Date</th><th>Status</th></tr>"
                    for o in patient_orders:
                        test_desc = f"{o.test.code} - {o.test.name}" if o.test else "Unknown"
                        history_text += f"<tr><td>{o.id}</td><td>{test_desc}</td><td>{o.order_date.strftime('%Y-%m-%d') if o.order_date else ''}</td><td>{o.status}</td></tr>"
                    history_text += "</table>"
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Patient Order History")
                    dialog.setMinimumSize(600, 400)
                    dialog.setStyleSheet("""
                        QDialog {
                            background-color: #f5f5f5;
                            border-radius: 12px;
                        }
                        QTextEdit {
                            background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                            padding: 6px 10px; font-size: 13px; color: #2d3748;
                        }
                        QDialogButtonBox QPushButton {
                            background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                            padding: 8px 16px; font-size: 13px; font-weight: 500;
                        }
                        QDialogButtonBox QPushButton:hover { background-color: #357abd; }
                        QComboBox QAbstractItemView {
                            background-color: #ffffff;
                            color: #2d3748;
                            selection-background-color: #4a90e2;
                            selection-color: #ffffff;
                            border: 1px solid #e2e8f0;
                            border-radius: 4px;
                        }
                        QListWidget::item:selected {
                            background-color: #4a90e2;
                            color: #ffffff;
                        }
                        QListWidget::item:hover {
                            background-color: #e2e8f0;
                        }
                    """)
                    layout = QVBoxLayout(dialog)
                    text_edit = QTextEdit()
                    text_edit.setHtml(history_text)
                    text_edit.setReadOnly(True)
                    layout.addWidget(text_edit)
                    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
                    buttons.accepted.connect(dialog.accept)
                    layout.addWidget(buttons)
                    dialog.exec()
        except Exception as e:
            logger.error(f"Error loading patient history: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load patient history: {str(e)}")

    def export_orders(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Orders", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['ID', 'PID', 'Patient', 'Test', 'Referring Physician', 'Date', 'Status'])
                for row in range(self.orders_table.table.rowCount()):
                    row_data = []
                    for col in range(self.orders_table.table.columnCount()):
                        item = self.orders_table.table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            QMessageBox.information(self, "Success", "Orders exported successfully.")
            logger.info(f"Exported orders to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting orders: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export orders: {str(e)}")

    def reprint_invoice(self):
        row = self.orders_table.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Select an order to reprint invoice.")
            return
        order_id = int(self.orders_table.table.item(row, 0).text())
        try:
            with Session() as session:
                order = session.get(Order, order_id)
                if order:
                    group_id = order.group_id
                    group_orders = session.query(Order).filter_by(group_id=group_id).all()
                    group_order_ids = [o.id for o in group_orders]
                    pdf_path = generate_invoice(group_order_ids)
                    os.startfile(pdf_path)
                    QMessageBox.information(self, "Success", "Invoice reprinted successfully.")
                else:
                    QMessageBox.warning(self, "Warning", "Order not found.")
        except Exception as e:
            logger.error(f"Error reprinting invoice: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to reprint invoice: {str(e)}")

class PatientSearchDialog(QDialog):
    """Dialog for searching and selecting patients"""
    patient_selected = pyqtSignal(int)  # Signal to emit selected patient_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Patients")
        self.setModal(True)
        self.setMinimumSize(600, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QLineEdit, QDateEdit, QComboBox {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QLineEdit:hover, QDateEdit:hover, QComboBox:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 2px solid #4a90e2; outline: none;
            }
            QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
               
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5aa0; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2d3748;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #e2e8f0;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
            QTableWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #e2e8f0;
            }
            QHeaderView::section {
                background-color: #f7fafc;
                border: 1px solid #e2e8f0;
                padding: 4px;
                font-weight: bold;
                color: #4a5568;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search By:"))
        self.search_by_combo = QComboBox()
        self.search_by_combo.addItems(["Name", "PID", "Contact"])
        search_layout.addWidget(self.search_by_combo)
        self.search_term = QLineEdit()
        self.search_term.setPlaceholderText("Enter search term...")
        search_layout.addWidget(self.search_term)
        search_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        search_layout.addWidget(self.date_from)
        search_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        search_layout.addWidget(self.date_to)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.load_patients_dialog)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        self.patients_table = QTableWidget()
        self.patients_table.setColumnCount(5)
        self.patients_table.setHorizontalHeaderLabels(["ID", "PID", "Name", "Contact", "Created At"])
        self.patients_table.setAlternatingRowColors(True)
        self.patients_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Fixed line
        self.patients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.patients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.patients_table.hideColumn(0)  # Hide ID column
        self.patients_table.setSortingEnabled(True)
        self.patients_table.doubleClicked.connect(self.select_patient)
        layout.addWidget(self.patients_table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_patients_dialog(self):
        search_by = self.search_by_combo.currentText()
        search_term = self.search_term.text().strip().lower()
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        try:
            with Session() as session:
                query = session.query(Patient)
                if date_from and date_to:
                    query = query.filter(and_(Patient.created_at >= date_from, Patient.created_at <= date_to))
                patients = query.all()
                filtered_patients = []
                for patient in patients:
                    if search_term:
                        if search_by == "Name":
                            if search_term not in patient.decrypted_name.lower():
                                continue
                        elif search_by == "PID":
                            if patient.pid is None or search_term not in patient.pid.lower():
                                continue
                        elif search_by == "Contact":
                            if search_term not in patient.decrypted_contact.lower():
                                continue
                    filtered_patients.append(patient)
                self.patients_table.setRowCount(len(filtered_patients))
                for row, patient in enumerate(filtered_patients):
                    self.patients_table.setItem(row, 0, QTableWidgetItem(str(patient.id)))
                    self.patients_table.setItem(row, 1, QTableWidgetItem(patient.pid or "N/A"))
                    self.patients_table.setItem(row, 2, QTableWidgetItem(patient.decrypted_name))
                    self.patients_table.setItem(row, 3, QTableWidgetItem(patient.decrypted_contact))
                    self.patients_table.setItem(row, 4, QTableWidgetItem(patient.created_at.strftime("%Y-%m-%d") if patient.created_at else "N/A"))
        except Exception as e:
            logger.error(f"Error loading patients in dialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load patients: {str(e)}")

    def select_patient(self):
        selected_rows = self.patients_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            patient_id = int(self.patients_table.item(row, 0).text())
            self.patient_selected.emit(patient_id)
            self.accept()

class PackageDialog(QDialog):
    """Dialog for creating and editing packages"""
    def __init__(self, parent=None, package_id=None):
        super().__init__(parent)
        self.package_id = package_id
        self.setWindowTitle("Edit Package" if package_id else "Create New Package")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QLineEdit, QListWidget {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QLineEdit:hover, QListWidget:hover {
                border-color: #4a90e2;
            }
            QLineEdit:focus, QListWidget:focus {
                border: 2px solid #4a90e2; outline: none;
            }
            QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
             
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5aa0; }
            QDialogButtonBox QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
            }
            QDialogButtonBox QPushButton:hover { background-color: #357abd; }
            QDialogButtonBox QPushButton:pressed { background-color: #2c5aa0; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2d3748;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4a90e2;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #e2e8f0;
            }
        """)
        self.setup_ui()
        self.load_tests()
        if package_id:
            self.load_package_data(package_id)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Package Name:"))
        self.package_name = QLineEdit()
        self.package_name.setPlaceholderText("Enter package name")
        self.package_name.setToolTip("Enter a unique name for the package")
        self.package_name.setAccessibleDescription("Text field for package name")
        layout.addWidget(self.package_name)
        layout.addWidget(QLabel("Select Tests:"))
        self.test_list = QListWidget()
        self.test_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.test_list.setToolTip("Select one or more tests to include in the package")
        self.test_list.setAccessibleDescription("List of tests for package creation")
        layout.addWidget(self.test_list)
        test_actions = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_tests)
        test_actions.addWidget(self.select_all_btn)
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_test_selection)
        test_actions.addWidget(self.clear_selection_btn)
        layout.addLayout(test_actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_package)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_tests(self):
        self.test_list.clear()
        try:
            with Session() as session:
                tests = session.query(Test).all()
                for t in tests:
                    item = QListWidgetItem(f"{t.code} - {t.name} ({t.department})")
                    item.setData(Qt.ItemDataRole.UserRole, t.id)
                    self.test_list.addItem(item)
        except Exception as e:
            logger.error(f"Error loading tests in PackageDialog: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load tests: {str(e)}")

    def load_package_data(self, package_id):
        try:
            with Session() as session:
                package = session.get(Package, package_id)
                if package:
                    self.package_name.setText(package.name)
                    test_ids = package.test_ids.split(',') if package.test_ids else []
                    for i in range(self.test_list.count()):
                        item = self.test_list.item(i)
                        if str(item.data(Qt.ItemDataRole.UserRole)) in test_ids:
                            item.setSelected(True)
        except Exception as e:
            logger.error(f"Error loading package data: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load package: {str(e)}")

    def select_all_tests(self):
        for i in range(self.test_list.count()):
            self.test_list.item(i).setSelected(True)

    def clear_test_selection(self):
        self.test_list.clearSelection()

    def save_package(self):
        package_name = self.package_name.text().strip()
        if not package_name:
            QMessageBox.warning(self, "Error", "Package name cannot be empty.")
            return
        selected_tests = [self.test_list.item(i).data(Qt.ItemDataRole.UserRole)
                         for i in range(self.test_list.count())
                         if self.test_list.item(i).isSelected()]
        if not selected_tests:
            QMessageBox.warning(self, "Error", "At least one test must be selected.")
            return
        try:
            with Session() as session:
                if self.package_id:
                    package = session.get(Package, self.package_id)
                    if not package:
                        QMessageBox.warning(self, "Error", "Package not found.")
                        return
                    package.name = package_name
                    package.test_ids = ','.join(str(tid) for tid in selected_tests)
                    log_message = f"Updated package ID: {self.package_id}"
                else:
                    package = Package(
                        name=package_name,
                        test_ids=','.join(str(tid) for tid in selected_tests)
                    )
                    session.add(package)
                    log_message = f"Created new package: {package_name}"
                session.commit()
                self.new_package_id = package.id
                QMessageBox.information(self, "Success", f"Package '{package_name}' {'updated' if self.package_id else 'created'} successfully.")
                logger.info(log_message)
                self.accept()
        except Exception as e:
            logger.error(f"Error saving package: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save package: {str(e)}")

class OrderTab(QWidget):
    """Tab for managing patient orders with multi-test selection and a modern light theme."""
    order_placed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("orderTab")
        self.setStyleSheet(self._load_stylesheet())
        self.is_orders_expanded = True
        self.expanded_sizes = [400, 300]
        self.selected_test_ids = []
        self._init_ui()
        self.load_combos()
        self.load_packages()

    def _load_stylesheet(self) -> str:
        return """
            QWidget#orderTab {
                background-color: #FAF9F6;
                border-radius: 12px;
                padding: 10px;
                font-family: "Calibri", "Arial", sans-serif;
            }
            .tab-heading {
                font-size: 20px; font-weight: 600; color: #1a202c; margin-bottom: 15px;
                background: linear-gradient(90deg, #FAF9F6, #F5F5F5); padding: 8px;
                border-radius: 8px; text-align: center;
            }
            QLabel {
                color: #1a202c; font-family: 'Calibri', Arial, sans-serif; font-size: 12px; margin-top: 5px; padding: 3px;
            }
            QComboBox, QDateTimeEdit, QLineEdit, QTextEdit {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2d3748;
                selection-background-color: #4a90e2;
                selection-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
            }
            QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                min-width: 100px;
            }
            QPushButton:disabled { 
                background-color: #e2e8f0; color: #a0aec0; 
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:pressed { background-color: #2c5aa0; }
        """

    def _init_ui(self):
        self.setFont(QFont("Segoe UI", 11))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        main_layout = QVBoxLayout(scroll_content)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        heading = QLabel("Order Management")
        heading.setProperty("class", "tab-heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(heading)
        top_widget = QWidget()
        top_layout = QGridLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)
        left_panel = QGroupBox("Patient Information")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        patient_toolbar = QHBoxLayout()
        patient_toolbar.addWidget(QLabel("Search:"))
        self.patient_search = QLineEdit()
        self.patient_search.setPlaceholderText("Type to search patients...")
        self.patient_search.setToolTip("Search for patients by name or PID")
        self.patient_search.setAccessibleDescription("Search field for filtering patients")
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.filter_patients)
        self.patient_search.textChanged.connect(self.start_search_timer)
        patient_toolbar.addWidget(self.patient_search)
        self.patient_search_btn = QPushButton("Advanced Search")
        self.patient_search_btn.clicked.connect(self.open_patient_search_dialog)
        self.patient_search_btn.setToolTip("Open advanced patient search dialog")
        patient_toolbar.addWidget(self.patient_search_btn)
        patient_toolbar.addStretch()
        left_layout.addLayout(patient_toolbar)
        left_layout.addWidget(QLabel("Select Patient:"))
        self.patient_combo = QComboBox()
        self.patient_combo.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.patient_combo.setAccessibleName("Patient selection combo box")
        self.patient_combo.setToolTip("Select a patient from the list or use search to filter")
        self.patient_combo.setAccessibleDescription("Dropdown menu to select a patient for the order")
        left_layout.addWidget(self.patient_combo)
        
        package_group = QGroupBox("Package Management")
        package_layout = QVBoxLayout(package_group)
        package_layout.setSpacing(6)
        package_layout.addWidget(QLabel("Order Packages:"))
        self.package_combo = QComboBox()
        self.package_combo.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.package_combo.setToolTip("Select a predefined package to auto-select tests")
        self.package_combo.setAccessibleDescription("Dropdown to select a package of tests")
        self.package_combo.currentIndexChanged.connect(self.apply_package)
        self.package_combo.setMouseTracking(True)
        self.package_combo.enterEvent = self.show_package_preview
        package_layout.addWidget(self.package_combo)
        package_buttons = QHBoxLayout()
        self.create_package_btn = QPushButton("Create New Package")
        self.create_package_btn.clicked.connect(self.create_new_package)
        self.create_package_btn.setToolTip("Create a new package with selected tests")
        package_buttons.addWidget(self.create_package_btn)
        self.edit_package_btn = QPushButton("Edit Package")
        self.edit_package_btn.clicked.connect(self.edit_package)
        self.edit_package_btn.setToolTip("Edit the selected package")
        package_buttons.addWidget(self.edit_package_btn)
        self.delete_package_btn = QPushButton("Delete Package")
        self.delete_package_btn.clicked.connect(self.delete_package)
        self.delete_package_btn.setStyleSheet("background-color: #e53e3e; color: white; border-radius: 10px;")
        self.delete_package_btn.setToolTip("Delete the selected package")
        package_buttons.addWidget(self.delete_package_btn)
        self.export_packages_btn = QPushButton("Export Packages")
        self.export_packages_btn.clicked.connect(self.export_packages)
        self.export_packages_btn.setToolTip("Export all packages to a CSV file")
        package_buttons.addWidget(self.export_packages_btn)
        package_buttons.addStretch()
        package_layout.addLayout(package_buttons)
        left_layout.addWidget(package_group)
        left_layout.addWidget(QLabel("Referring Physician:"))
        self.referring_physician = QLineEdit()
        self.referring_physician.setPlaceholderText("Enter referring physician name")
        self.referring_physician.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.referring_physician.setToolTip("Enter the name of the referring physician")
        self.referring_physician.setAccessibleDescription("Text field for referring physician name")
        left_layout.addWidget(self.referring_physician)
        left_layout.addWidget(QLabel("Order Date & Time:"))
        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.date_edit.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.date_edit.setToolTip("Set the date and time for the order")
        self.date_edit.setAccessibleDescription("Date and time picker for order scheduling")
        left_layout.addWidget(self.date_edit)
        left_layout.addStretch()
        right_panel = QGroupBox("Test Selection")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)
        self.select_tests_btn = QPushButton("Select Tests")
        self.select_tests_btn.clicked.connect(self.open_test_selection_dialog)
        right_layout.addWidget(self.select_tests_btn)
        self.selected_tests_label = QTextEdit()
        self.selected_tests_label.setReadOnly(True)
        self.selected_tests_label.setMinimumHeight(200)
        right_layout.addWidget(self.selected_tests_label)
        right_layout.addStretch()
        top_layout.addWidget(left_panel, 0, 0)
        top_layout.addWidget(right_panel, 0, 1)
        top_layout.setColumnStretch(0, 1)
        top_layout.setColumnStretch(1, 2)
        main_layout.addWidget(top_widget)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.order_btn = QPushButton("Place Order")
        self.order_btn.clicked.connect(self.place_order)
        self.order_btn.setShortcut("Ctrl+Enter")
        self.order_btn.setToolTip("Place a new order for the selected patient and tests")
        self.order_btn.setStyleSheet("background-color: #48bb78; min-width: 120px; border-radius: 10px;")
        button_layout.addWidget(self.order_btn)
        self.batch_order_btn = QPushButton("Batch Order")
        self.batch_order_btn.clicked.connect(self.open_batch_order_dialog)
        self.batch_order_btn.setToolTip("Place orders for multiple patients using a package")
        self.batch_order_btn.setStyleSheet("background-color: #805ad5; min-width: 120px; border-radius: 10px;")
        button_layout.addWidget(self.batch_order_btn)
        self.clear_btn = QPushButton("Clear Form")
        self.clear_btn.clicked.connect(self.clear_form)
        self.clear_btn.setShortcut("Ctrl+Shift+C")
        self.clear_btn.setToolTip("Reset all fields to default")
        self.clear_btn.setStyleSheet("background-color: #ed8936; min-width: 120px; border-radius: 10px;")
        button_layout.addWidget(self.clear_btn)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(QIcon("icons/refresh_icon.png"))
        self.refresh_btn.clicked.connect(self._on_refresh)
        self.refresh_btn.setToolTip("Refresh patient, test, and package data")
        button_layout.addWidget(self.refresh_btn)
        self.search_orders_btn = QPushButton("Search Orders")
        self.search_orders_btn.clicked.connect(self.open_search_dialog)
        self.search_orders_btn.setStyleSheet("background-color: #4299e1; min-width: 120px; border-radius: 10px;")
        self.search_orders_btn.setToolTip("Search and view existing orders")
        button_layout.addWidget(self.search_orders_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready to place orders")
        main_layout.addWidget(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setTabOrder(self.patient_search, self.patient_combo)
        self.setTabOrder(self.patient_combo, self.package_combo)
        self.setTabOrder(self.package_combo, self.create_package_btn)
        self.setTabOrder(self.create_package_btn, self.edit_package_btn)
        self.setTabOrder(self.edit_package_btn, self.delete_package_btn)
        self.setTabOrder(self.delete_package_btn, self.export_packages_btn)
        self.setTabOrder(self.export_packages_btn, self.referring_physician)
        self.setTabOrder(self.referring_physician, self.date_edit)
        self.setTabOrder(self.date_edit, self.select_tests_btn)
        self.setTabOrder(self.select_tests_btn, self.order_btn)
        self.setTabOrder(self.batch_order_btn, self.clear_btn)
        self.setTabOrder(self.clear_btn, self.refresh_btn)
        self.setTabOrder(self.refresh_btn, self.search_orders_btn)

    def start_search_timer(self):
        self.search_timer.start(300)

    def open_search_dialog(self):
        dialog = OrderSearchDialog(self)
        dialog.exec()

    def open_batch_order_dialog(self):
        dialog = BatchOrderDialog(self)
        dialog.exec()
        self.order_placed.emit()

    def open_patient_search_dialog(self):
        dialog = PatientSearchDialog(self)
        dialog.patient_selected.connect(self.select_patient_from_search)
        dialog.exec()

    def open_test_selection_dialog(self):
        dialog = TestSelectionDialog(self, self.selected_test_ids)
        if dialog.exec():
            self.selected_test_ids = dialog.get_selected_test_ids()
            self.update_selected_tests_summary()

    def select_patient_from_search(self, patient_id):
        index = self.patient_combo.findData(patient_id)
        if index >= 0:
            self.patient_combo.setCurrentIndex(index)

    def create_new_package(self):
        dialog = PackageDialog(self)
        if dialog.exec():
            self.load_packages()
            new_package_id = getattr(dialog, 'new_package_id', None)
            if new_package_id:
                index = self.package_combo.findData(new_package_id)
                if index >= 0:
                    self.package_combo.setCurrentIndex(index)

    def edit_package(self):
        package_id = self.package_combo.currentData()
        if not package_id:
            QMessageBox.warning(self, "Warning", "Please select a package to edit.")
            return
        dialog = PackageDialog(self, package_id=package_id)
        if dialog.exec():
            self.load_packages()

    def delete_package(self):
        package_id = self.package_combo.currentData()
        if not package_id:
            QMessageBox.warning(self, "Warning", "Please select a package to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete the package?\nThis action cannot be undone.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with Session() as session:
                    package = session.get(Package, package_id)
                    if package:
                        session.delete(package)
                        session.commit()
                        self.load_packages()
                        self.status_bar.showMessage("Package deleted successfully")
                        logger.info(f"Deleted package ID: {package_id}")
                    else:
                        QMessageBox.warning(self, "Warning", "Package not found.")
            except Exception as e:
                logger.error(f"Error deleting package: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to delete package: {str(e)}")

    def export_packages(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Packages", "", "CSV Files (*.csv)")
        if not file_path:
            return
        try:
            with Session() as session:
                packages = session.query(Package).all()
                test_map = {t.id: f"{t.code} - {t.name}" for t in session.query(Test).all()}
                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Package Name', 'Test IDs', 'Test Names'])
                    for package in packages:
                        test_ids = package.test_ids or ''
                        test_names = []
                        for tid_str in test_ids.split(','):
                            tid = int(tid_str.strip())
                            if tid in test_map:
                                test_names.append(test_map[tid])
                        writer.writerow([package.name, test_ids, ', '.join(test_names)])
                QMessageBox.information(self, "Success", "Packages exported successfully.")
                logger.info(f"Exported packages to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting packages: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to export packages: {str(e)}")

    def show_package_preview(self, event):
        package_id = self.package_combo.currentData()
        if not package_id:
            return
        try:
            with Session() as session:
                package = session.get(Package, package_id)
                if package:
                    test_ids = package.test_ids.split(',') if package.test_ids else []
                    tests = session.query(Test).filter(Test.id.in_(test_ids)).all()
                    test_list = "\n".join([f"{t.code} - {t.name}" for t in tests])
                    QToolTip.showText(self.package_combo.mapToGlobal(self.package_combo.pos()),
                                    f"Package: {package.name}\nTests:\n{test_list or 'No tests'}")
        except Exception as e:
            logger.error(f"Error showing package preview: {str(e)}")

    def load_packages(self):
        self.package_combo.clear()
        self.package_combo.addItem("-- Select Package --", None)
        try:
            with Session() as session:
                packages = session.query(Package).all()
                test_map = {t.id: f"{t.code} - {t.name}" for t in session.query(Test).all()}
                for package in packages:
                    test_ids = package.test_ids.split(',') if package.test_ids else []
                    test_names = []
                    for tid_str in test_ids:
                        tid = int(tid_str.strip())
                        if tid in test_map:
                            test_names.append(test_map[tid])
                    includes = ', '.join(test_names[:3])
                    if len(test_names) > 3:
                        includes += f" +{len(test_names)-3} more"
                    elif not test_names:
                        includes = "No tests"
                    display_text = f"{package.name} ({includes})"
                    self.package_combo.addItem(display_text, package.id)
        except Exception as e:
            logger.error(f"Error loading packages: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load packages: {str(e)}")

    def apply_package(self):
        package_id = self.package_combo.currentData()
        if not package_id:
            return
        try:
            with Session() as session:
                package = session.get(Package, package_id)
                if package:
                    self.selected_test_ids = [int(tid.strip()) for tid in package.test_ids.split(',') if tid.strip()]
                    self.update_selected_tests_summary()
                    self.status_bar.showMessage(f"Applied package: {package.name}")
                    logger.info(f"Applied package: {package.name}")
        except Exception as e:
            logger.error(f"Error applying package: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to apply package: {str(e)}")

    def filter_patients(self):
        search_text = self.patient_search.text().lower()
        try:
            with Session() as session:
                query = session.query(Patient)
                if search_text:
                    # Search in name, contact, or pid
                    query = query.filter(
                        Patient.name.contains(cipher.encrypt(search_text.encode()).decode()) |
                        Patient.contact.contains(cipher.encrypt(search_text.encode()).decode()) |
                        Patient.pid.ilike(f"%{search_text}%")
                    )
                patients = query.limit(100).all()
                self.patient_combo.clear()
                self.patient_combo.addItem("-- Select Patient --", None)
                for p in patients:
                    try:
                        name = p.decrypted_name
                        pid = p.pid if p.pid else "N/A"
                        self.patient_combo.addItem(f"{name} ({pid})", p.id)
                    except Exception:
                        name = f"Decryption failed (ID:{p.id})"
                        pid = p.pid if p.pid else "N/A"
                        self.patient_combo.addItem(f"{name} ({pid})", p.id)
        except Exception as e:
            logger.error(f"Error filtering patients: {str(e)}")

    def update_selected_tests_summary(self):
        if not self.selected_test_ids:
            self.selected_tests_label.setText("No tests selected")
            return
        html = "<b>Selected Tests:</b><br>"
        subtotal = 0.0
        try:
            with Session() as session:
                tests = session.query(Test).filter(Test.id.in_(self.selected_test_ids)).all()
                for t in tests:
                    rate = t.rate_inr or 0.0
                    html += f"{t.code} - {t.name} ({t.department}): ₹{rate:.2f}<br>"
                    subtotal += rate
        except Exception as e:
            logger.error(f"Error updating summary: {str(e)}")
        html += f"<br><b>Total:</b> ₹{subtotal:.2f}"
        self.selected_tests_label.setHtml(html)

    def load_combos(self):
        self.patient_combo.clear()
        try:
            with Session() as session:
                patients = session.query(Patient).all()
                self.patient_combo.addItem("-- Select Patient --", None)
                for p in patients:
                    try:
                        name = p.decrypted_name
                        pid = p.pid if p.pid else "N/A"
                        self.patient_combo.addItem(f"{name} ({pid})", p.id)
                    except Exception:
                        name = f"Decryption failed (ID:{p.id})"
                        pid = p.pid if p.pid else "N/A"
                        self.patient_combo.addItem(f"{name} ({pid})", p.id)
        except Exception as e:
            logger.error(f"Error loading patients: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load patients: {str(e)}")

    def place_order(self):
        try:
            patient_id = self.patient_combo.currentData()
            date = self.date_edit.dateTime().toPyDateTime()
            referring_physician = self.referring_physician.text().strip()
            
            if not referring_physician:
                QMessageBox.warning(self, "Error", "Referring Physician is required.")
                return
                
            test_ids = self.selected_test_ids
            if not patient_id or not test_ids:
                QMessageBox.warning(self, "Error", "Select a patient and at least one test.")
                return
                
            # Calculate subtotal
            subtotal = 0.0
            with Session() as session:
                tests = session.query(Test).filter(Test.id.in_(test_ids)).all()
                for t in tests:
                    subtotal += t.rate_inr or 0.0
            
            # Open PaymentDialog
            payment_dialog = PaymentDialog(subtotal, self)
            if not payment_dialog.exec():
                return
            
            discount_perc, payments_str = payment_dialog.get_data()
            
            self.status_bar.showMessage("Placing orders...")
            self.progress_bar.setMaximum(len(test_ids))
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            QApplication.processEvents()
            order_ids = []
            with Session() as session:
                max_group_id = session.query(func.max(Order.group_id)).scalar()
                group_id = (max_group_id or 0) + 1
                for i, tid in enumerate(test_ids):
                    order = Order(
                        patient_id=patient_id, 
                        test_id=tid, 
                        order_date=date, 
                        status="Pending", 
                        referring_physician=referring_physician,
                        payment_method=payments_str,
                        discount=discount_perc,
                        group_id=group_id
                    )
                    session.add(order)
                    session.flush()
                    order_ids.append(order.id)
                    self.progress_bar.setValue(i + 1)
                    QApplication.processEvents()
                session.commit()
            self.progress_bar.setVisible(False)
            self.clear_form()
            self.status_bar.showMessage(f"Orders placed successfully ({len(test_ids)} tests)")
            self.order_placed.emit()  # Emit signal to notify OrderSearchDialog
            QMessageBox.information(self, "Success", "Orders placed successfully.")
            logger.info(f"Placed {len(test_ids)} orders for patient ID {patient_id}")
            pdf_path = generate_invoice(order_ids)
            QMessageBox.information(self, "Invoice Generated", f"Invoice saved to {pdf_path}")
            os.startfile(pdf_path)
            self.show_invoice(order_ids)
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            self.status_bar.showMessage("Error placing order")
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to place order: {str(e)}")

    def show_invoice(self, order_ids):
        invoice_dialog = InvoiceDialog(order_ids, self)
        invoice_dialog.exec()

    def clear_form(self):
        self.patient_search.clear()
        self.patient_combo.setCurrentIndex(0)
        self.referring_physician.clear()
        self.date_edit.setDateTime(QDateTime.currentDateTime())
        self.package_combo.setCurrentIndex(0)
        self.selected_test_ids = []
        self.update_selected_tests_summary()
        self.status_bar.showMessage("Form cleared")

    def _on_refresh(self):
        self.load_combos()
        self.load_packages()
        self.status_bar.showMessage("Data refreshed")
        logger.info("Refreshed order tab data")

class BatchOrderDialog(QDialog):
    """Dialog for batch ordering (multiple patients with same package)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Order")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QComboBox, QLineEdit {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
                min-height: 35px;
            }
            QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                min-width: 100px;
            }
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #e2e8f0;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select Package:"))
        self.package_combo = QComboBox()
        self.load_packages()
        layout.addWidget(self.package_combo)
        
        layout.addWidget(QLabel("Select Patients (multiple):"))
        self.patient_list = QListWidget()
        self.patient_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.load_patients()
        layout.addWidget(self.patient_list)
        
        layout.addWidget(QLabel("Referring Physician:"))
        self.physician_edit = QLineEdit()
        layout.addWidget(self.physician_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.create_batch_orders)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_packages(self):
        self.package_combo.clear()
        self.package_combo.addItem("-- Select Package --", None)
        try:
            with Session() as session:
                packages = session.query(Package).all()
                for package in packages:
                    self.package_combo.addItem(package.name, package.id)
        except Exception as e:
            logger.error(f"Error loading packages: {str(e)}")
    
    def load_patients(self):
        self.patient_list.clear()
        try:
            with Session() as session:
                patients = session.query(Patient).all()
                for patient in patients:
                    try:
                        name = patient.decrypted_name
                        pid = patient.pid if patient.pid else "N/A"
                        item = QListWidgetItem(f"{name} ({pid})")
                        item.setData(Qt.ItemDataRole.UserRole, patient.id)
                        self.patient_list.addItem(item)
                    except Exception:
                        name = f"Decryption failed (ID:{patient.id})"
                        pid = patient.pid if patient.pid else "N/A"
                        item = QListWidgetItem(f"{name} ({pid})")
                        item.setData(Qt.ItemDataRole.UserRole, patient.id)
                        self.patient_list.addItem(item)
        except Exception as e:
            logger.error(f"Error loading patients: {str(e)}")
    
    def create_batch_orders(self):
        package_id = self.package_combo.currentData()
        if not package_id:
            QMessageBox.warning(self, "Warning", "Please select a package.")
            return
            
        selected_patients = []
        for i in range(self.patient_list.count()):
            if self.patient_list.item(i).isSelected():
                selected_patients.append(self.patient_list.item(i).data(Qt.ItemDataRole.UserRole))
                
        if not selected_patients:
            QMessageBox.warning(self, "Warning", "Please select at least one patient.")
            return
            
        physician = self.physician_edit.text().strip()
        if not physician:
            QMessageBox.warning(self, "Warning", "Please enter a referring physician.")
            return
            
        try:
            with Session() as session:
                package = session.get(Package, package_id)
                if not package:
                    QMessageBox.warning(self, "Warning", "Package not found.")
                    return
                    
                test_ids = package.test_ids.split(',') if package.test_ids else []
                order_date = datetime.now()
                
                # Generate a unique group_id for the batch
                max_group_id = session.query(func.max(Order.group_id)).scalar()
                group_id = (max_group_id or 0) + 1
                
                for patient_id in selected_patients:
                    for test_id in test_ids:
                        order = Order(
                            patient_id=patient_id,
                            test_id=int(test_id),
                            order_date=order_date,
                            status="Pending",
                            referring_physician=physician,
                            group_id=group_id
                        )
                        session.add(order)
                
                session.commit()
                QMessageBox.information(self, "Success", 
                                      f"Created {len(selected_patients) * len(test_ids)} orders successfully.")
                self.accept()
                
        except Exception as e:
            logger.error(f"Error creating batch orders: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to create batch orders: {str(e)}")

class InvoiceDialog(QDialog):
    """Dialog for generating and displaying invoices"""
    def __init__(self, order_ids, parent=None):
        super().__init__(parent)
        self.order_ids = order_ids
        self.setWindowTitle("Invoice")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
            QLabel {
                color: #4a5568; font-size: 13px; margin-top: 5px; padding: 3px;
            }
            QTextEdit {
                background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;
                padding: 6px 10px; font-size: 13px; color: #2d3748;
            }
            QDialogButtonBox QPushButton {
                background-color: #4a90e2; color: #ffffff; border-radius: 10px;
                padding: 8px 16px; font-size: 13px; font-weight: 500;
                
            }
            QDialogButtonBox QPushButton:hover { background-color: #357abd; }
            QDialogButtonBox QPushButton:pressed { background-color: #2c5aa0; }
        """)
        self.setup_ui()
        self.generate_invoice()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.invoice_text = QTextEdit()
        self.invoice_text.setReadOnly(True)
        layout.addWidget(self.invoice_text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def generate_invoice(self):
        try:
            with Session() as session:
                orders = session.query(Order).options(
                    joinedload(Order.patient), joinedload(Order.test)
                ).filter(Order.id.in_(self.order_ids)).all()
                if not orders:
                    self.invoice_text.setHtml("No orders found.")
                    return

                patient = orders[0].patient  # Assuming all orders for same patient
                invoice_content = f"<h3>Invoice</h3>"
                invoice_content += f"<p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
                invoice_content += f"<p><b>Patient:</b> {patient.decrypted_name if patient else 'N/A'} ({patient.pid if patient else 'N/A'})</p>"
                invoice_content += f"<p><b>Referring Physician:</b> {orders[0].referring_physician or 'N/A'}</p>"
                invoice_content += f"<p><b>Payment Method:</b> {orders[0].payment_method or 'N/A'}</p>"
                invoice_content += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
                invoice_content += "<tr><th>Test Code</th><th>Test Name</th><th>Department</th><th>Rate (INR)</th></tr>"
                subtotal = 0.0
                for order in orders:
                    t = order.test
                    rate = t.rate_inr or 0.0
                    subtotal += rate
                    invoice_content += f"<tr><td>{t.code}</td><td>{t.name}</td><td>{t.department}</td><td>₹{rate:.2f}</td></tr>"
                invoice_content += "</table>"
                discount_perc = orders[0].discount or 0.0
                discount_amt = subtotal * (discount_perc / 100)
                total = subtotal - discount_amt
                invoice_content += f"<p><b>Subtotal:</b> ₹{subtotal:.2f}</p>"
                invoice_content += f"<p><b>Discount ({discount_perc}%):</b> -₹{discount_amt:.2f}</p>"
                invoice_content += f"<p><b>Total Amount:</b> ₹{total:.2f}</p>"
                self.invoice_text.setHtml(invoice_content)
        except Exception as e:
            logger.error(f"Error generating invoice: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to generate invoice: {str(e)}")
