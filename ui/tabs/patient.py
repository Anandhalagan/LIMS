from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QLabel,
    QMessageBox, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QComboBox, QSpacerItem, QSizePolicy, QHeaderView, QFrame, QDialog,
    QDialogButtonBox, QScrollArea, QDateEdit, QFileDialog
)
from PyQt6.QtGui import QIntValidator, QIcon, QFont, QPalette, QColor
from PyQt6.QtCore import Qt, QTimer, QDate, pyqtSignal
from database import Session
from models import Patient, cipher, generate_pid
from sqlalchemy.sql import and_
import csv

class AddressDialog(QDialog):
    def __init__(self, parent=None, address_data=None):
        super().__init__(parent)
        self.setWindowTitle("Address Information")
        self.setModal(True)
        self.setMinimumSize(350, 300)
        self.resize(400, 320)
        self.setup_ui()
        self.apply_styles()
        if address_data:
            self.load_address_data(address_data)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Address Details")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setToolTip("Enter patient address details")
        layout.addWidget(header)

        form_group = QGroupBox("Address Information")
        form_layout = QGridLayout(form_group)
        form_layout.setContentsMargins(10, 15, 10, 10)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(8)

        labels = ["Door No.:", "Street:", "Location:", "District:", "Pincode:"]
        self.address_inputs = []
        tooltips = [
            "Enter door or house number (optional)",
            "Enter street name (required)",
            "Enter area or locality (optional)",
            "Enter district or city (optional)",
            "Enter 6-digit pincode (optional)"
        ]

        for i, label in enumerate(labels):
            label_widget = QLabel(label)
            label_widget.setMinimumWidth(70)
            form_layout.addWidget(label_widget, i, 0, Qt.AlignmentFlag.AlignRight)

            input_widget = QLineEdit()
            input_widget.setMinimumHeight(30)
            input_widget.setToolTip(tooltips[i])
            if i == 0:
                input_widget.setPlaceholderText("Door number")
            elif i == 1:
                input_widget.setPlaceholderText("Street name")
                input_widget.textChanged.connect(self.validate_street)
            elif i == 2:
                input_widget.setPlaceholderText("Area")
            elif i == 3:
                input_widget.setPlaceholderText("District")
            elif i == 4:
                input_widget.setPlaceholderText("6-digit pincode")
                input_widget.setValidator(QIntValidator(100000, 999999))
                input_widget.setMaxLength(6)
                input_widget.textChanged.connect(self.validate_pincode)

            form_layout.addWidget(input_widget, i, 1)
            self.address_inputs.append(input_widget)

        form_layout.setColumnStretch(1, 1)
        layout.addWidget(form_group)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(QIcon("icons/clear_icon.png"))
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(35)
        self.clear_btn.setMinimumWidth(70)
        self.clear_btn.setToolTip("Clear all address fields")
        layout.addWidget(self.clear_btn)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setToolTip("Save address details")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setToolTip("Discard changes")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.address_inputs[0].setFocus()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; color: #333; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; }
            QGroupBox { border: 1px solid #dee2e6; border-radius: 4px; margin-top: 8px; background-color: #ffffff; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 8px; padding: 0 6px; color: #495057; }
            QLabel { padding: 2px; color: #495057; font-weight: 500; }
            QLineEdit { padding: 6px; border: 1px solid #ced4da; border-radius: 3px; background-color: #ffffff; selection-background-color: #e2e6ea; font-size: 12px; }
            QLineEdit:focus { border-color: #80bdff; outline: none; }
            QLineEdit[error="true"] { border: 2px solid #dc3545; background-color: #fff5f5; }
            QDialogButtonBox QPushButton { padding: 6px 15px; border: none; border-radius: 3px; font-weight: bold; min-width: 70px; }
            QDialogButtonBox QPushButton[text="OK"] { background-color: #28a745; color: white; }
            QDialogButtonBox QPushButton[text="Cancel"] { background-color: #6c757d; color: white; }
            QPushButton#clear_btn { background-color: #6c757d; color: white; }
            QDialogButtonBox QPushButton:hover, QPushButton#clear_btn:hover { opacity: 0.9; }
        """)

    def load_address_data(self, address_text):
        parts = [part.strip() for part in address_text.split(',')]
        for i, part in enumerate(parts):
            if i < len(self.address_inputs) and part:
                self.address_inputs[i].setText(part)

    def get_address_data(self):
        address_parts = []
        for input_widget in self.address_inputs:
            text = input_widget.text().strip()
            if text:
                address_parts.append(text)
        return ', '.join(address_parts)

    def validate_inputs(self):
        errors = []
        if not self.address_inputs[1].text().strip():
            errors.append("Street name is required")
        pincode = self.address_inputs[4].text().strip()
        if pincode and (not pincode.isdigit() or len(pincode) != 6):
            errors.append("Pincode must be 6 digits")
        return errors

    def validate_street(self):
        street = self.address_inputs[1].text().strip()
        self.address_inputs[1].setProperty("error", not street)
        self.address_inputs[1].style().unpolish(self.address_inputs[1])
        self.address_inputs[1].style().polish(self.address_inputs[1])

    def validate_pincode(self):
        pincode = self.address_inputs[4].text().strip()
        valid = not pincode or (pincode.isdigit() and len(pincode) == 6)
        self.address_inputs[4].setProperty("error", not valid)
        self.address_inputs[4].style().unpolish(self.address_inputs[4])
        self.address_inputs[4].style().polish(self.address_inputs[4])

    def clear_inputs(self):
        for input_widget in self.address_inputs:
            input_widget.clear()

    def accept(self):
        errors = self.validate_inputs()
        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return
        super().accept()

class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Patients")
        self.setModal(True)
        self.setMinimumSize(500, 500)
        self.resize(550, 550)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Search Patients")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setToolTip("Search for patients by name, PID, or contact")
        layout.addWidget(header)

        form_group = QGroupBox("Search Criteria")
        form_layout = QGridLayout(form_group)
        form_layout.setContentsMargins(10, 15, 10, 10)
        form_layout.setVerticalSpacing(8)
        form_layout.setHorizontalSpacing(8)

        labels = ["Search By:", "Search Term:", "Start Date:", "End Date:"]
        self.search_inputs = []
        tooltips = [
            "Select search criteria (Name, PID, or Contact)",
            "Enter search term (e.g., patient name, PID, or phone)",
            "Select start date for creation date range",
            "Select end date for creation date range"
        ]

        for i, label in enumerate(labels):
            label_widget = QLabel(label)
            label_widget.setMinimumWidth(70)
            form_layout.addWidget(label_widget, i, 0, Qt.AlignmentFlag.AlignRight)

            if i == 0:
                input_widget = QComboBox()
                input_widget.addItems(["Name", "PID", "Contact"])
                input_widget.setMinimumHeight(30)
                input_widget.setToolTip(tooltips[i])
            elif i == 1:
                input_widget = QLineEdit()
                input_widget.setPlaceholderText("Name, PID, or contact")
                input_widget.setMinimumHeight(30)
                input_widget.setToolTip(tooltips[i])
            else:
                input_widget = QDateEdit()
                input_widget.setCalendarPopup(True)
                input_widget.setDate(QDate.currentDate().addDays(-30) if i == 2 else QDate.currentDate())
                input_widget.setDisplayFormat("yyyy-MM-dd")
                input_widget.setMinimumHeight(30)
                input_widget.setToolTip(tooltips[i])

            form_layout.addWidget(input_widget, i, 1)
            self.search_inputs.append(input_widget)

        form_layout.setColumnStretch(1, 1)
        layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        self.search_btn = QPushButton("Search")
        self.search_btn.setIcon(QIcon("icons/search_icon.png"))
        self.search_btn.clicked.connect(self.perform_search)
        self.search_btn.setMinimumHeight(35)
        self.search_btn.setToolTip("Perform search with the specified criteria")
        button_layout.addWidget(self.search_btn)

        self.export_btn = QPushButton("Export to CSV")
        self.export_btn.setIcon(QIcon("icons/export_icon.png"))
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setMinimumHeight(35)
        self.export_btn.setMinimumWidth(100)
        self.export_btn.setToolTip("Export search results to CSV")
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)

        self.results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(self.results_group)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(["ID", "Title", "PID", "Name", "Age", "Gender", "Contact", "Address"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.hideColumn(0)
        self.results_table.setSortingEnabled(True)
        self.results_table.setToolTip("Double-click a row to view patient details")
        results_layout.addWidget(self.results_table)
        layout.addWidget(self.results_group)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).setToolTip("Close the search dialog")
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.search_inputs[1].setFocus()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #f8f9fa; color: #333; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; }
            QGroupBox { border: 1px solid #dee2e6; border-radius: 4px; margin-top: 8px; background-color: #ffffff; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 8px; padding: 0 6px; color: #495057; }
            QLabel { padding: 2px; color: #495057; font-weight: 500; }
            QLineEdit, QComboBox, QDateEdit { padding: 6px; border: 1px solid #ced4da; border-radius: 3px; background-color: #ffffff; selection-background-color: #e2e6ea; font-size: 12px; }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: #80bdff; outline: none; }
            QPushButton { padding: 6px 15px; border: none; border-radius: 3px; font-weight: bold; min-width: 70px; }
            QPushButton[text="Search"] { background-color: #007bff; color: white; }
            QPushButton[text="Close"] { background-color: #6c757d; color: white; }
            QPushButton#export_btn { background-color: #17a2b8; color: white; }
            QPushButton:hover { opacity: 0.9; }
            QTableWidget { background-color: #ffffff; gridline-color: #dee2e6; border: 1px solid #dee2e6; alternate-background-color: #f8f9fa; selection-background-color: #d1e7ff; selection-color: #004085; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background-color: #b8daff; color: #004085; }
            QHeaderView::section { background-color: #e9ecef; padding: 8px; border: none; font-weight: bold; border-bottom: 2px solid #dee2e6; }
        """)
        self.search_btn.setObjectName("search_btn")
        self.export_btn.setObjectName("export_btn")

    def perform_search(self):
        search_by, search_term, start_date, end_date = self.get_search_criteria()
        session = Session()
        try:
            query = session.query(Patient)
            if start_date and end_date:  # Date filter takes precedence
                query = query.filter(and_(Patient.created_at >= start_date, Patient.created_at <= end_date))
            elif search_by and search_term:  # Fallback to search term if no date filter
                if search_by == "Name":
                    query = query.filter(Patient.name.contains(cipher.encrypt(search_term.encode()).decode()))
                elif search_by == "PID":
                    query = query.filter(Patient.pid.ilike(f"%{search_term}%"))
                elif search_by == "Contact":
                    query = query.filter(Patient.contact.contains(cipher.encrypt(search_term.encode()).decode()))
            else:
                QMessageBox.warning(self, "Error", "Please provide a search term or date range.")
                return

            patients = query.all()
            self.results_table.setRowCount(len(patients))
            for row, patient in enumerate(patients):
                self.results_table.setItem(row, 0, QTableWidgetItem(str(patient.id)))
                self.results_table.setItem(row, 1, QTableWidgetItem(patient.decrypted_title))
                self.results_table.setItem(row, 2, QTableWidgetItem(patient.pid if patient.pid else ""))
                self.results_table.setItem(row, 3, QTableWidgetItem(patient.decrypted_name))
                self.results_table.setItem(row, 4, QTableWidgetItem(str(patient.age) if patient.age else ""))
                self.results_table.setItem(row, 5, QTableWidgetItem(patient.gender if patient.gender else ""))
                self.results_table.setItem(row, 6, QTableWidgetItem(patient.decrypted_contact if patient.contact else ""))
                self.results_table.setItem(row, 7, QTableWidgetItem(patient.decrypted_address if patient.address else ""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to perform search: {e}")
        finally:
            session.close()

    def get_search_criteria(self):
        search_by = self.search_inputs[0].currentText()
        search_term = self.search_inputs[1].text().strip()
        start_date = self.search_inputs[2].date().toPyDate()
        end_date = self.search_inputs[3].date().toPyDate()
        return search_by, search_term, start_date, end_date

    def export_results(self):
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No search results to export.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")
        if not file_name:
            return

        try:
            with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                headers = ["Title", "PID", "Name", "Age", "Gender", "Contact", "Address"]
                writer.writerow(headers)
                for row in range(self.results_table.rowCount()):
                    row_data = []
                    for col in range(1, self.results_table.columnCount()):
                        item = self.results_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            QMessageBox.information(self, "Success", f"Search results exported to {file_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export results: {e}")

class PatientTab(QWidget):
    # Signal emitted when patients are created/updated/deleted so other tabs can refresh
    # Emits the patient id (int) when a patient is created/updated, or 0 when deleted
    patient_saved = pyqtSignal(int)
    # Signal emitted when user wants to open Orders tab for a specific patient
    patient_open_in_order = pyqtSignal(int)
    def __init__(self, current_user=None):
        super().__init__()
        # Store current user (MainWindow will pass current_user when available)
        self.current_user = current_user
        self.setWindowTitle("Patient Management")
        self.setup_ui()
        self.apply_styles()
        self.clear_inputs()
        self.load_patients()
        self.setup_responsive_behavior()

    def setup_responsive_behavior(self):
        self.setMinimumSize(800, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_resize_finished)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(100)

    def on_resize_finished(self):
        self.adjust_layout_for_size()

    def adjust_layout_for_size(self):
        width = self.width()
        if hasattr(self, 'table'):
            if width < 800:
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
                self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            else:
                self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def setup_ui(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        main_widget = QWidget()
        scroll_area.setWidget(main_widget)

        main_container_layout = QVBoxLayout(self)
        main_container_layout.setContentsMargins(0, 0, 0, 0)
        main_container_layout.addWidget(scroll_area)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        header = QLabel("Patient Management")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setToolTip("Manage patient records")
        main_layout.addWidget(header)

        form_group = QGroupBox("Patient Information")
        self.form_layout = QGridLayout(form_group)
        self.form_layout.setContentsMargins(8, 10, 8, 8)
        self.form_layout.setHorizontalSpacing(6)
        self.form_layout.setVerticalSpacing(6)

        labels = ["Title:", "PID:", "Name:", "Age:", "Gender:", "Contact:", "Address:"]
        tooltips = [
            "Select patient title (optional)",
            "Enter or auto-generate PID (e.g., ABC00001)",
            "Enter full name (required)",
            "Enter age (0–150, required)",
            "Select gender (required)",
            "Enter phone or email (optional)",
            "Enter address via details button (optional)"
        ]

        for i, label in enumerate(labels):
            label_widget = QLabel(label)
            label_widget.setMinimumWidth(30)
            self.form_layout.addWidget(label_widget, i, 0, Qt.AlignmentFlag.AlignRight)

        self.title_input = QComboBox()
        self.title_input.addItems(["Mr.", "Mrs.", "Master.", "Ms.", "Dr.", "Miss.", "Baby."])
        self.title_input.setMinimumHeight(28)
        self.title_input.setToolTip(tooltips[0])
        self.form_layout.addWidget(self.title_input, 0, 1)

        self.pid_input = QLineEdit()
        self.pid_input.setPlaceholderText("Auto-generate PID")
        self.pid_input.setMinimumHeight(28)
        self.pid_input.setToolTip(tooltips[1])
        self.pid_input.textChanged.connect(self.validate_pid)
        self.form_layout.addWidget(self.pid_input, 1, 1)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")
        self.name_input.setMinimumHeight(28)
        self.name_input.setToolTip(tooltips[2])
        self.name_input.textChanged.connect(self.validate_name)
        self.form_layout.addWidget(self.name_input, 2, 1)

        self.age_input = QLineEdit()
        self.age_input.setValidator(QIntValidator(0, 150))
        self.age_input.setPlaceholderText("0–150")
        self.age_input.setMinimumHeight(28)
        self.age_input.setToolTip(tooltips[3])
        self.age_input.textChanged.connect(self.validate_age)
        self.form_layout.addWidget(self.age_input, 3, 1)

        self.gender_input = QComboBox()
        self.gender_input.addItems(["Male", "Female", "Other"])
        self.gender_input.setMinimumHeight(28)
        self.gender_input.setToolTip(tooltips[4])
        self.form_layout.addWidget(self.gender_input, 4, 1)

        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Phone/email")
        self.contact_input.setMinimumHeight(28)
        self.contact_input.setToolTip(tooltips[5])
        self.form_layout.addWidget(self.contact_input, 5, 1)

        address_layout = QHBoxLayout()
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address details")
        self.address_input.setReadOnly(True)
        self.address_input.setMinimumHeight(28)
        self.address_input.setToolTip(tooltips[6])
        self.address_btn = QPushButton("Address")
        self.address_btn.setIcon(QIcon("icons/address_icon.png"))
        self.address_btn.clicked.connect(self.open_address_dialog)
        self.address_btn.setMinimumHeight(32)
        self.address_btn.setMinimumWidth(90)
        self.address_btn.setToolTip("Open address details dialog")
        address_layout.addWidget(self.address_input, 1)
        address_layout.addWidget(self.address_btn)
        self.form_layout.addLayout(address_layout, 6, 1)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(5)

        self.save_btn = QPushButton("Save Patient")
        self.save_btn.setIcon(QIcon("icons/save_icon.png"))
        self.save_btn.clicked.connect(self.save_patient)
        self.save_btn.setMinimumHeight(32)
        self.save_btn.setMinimumWidth(90)
        self.save_btn.setToolTip("Save patient details")
        btn_layout.addWidget(self.save_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(QIcon("icons/refresh_icon.png"))
        self.refresh_btn.clicked.connect(self.load_patients)
        self.refresh_btn.setMinimumHeight(32)
        self.refresh_btn.setMinimumWidth(90)
        self.refresh_btn.setToolTip("Reload patient records")
        btn_layout.addWidget(self.refresh_btn)

        self.search_btn = QPushButton("Search")
        self.search_btn.setIcon(QIcon("icons/search_icon.png"))
        self.search_btn.clicked.connect(self.open_search_dialog)
        self.search_btn.setMinimumHeight(32)
        self.search_btn.setMinimumWidth(90)
        self.search_btn.setToolTip("Open search dialog")
        btn_layout.addWidget(self.search_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(QIcon("icons/clear_icon.png"))
        self.clear_btn.clicked.connect(self.clear_inputs)
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.setMinimumWidth(90)
        self.clear_btn.setToolTip("Clear all input fields")
        btn_layout.addWidget(self.clear_btn)

        # Button to open Orders tab with selected patient
        self.open_in_order_btn = QPushButton("Order For Patient")
        self.open_in_order_btn.setIcon(QIcon("icons/order_icon.png"))
        self.open_in_order_btn.clicked.connect(self.open_in_orders_tab)
        self.open_in_order_btn.setMinimumHeight(32)
        self.open_in_order_btn.setMinimumWidth(120)
        self.open_in_order_btn.setToolTip("Open Orders tab and select the highlighted patient")
        self.open_in_order_btn.setObjectName("open_in_order_btn")
        btn_layout.addWidget(self.open_in_order_btn)

        btn_layout.addStretch()
        self.form_layout.addLayout(btn_layout, 0, 2, 7, 1)
        self.form_layout.setColumnStretch(1, 1)
        main_layout.addWidget(form_group)

        table_group = QGroupBox("Patient Records")
        table_layout = QVBoxLayout(table_group)
        table_layout.setContentsMargins(5, 10, 5, 5)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "PID", "Name", "Age", "Gender", "Contact", "Address"])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.hideColumn(0)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_patient)
        self.table.setMinimumHeight(250)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setToolTip("Double-click a row to edit patient")
        table_layout.addWidget(self.table)
        main_layout.addWidget(table_group, 1)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setIcon(QIcon("icons/edit_icon.png"))
        self.edit_btn.clicked.connect(self.edit_patient)
        self.edit_btn.setMinimumHeight(32)
        self.edit_btn.setMinimumWidth(90)
        self.edit_btn.setToolTip("Edit selected patient")
        action_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setIcon(QIcon("icons/delete_icon.png"))
        self.delete_btn.clicked.connect(self.delete_patient)
        self.delete_btn.setMinimumHeight(32)
        self.delete_btn.setMinimumWidth(90)
        self.delete_btn.setToolTip("Delete selected patient")
        action_layout.addWidget(self.delete_btn)

        main_layout.addLayout(action_layout)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8f9fa; color: #1a202c; font-family: 'Calibri', Arial, sans-serif; font-size: 12px; }
            QScrollArea { border: none; background-color: #f8f9fa; }
            QGroupBox { border: 1px solid #dee2e6; border-radius: 4px; margin-top: 8px; background-color: #ffffff; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 6px; color: #1a202c; }
            QLabel { padding: 2px; color: #1a202c; }
            QLineEdit, QComboBox, QDateEdit { padding: 5px; border: 1px solid #ced4da; border-radius: 3px; background-color: #ffffff; selection-background-color: #e2e6ea; min-height: 26px; }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: #007bff; outline: none; }
            QLineEdit[readOnly="true"] { background-color: #e9ecef; color: #6c757d; }
            QLineEdit[error="true"] { border: 2px solid #dc3545; background-color: #fff5f5; }
            QPushButton { padding: 5px 12px; border: none; border-radius: 3px; font-weight: bold; min-height: 26px; min-width: 80px; }
            QPushButton:hover { opacity: 0.95; }
            QPushButton:pressed { opacity: 0.85; }
            #save_btn { background-color: #28a745; color: white; }
            #refresh_btn { background-color: #17a2b8; color: white; }
            #search_btn { background-color: #007bff; color: white; }
            #open_in_order_btn { background-color: #007bff; color: white; }
            #edit_btn { background-color: #ffc107; color: #212529; }
            #delete_btn { background-color: #dc3545; color: white; }
            #address_btn { background-color: #6f42c1; color: white; }
            #clear_btn { background-color: #6c757d; color: white; }
            QTableWidget { background-color: #ffffff; gridline-color: #dee2e6; border: 1px solid #dee2e6; alternate-background-color: #f8f9fa; selection-background-color: #d1e7ff; selection-color: #004085; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background-color: #b8daff; color: #004085; }
            QHeaderView::section { background-color: #e9ecef; padding: 8px; border: none; font-weight: bold; border-bottom: 2px solid #dee2e6; }
        """)
        self.save_btn.setObjectName("save_btn")
        self.refresh_btn.setObjectName("refresh_btn")
        self.search_btn.setObjectName("search_btn")
        self.edit_btn.setObjectName("edit_btn")
        self.delete_btn.setObjectName("delete_btn")
        self.address_btn.setObjectName("address_btn")
        self.clear_btn.setObjectName("clear_btn")
        self.open_in_order_btn.setObjectName("open_in_order_btn")

    def open_address_dialog(self):
        current_address = self.address_input.text()
        dialog = AddressDialog(self, current_address if current_address else None)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            address_data = dialog.get_address_data()
            self.address_input.setText(address_data)

    def open_search_dialog(self):
        dialog = SearchDialog(self)
        dialog.exec()

    def open_in_orders_tab(self):
        # Use selected row in the patients table to identify patient
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Error", "Please select a patient from the table to open in Orders tab.")
            return
        row = selected_rows[0].row()
        try:
            patient_id = int(self.table.item(row, 0).text())
            self.patient_open_in_order.emit(patient_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to determine selected patient: {e}")

    def save_patient(self):
        title = self.title_input.currentText().strip()
        pid = self.pid_input.text().strip()
        name = self.name_input.text().strip()
        age = self.age_input.text().strip()
        gender = self.gender_input.currentText().strip()
        contact = self.contact_input.text().strip()
        address = self.address_input.text().strip()

        self.name_input.setProperty("error", False)
        self.age_input.setProperty("error", False)
        self.pid_input.setProperty("error", False)
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)
        self.age_input.style().unpolish(self.age_input)
        self.age_input.style().polish(self.age_input)
        self.pid_input.style().unpolish(self.pid_input)
        self.pid_input.style().polish(self.pid_input)

        has_error = False
        if not name:
            self.name_input.setProperty("error", True)
            self.name_input.style().unpolish(self.name_input)
            self.name_input.style().polish(self.name_input)
            has_error = True

        if not age or not age.isdigit():
            self.age_input.setProperty("error", True)
            self.age_input.style().unpolish(self.age_input)
            self.age_input.style().polish(self.age_input)
            has_error = True

        if pid and not (len(pid) == 8 and pid[:3].isalpha() and pid[3:].isdigit() and int(pid[3:]) < 100000):
            self.pid_input.setProperty("error", True)
            self.pid_input.style().unpolish(self.pid_input)
            self.pid_input.style().polish(self.pid_input)
            has_error = True

        if has_error:
            QMessageBox.warning(self, "Error", "Please fill in all required fields correctly.")
            return

        session = Session()
        patient = Patient()
        try:
            if not pid:
                pid = generate_pid()
                while session.query(Patient).filter_by(pid=pid).first():
                    pid = generate_pid()
            patient.pid = pid
            patient.title = cipher.encrypt(title.encode()).decode() if title else None
            patient.name = cipher.encrypt(name.encode()).decode()
            patient.age = int(age)
            patient.gender = gender
            patient.contact = cipher.encrypt(contact.encode()).decode() if contact else None
            patient.address = cipher.encrypt(address.encode()).decode() if address else None
            session.add(patient)
            session.commit()
            # Notify other tabs (e.g., OrderTab) that a patient was created
            try:
                self.patient_saved.emit(patient.id if patient and patient.id else 0)
                # Also request Orders tab to open for this patient so it becomes selected
                if patient and patient.id:
                    try:
                        self.patient_open_in_order.emit(patient.id)
                    except Exception:
                        pass
            except Exception:
                pass
            QMessageBox.information(self, "Success", f"Patient saved with PID: {pid}")
            self.clear_inputs()
            self.load_patients()
        except ValueError as ve:
            session.rollback()
            QMessageBox.warning(self, "Error", f"Invalid age format: {ve}")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save patient: {e}")
        finally:
            session.close()

    def load_patients(self):
        session = Session()
        try:
            patients = session.query(Patient).all()
            self.table.setRowCount(len(patients))
            for row, patient in enumerate(patients):
                self.table.setItem(row, 0, QTableWidgetItem(str(patient.id)))
                self.table.setItem(row, 1, QTableWidgetItem(patient.decrypted_title))
                self.table.setItem(row, 2, QTableWidgetItem(patient.pid if patient.pid else ""))
                self.table.setItem(row, 3, QTableWidgetItem(patient.decrypted_name))
                self.table.setItem(row, 4, QTableWidgetItem(str(patient.age) if patient.age else ""))
                self.table.setItem(row, 5, QTableWidgetItem(patient.gender if patient.gender else ""))
                self.table.setItem(row, 6, QTableWidgetItem(patient.decrypted_contact if patient.contact else ""))
                self.table.setItem(row, 7, QTableWidgetItem(patient.decrypted_address if patient.address else ""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load patients: {e}")
        finally:
            session.close()

    def edit_patient(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Error", "Please select a patient to edit.")
            return
        row = selected_rows[0].row()
        patient_id = int(self.table.item(row, 0).text())
        session = Session()
        patient = session.query(Patient).filter_by(id=patient_id).first()
        if patient:
            try:
                self.title_input.setCurrentText(patient.decrypted_title)
                self.pid_input.setText(patient.pid if patient.pid else "")
                self.name_input.setText(patient.decrypted_name)
                self.age_input.setText(str(patient.age) if patient.age else "")
                self.gender_input.setCurrentText(patient.gender if patient.gender else "")
                self.contact_input.setText(patient.decrypted_contact if patient.contact else "")
                self.address_input.setText(patient.decrypted_address if patient.address else "")
                self.save_btn.setText("Update Patient")
                self.save_btn.clicked.disconnect()
                self.save_btn.clicked.connect(lambda: self.update_patient(patient_id))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load patient data: {e}")
        session.close()

    def update_patient(self, patient_id):
        title = self.title_input.currentText().strip()
        pid = self.pid_input.text().strip()
        name = self.name_input.text().strip()
        age = self.age_input.text().strip()
        gender = self.gender_input.currentText().strip()
        contact = self.contact_input.text().strip()
        address = self.address_input.text().strip()

        if not name or not age or not gender:
            QMessageBox.warning(self, "Error", "Name, Age, and Gender are required.")
            return
        if pid and not (len(pid) == 8 and pid[:3].isalpha() and pid[3:].isdigit() and int(pid[3:]) < 100000):
            QMessageBox.warning(self, "Error", "PID must be 8 characters, start with 3 letters, and end with 5 digits (e.g., ABC00001)")
            return

        session = Session()
        patient = session.query(Patient).filter_by(id=patient_id).first()
        if patient:
            try:
                patient.title = cipher.encrypt(title.encode()).decode() if title else None
                patient.pid = pid
                patient.name = cipher.encrypt(name.encode()).decode()
                patient.age = int(age) if age.isdigit() else None
                patient.gender = gender
                patient.contact = cipher.encrypt(contact.encode()).decode() if contact else None
                patient.address = cipher.encrypt(address.encode()).decode() if address else None
                session.commit()
                QMessageBox.information(self, "Success", "Patient updated successfully.")
                # Notify other tabs that patient data changed (emit updated patient id)
                try:
                    self.patient_saved.emit(patient_id if patient_id else 0)
                    # Also open Orders tab for this updated patient
                    if patient_id:
                        try:
                            self.patient_open_in_order.emit(patient_id)
                        except Exception:
                            pass
                except Exception:
                    pass
                self.clear_inputs()
                self.load_patients()
                self.save_btn.setText("Save Patient")
                self.save_btn.clicked.disconnect()
                self.save_btn.clicked.connect(self.save_patient)
            except ValueError as ve:
                session.rollback()
                QMessageBox.warning(self, "Error", f"Invalid age format: {ve}")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to update patient: {e}")
        session.close()

    def delete_patient(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Error", "Please select a patient to delete.")
            return
        # Restrict deletion to admin users
        try:
            role = self.current_user.role if self.current_user else None
        except Exception:
            role = None
        if role != "admin":
            QMessageBox.warning(self, "Permission Denied", "Only admin users can delete patients.")
            return
        row = selected_rows[0].row()
        patient_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to delete this patient?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            session = Session()
            patient = session.query(Patient).filter_by(id=patient_id).first()
            try:
                if patient:
                    # Archive before deletion
                    try:
                        from models import archive_patient
                        deleted_by = self.current_user.id if hasattr(self.current_user, 'id') else None
                        archive_patient(session, patient, deleted_by=deleted_by)
                    except Exception as arch_err:
                        # If archiving fails, abort delete and show error
                        session.rollback()
                        QMessageBox.critical(self, "Error", f"Failed to archive patient before deletion: {arch_err}")
                        return

                    # Now delete (cascade will handle related records)
                    session.delete(patient)
                    deleted_id = patient.id if patient else 0
                    session.commit()
                    QMessageBox.information(self, "Success", "Patient archived and deleted successfully.")
                    # Notify other tabs that a patient was deleted (emit 0 to indicate deletion)
                    try:
                        self.patient_saved.emit(0)
                    except Exception:
                        pass
                    self.load_patients()
                else:
                    QMessageBox.warning(self, "Error", "Patient not found.")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete patient: {e}")
            finally:
                session.close()

    def clear_inputs(self):
        self.title_input.setCurrentIndex(0)
        self.pid_input.clear()
        self.name_input.clear()
        self.age_input.clear()
        self.gender_input.setCurrentIndex(0)
        self.contact_input.clear()
        self.address_input.clear()
        self.save_btn.setText("Save Patient")
        try:
            self.save_btn.clicked.disconnect()
        except TypeError:
            pass
        self.save_btn.clicked.connect(self.save_patient)
        self.validate_name()
        self.validate_age()
        self.validate_pid()

    def validate_name(self):
        name = self.name_input.text().strip()
        self.name_input.setProperty("error", not name)
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)

    def validate_age(self):
        age = self.age_input.text().strip()
        self.age_input.setProperty("error", not (age and age.isdigit() and 0 <= int(age) <= 150))
        self.age_input.style().unpolish(self.age_input)
        self.age_input.style().polish(self.age_input)

    def validate_pid(self):
        pid = self.pid_input.text().strip()
        valid = not pid or (len(pid) == 8 and pid[:3].isalpha() and pid[3:].isdigit() and int(pid[3:]) < 100000)
        self.pid_input.setProperty("error", not valid)
        self.pid_input.style().unpolish(self.pid_input)
        self.pid_input.style().polish(self.pid_input)