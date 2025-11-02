import json
import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QFormLayout, QLineEdit, QTableWidgetItem,
    QTextEdit, QPushButton, QGroupBox, QGridLayout, QDateEdit, QScrollArea,
    QMessageBox, QFrame, QSizePolicy, QDialog, QDialogButtonBox, QProgressBar,
    QTableWidget
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QAction, QDoubleValidator, QPalette, QColor
from ui.components.test_table import TestTable
from database import Session
from models import Result, Order, Test, Patient, AuditLog, User
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy.sql.sqltypes import String
from sqlalchemy.sql.expression import cast
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CollapsibleGroupBox(QGroupBox):
    toggled = pyqtSignal(bool)

    def __init__(self, title):
        super().__init__(title)
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #d1d5db;
                border-radius: 8px;
                margin-top: 12px;
                padding: 10px;
                background-color: #ffffff;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 4px 12px;
                color: #1f2937;
                font-size: 16px;
                font-weight: bold;
                background-color: #f3f4f6;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                min-width: 100px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.layout = QVBoxLayout()
        self.toggle_button = QPushButton("Collapse")
        self.toggle_button.clicked.connect(self.toggle)
        self.layout.addWidget(self.toggle_button)
        self.content_widget = None
        self.setLayout(self.layout)
        self.is_expanded = True

    def setContentLayout(self, layout):
        if self.content_widget:
            self.layout.removeWidget(self.content_widget)
            self.content_widget.deleteLater()
        self.content_widget = QWidget()
        self.content_widget.setLayout(layout)
        self.layout.addWidget(self.content_widget)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.toggle_button.setText("Expand" if not self.is_expanded else "Collapse")
        if self.content_widget:
            self.content_widget.setVisible(self.is_expanded)
        self.toggled.emit(self.is_expanded)

class PatientSearchDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Search Patient")
        self.setStyleSheet("""
            QDialog {
                background-color: #f9fafb;
                border: 1px solid #d1d5db;
                border-radius: 10px;
            }
            QLabel {
                color: #1f2937;
                font-size: 14px;
                padding: 6px;
                font-weight: 500;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #ffffff;
                color: #1f2937;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: #f0f6ff;
            }
            QTableWidget {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #ffffff;
            }
            QTableWidget:item {
                padding: 8px;
                color: #1f2937;
                font-size: 13px;
            }
            QTableWidget:item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.setMinimumSize(600, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Search inputs
        search_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter patient name")
        self.name_input.setToolTip("Search by patient name (partial match)")
        self.name_input.setAccessibleName("Patient Name Search")
        self.name_input.textChanged.connect(self.search_patients)
        search_layout.addRow(QLabel("Name:"), self.name_input)

        self.pid_input = QLineEdit()
        self.pid_input.setPlaceholderText("Enter PID (e.g., ABC00001)")
        self.pid_input.setToolTip("Search by patient PID")
        self.pid_input.setAccessibleName("Patient PID Search")
        self.pid_input.textChanged.connect(self.search_patients)
        search_layout.addRow(QLabel("PID:"), self.pid_input)

        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Enter contact number")
        self.contact_input.setToolTip("Search by patient contact number")
        self.contact_input.setAccessibleName("Patient Contact Search")
        self.contact_input.textChanged.connect(self.search_patients)
        search_layout.addRow(QLabel("Contact:"), self.contact_input)

        self.layout.addLayout(search_layout)

        # Patient table
        self.patient_table = QTableWidget()
        self.patient_table.setColumnCount(4)
        self.patient_table.setHorizontalHeaderLabels(["ID", "Name", "PID", "Contact"])
        self.patient_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.patient_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.patient_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.patient_table.setAccessibleName("Patient Search Results")
        self.layout.addWidget(self.patient_table)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.select_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.select_btn.setText("Select")
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

        self.setLayout(self.layout)
        self.patient_table.itemSelectionChanged.connect(self.enable_select_button)
        self.search_patients()

    def search_patients(self):
        name = self.name_input.text().lower().strip()
        pid = self.pid_input.text().strip()
        contact = self.contact_input.text().strip()

        session = Session()
        try:
            query = session.query(Patient)
            if pid:
                query = query.filter(Patient.pid.contains(pid))
            patients = query.all()
            filtered_patients = []
            for patient in patients:
                try:
                    p_name = patient.decrypted_name.lower()
                except Exception as e:
                    logger.warning(f"Decryption error for patient {patient.id}: {e}")
                    p_name = ''
                try:
                    p_contact = (patient.decrypted_contact or '').lower()
                except Exception as e:
                    logger.warning(f"Decryption error for contact {patient.id}: {e}")
                    p_contact = ''
                if (not name or name in p_name) and (not contact or contact in p_contact):
                    filtered_patients.append(patient)
            self.patient_table.setRowCount(len(filtered_patients))
            for row, patient in enumerate(filtered_patients):
                patient_name = patient.decrypted_name if hasattr(patient, 'decrypted_name') else "Decryption Failed"
                patient_contact = patient.decrypted_contact or "N/A"
                self.patient_table.setItem(row, 0, QTableWidgetItem(str(patient.id)))
                self.patient_table.setItem(row, 1, QTableWidgetItem(patient_name))
                self.patient_table.setItem(row, 2, QTableWidgetItem(patient.pid or "N/A"))
                self.patient_table.setItem(row, 3, QTableWidgetItem(patient_contact))
            self.patient_table.resizeColumnsToContents()
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            QMessageBox.critical(self, "Error", f"Failed to search patients: {str(e)}")
        finally:
            session.close()

    def enable_select_button(self):
        self.select_btn.setEnabled(self.patient_table.currentRow() >= 0)

    def get_selected_patient_id(self):
        selected_row = self.patient_table.currentRow()
        if selected_row >= 0:
            return int(self.patient_table.item(selected_row, 0).text())
        return None

class ProfessionalFieldWidget(QWidget):
    def __init__(self, field_name, field_type, unit="", reference_range=""):
        super().__init__()
        self.field_name = field_name
        self.field_type = field_type
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)  # Reduced vertical margins
        
        # Field label with reference range
        label_text = f"{field_name}"
        if unit:
            label_text += f" ({unit})"
        if reference_range:
            label_text += f" [Ref: {reference_range}]"
            
        self.label = QLabel(label_text)
        self.label.setMinimumWidth(220)  # Slightly wider for better readability
        self.label.setStyleSheet("font-weight: 500; color: #374151; font-size: 13px;")
        layout.addWidget(self.label)
        
        # Input field
        if field_type in ['float', 'int']:
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Enter value...")
            if field_type == 'float':
                self.input_field.setValidator(QDoubleValidator())
            self.input_field.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    background-color: #ffffff;
                    font-size: 13px;
                    min-height: 20px;
                }
                QLineEdit:focus {
                    border-color: #3b82f6;
                    background-color: #f0f9ff;
                }
                QLineEdit:disabled {
                    background-color: #f3f4f6;
                    color: #6b7280;
                }
            """)
        else:
            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Enter text...")
            self.input_field.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    background-color: #ffffff;
                    font-size: 13px;
                    min-height: 20px;
                }
                QLineEdit:focus {
                    border-color: #3b82f6;
                    background-color: #f0f9ff;
                }
            """)
            
        self.input_field.setMinimumWidth(180)  # Wider input fields
        self.input_field.setMaximumWidth(250)
        layout.addWidget(self.input_field)
        layout.addStretch()
        
        self.setLayout(layout)

    def get_value(self):
        return self.input_field.text().strip()

    def set_value(self, value):
        self.input_field.setText(str(value) if value is not None else "")

    def set_calculated(self, is_calculated=False):
        if is_calculated:
            self.input_field.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    border: 1px solid #10b981;
                    border-radius: 6px;
                    background-color: #ecfdf5;
                    font-size: 13px;
                    font-weight: 500;
                    color: #065f46;
                    min-height: 20px;
                }
                QLineEdit:disabled {
                    background-color: #d1fae5;
                    color: #065f46;
                }
            """)
            self.input_field.setEnabled(False)

class ResultEntryDialog(QDialog):
    def __init__(self, parent, order_id, editing_result_id=None):
        super().__init__(parent)
        self.order_id = order_id
        self.editing_result_id = editing_result_id
        self.setWindowTitle("Laboratory Result Entry" if not editing_result_id else "Edit Laboratory Result")
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 6px;
                padding: 8px;
                background-color: #ffffff;
                font-weight: bold;
                color: #1e293b;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 3px 6px;
                background-color: #f1f5f9;
                border-radius: 4px;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
            }
            QLabel {
                color: #1a202c;
                font-size: 12px;
                padding: 2px;
                font-weight: 500;
                font-family: 'Calibri', Arial, sans-serif;
            }
            QTextEdit {
                padding: 8px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #ffffff;
                color: #1a202c;
                font-size: 12px;
                font-family: 'Calibri', Arial, sans-serif;
            }
            QTextEdit:focus {
                border-color: #3b82f6;
                background-color: #f8fafc;
            }
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #d1d5db;
            }
            QProgressBar {
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background-color: #f3f4f6;
                text-align: center;
                font-size: 10px;
                color: #6b7280;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 6px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1000, 800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(6)  # Reduced overall spacing
        self.layout.setContentsMargins(12, 12, 12, 12)  # Reduced margins

        # Header with test information - COMPACT
        self.create_header_section()
        
        # Patient Details - COMPACT
        self.create_patient_section()
        
        # Dynamic form for test parameters - MAXIMIZED SPACE
        self.create_test_parameters_section()

        # Notes section - COMPACT
        self.create_notes_section()

        # Action buttons
        self.create_action_buttons()

        self.setLayout(self.layout)
        self.validation_errors = []

        # Calculation mapping
        self.calculation_map = {
            'LTP': {
                'Globulin': self.calculate_globulin,
                'A/G Ratio': self.calculate_ag_ratio
            },
            'LFT': {
                'Globulin': self.calculate_globulin,
                'A/G Ratio': self.calculate_ag_ratio
            },
            'LIPID': {
                'LDL Cholesterol': self.calculate_ldl,
                'VLDL Cholesterol': self.calculate_vldl,
                'Non-HDL Cholesterol': self.calculate_non_hdl,
                'TC/HDL Ratio': self.calculate_tc_hdl_ratio,
                'LDL/HDL Ratio': self.calculate_ldl_hdl_ratio
            },
            'LIP': {
                'LDL Cholesterol': self.calculate_ldl,
                'VLDL Cholesterol': self.calculate_vldl,
                'Non-HDL Cholesterol': self.calculate_non_hdl,
                'TC/HDL Ratio': self.calculate_tc_hdl_ratio,
                'LDL/HDL Ratio': self.calculate_ldl_hdl_ratio
            }
        }

        self.calculation_dependencies = {}
        self.calculated_fields = {}
        self.field_widgets = []

        self.load_order_details()

    def create_header_section(self):
        """Compact header section"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #3b82f6, stop: 1 #1d4ed8);
                border-radius: 6px;
                padding: 8px;
            }
            QLabel {
                color: white;
                font-weight: 600;
            }
        """)
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)  # Very compact spacing
        
        title = QLabel("LABORATORY RESULT ENTRY")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: white; margin-bottom: 2px;")
        
        self.test_info = QLabel("Loading test information...")
        self.test_info.setStyleSheet("font-size: 11px; color: #e0f2fe;")
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.test_info)
        header_frame.setLayout(header_layout)
        self.layout.addWidget(header_frame)

    def create_patient_section(self):
        """Compact patient information section"""
        patient_group = QGroupBox("Patient Information")
        patient_layout = QGridLayout()
        patient_layout.setSpacing(4)  # Compact spacing
        patient_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins

        # Patient details in a grid
        self.patient_name = QLabel("Loading...")
        self.patient_age = QLabel("Loading...")
        self.patient_gender = QLabel("Loading...")
        self.patient_pid = QLabel("Loading...")
        
        # Compact style for value labels
        value_style = "font-weight: 600; color: #1e293b; background-color: #f8fafc; padding: 4px 8px; border-radius: 3px; font-size: 11px;"
        self.patient_name.setStyleSheet(value_style)
        self.patient_age.setStyleSheet(value_style)
        self.patient_gender.setStyleSheet(value_style)
        self.patient_pid.setStyleSheet(value_style)

        # Compact labels
        label_style = "font-size: 11px; color: #64748b; font-weight: 500;"
        
        name_label = QLabel("Full Name:")
        name_label.setStyleSheet(label_style)
        age_label = QLabel("Age:")
        age_label.setStyleSheet(label_style)
        gender_label = QLabel("Gender:")
        gender_label.setStyleSheet(label_style)
        pid_label = QLabel("Patient ID:")
        pid_label.setStyleSheet(label_style)

        patient_layout.addWidget(name_label, 0, 0)
        patient_layout.addWidget(self.patient_name, 0, 1)
        patient_layout.addWidget(age_label, 0, 2)
        patient_layout.addWidget(self.patient_age, 0, 3)
        patient_layout.addWidget(gender_label, 1, 0)
        patient_layout.addWidget(self.patient_gender, 1, 1)
        patient_layout.addWidget(pid_label, 1, 2)
        patient_layout.addWidget(self.patient_pid, 1, 3)

        patient_group.setLayout(patient_layout)
        self.layout.addWidget(patient_group)

    def create_test_parameters_section(self):
        """Test parameters section - MAXIMIZED for visibility"""
        parameters_group = QGroupBox("Test Parameters & Results")
        parameters_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 4px;
                padding: 6px;
                background-color: #ffffff;
                font-weight: bold;
                color: #1e293b;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 6px;
                padding: 2px 6px;
                background-color: #f1f5f9;
                border-radius: 3px;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        parameters_layout = QVBoxLayout()
        parameters_layout.setSpacing(4)
        parameters_layout.setContentsMargins(4, 4, 4, 4)
        
        # Scroll area for dynamic form - MAXIMIZED
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background-color: #ffffff;
                min-height: 400px;
            }
        """)
        
        self.dynamic_widget = QWidget()
        self.dynamic_layout = QVBoxLayout()
        self.dynamic_layout.setSpacing(3)  # Very compact spacing between fields
        self.dynamic_layout.setContentsMargins(10, 8, 10, 8)  # Adequate margins for content
        self.dynamic_widget.setLayout(self.dynamic_layout)
        
        scroll.setWidget(self.dynamic_widget)
        parameters_layout.addWidget(scroll)
        parameters_group.setLayout(parameters_layout)
        self.layout.addWidget(parameters_group, stretch=1)  # Give this section maximum stretch

    def create_notes_section(self):
        """Compact notes section"""
        notes_group = QGroupBox("Clinical Notes")
        notes_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 4px;
                padding: 6px;
                background-color: #ffffff;
                font-weight: bold;
                color: #1e293b;
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                left: 6px;
                padding: 2px 6px;
                background-color: #f1f5f9;
                border-radius: 3px;
                color: #475569;
                font-weight: 600;
                font-size: 12px;
            }
        """)
        notes_layout = QVBoxLayout()
        notes_layout.setSpacing(4)
        notes_layout.setContentsMargins(4, 4, 4, 4)
        
        self.notes = QTextEdit()
        self.notes.setPlaceholderText(
            "Enter clinical observations, interpretation, or additional notes..."
        )
        self.notes.setToolTip("Add detailed clinical notes and interpretation for the test results")
        self.notes.setMaximumHeight(80)  # Compact height for notes
        self.notes.setAccessibleName("Clinical Notes")
        
        notes_layout.addWidget(self.notes)
        notes_group.setLayout(notes_layout)
        self.layout.addWidget(notes_group)

    def create_action_buttons(self):
        """Compact action buttons section"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Progress bar - very compact
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(4)
        self.layout.addWidget(self.progress)

        # Button box
        button_box = QDialogButtonBox()
        button_box.setStyleSheet("QPushButton { padding: 6px 12px; font-size: 11px; }")
        
        self.save_btn = QPushButton("💾 Save Results")
        self.save_btn.setIcon(QIcon("icons/save_icon.png"))
        self.save_btn.setToolTip("Save the laboratory results (Ctrl+S)")
        self.save_btn.setShortcut("Ctrl+S")
        self.save_btn.clicked.connect(self._save_result)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setIcon(QIcon("icons/cancel_icon.png"))
        self.cancel_btn.setToolTip("Cancel and close without saving (Esc)")
        self.cancel_btn.setShortcut("Esc")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.preview_btn = QPushButton("👁️ Preview")
        self.preview_btn.setIcon(QIcon("icons/preview_icon.png"))
        self.preview_btn.setToolTip("Preview the results before saving")
        self.preview_btn.clicked.connect(self.preview_results)
        
        button_box.addButton(self.save_btn, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(self.preview_btn, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(self.cancel_btn, QDialogButtonBox.ButtonRole.RejectRole)
        
        button_layout.addWidget(button_box)
        self.layout.addLayout(button_layout)

    def preview_results(self):
        """Preview the results before saving"""
        data = self.collect_form_data()
        if not data:
            QMessageBox.warning(self, "No Data", "Please enter some results before previewing.")
            return
            
        preview_text = "RESULTS PREVIEW\n"
        preview_text += "=" * 50 + "\n\n"
        
        for field_name, value in data.items():
            preview_text += f"{field_name}: {value}\n"
            
        preview_text += f"\nNotes: {self.notes.toPlainText()[:100]}..." if self.notes.toPlainText() else "\nNotes: None"
        
        QMessageBox.information(self, "Results Preview", preview_text)

    # Calculation methods (unchanged)
    def calculate_globulin(self, values):
        try:
            total_protein = float(values.get('Total Protein', 0))
            albumin = float(values.get('Albumin', 0))
            return total_protein - albumin
        except (ValueError, TypeError):
            return None

    def calculate_ag_ratio(self, values):
        try:
            albumin = float(values.get('Albumin', 0))
            globulin = float(values.get('Globulin', 0))
            if globulin != 0:
                return albumin / globulin
            return None
        except (ValueError, TypeError):
            return None

    def calculate_ldl(self, values):
        try:
            total_chol = float(values.get('Serum Cholesterol', 0))
            hdl = float(values.get('HDL Cholesterol', 0))
            triglycerides = float(values.get('Serum Triglycerides', 0))
            ldl = total_chol - hdl - (triglycerides / 5)
            return 0 if ldl < 0 else ldl
        except (ValueError, TypeError):
            return None

    def calculate_vldl(self, values):
        try:
            triglycerides = float(values.get('Serum Triglycerides', 0))
            vldl = triglycerides / 5
            return 0 if vldl < 0 else vldl
        except (ValueError, TypeError):
            return None

    def calculate_non_hdl(self, values):
        try:
            total_chol = float(values.get('Total Cholesterol', 0))
            hdl = float(values.get('HDL Cholesterol', 0))
            non_hdl = total_chol - hdl
            return 0 if non_hdl < 0 else non_hdl
        except (ValueError, TypeError):
            return None

    def calculate_tc_hdl_ratio(self, values):
        try:
            total_chol = float(values.get('Total Cholesterol', 0))
            hdl = float(values.get('HDL Cholesterol', 0))
            return total_chol / hdl if hdl != 0 else None
        except (ValueError, TypeError):
            return None

    def calculate_ldl_hdl_ratio(self, values):
        try:
            ldl = float(values.get('LDL Cholesterol', 0))
            hdl = float(values.get('HDL Cholesterol', 0))
            return ldl / hdl if hdl != 0 else None
        except (ValueError, TypeError):
            return None

    def setup_calculation_dependencies(self, test_code, fields):
        self.calculation_dependencies.clear()
        self.calculated_fields.clear()
        if test_code in self.calculation_map:
            calculations = self.calculation_map[test_code]
            for calc_field, calc_func in calculations.items():
                if calc_func == self.calculate_globulin:
                    deps = ['Total Protein', 'Albumin']
                elif calc_func == self.calculate_ag_ratio:
                    deps = ['Albumin', 'Globulin']
                elif calc_func == self.calculate_ldl:
                    deps = ['Serum Cholesterol', 'HDL Cholesterol', 'Serum Triglycerides']
                elif calc_func == self.calculate_vldl:
                    deps = ['Serum Triglycerides']
                elif calc_func == self.calculate_non_hdl:
                    deps = ['Total Cholesterol', 'HDL Cholesterol']
                elif calc_func == self.calculate_tc_hdl_ratio:
                    deps = ['Total Cholesterol', 'HDL Cholesterol']
                elif calc_func == self.calculate_ldl_hdl_ratio:
                    deps = ['LDL Cholesterol', 'HDL Cholesterol']
                else:
                    deps = []
                self.calculation_dependencies[calc_field] = {'dependencies': deps, 'function': calc_func}
                self.calculated_fields[calc_field] = True

    def on_any_field_changed(self):
        """Real-time recalculation on any input change."""
        self.perform_calculations()

    def perform_calculations(self):
        current_values = {}
        for field_widget in self.field_widgets:
            value = field_widget.get_value()
            if value:
                try:
                    current_values[field_widget.field_name] = float(value) if field_widget.field_type in ['float', 'int'] else value
                except:
                    pass
        
        for field_name, info in self.calculation_dependencies.items():
            deps = info['dependencies']
            if all(d in current_values for d in deps):
                result = info['function'](current_values)
                if result is not None:
                    # Find widget and update
                    for field_widget in self.field_widgets:
                        if field_widget.field_name == field_name:
                            field_widget.set_value(f"{result:.2f}" if isinstance(result, float) else str(result))
                            field_widget.set_calculated(True)
                            break

    def load_order_details(self):
        session = Session()
        try:
            order = session.query(Order).options(
                joinedload(Order.patient), joinedload(Order.test)
            ).filter(Order.id == self.order_id).first()
            if not order:
                QMessageBox.critical(self, "Error", "Order not found.")
                self.reject()
                return

            # Patient info
            patient = order.patient
            self.patient_name.setText(patient.decrypted_name if patient else "N/A")
            self.patient_age.setText(str(patient.age) if patient and patient.age else "N/A")
            self.patient_gender.setText(patient.gender.capitalize() if patient and patient.gender else "N/A")
            self.patient_pid.setText(patient.pid if patient and patient.pid else "N/A")

            # Test template
            test = order.test
            self.test_info.setText(f"Test: {test.name} | Department: {test.department} | Code: {test.code}")
            
            template = json.loads(test.template) if test.template else []
            self.field_widgets = []

            # Clear existing widgets
            for i in reversed(range(self.dynamic_layout.count())):
                widget = self.dynamic_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            # Add field widgets
            for field in template:
                name = field['name']
                ftype = field['type']
                unit = field.get('unit', '')
                ref = field.get('reference', '')
                
                field_widget = ProfessionalFieldWidget(name, ftype, unit, ref)
                
                # Connect text change signal for calculations
                if ftype in ['float', 'int']:
                    field_widget.input_field.textChanged.connect(self.on_any_field_changed)
                
                self.dynamic_layout.addWidget(field_widget)
                self.field_widgets.append(field_widget)

            # Load existing result if editing
            if self.editing_result_id:
                result = session.query(Result).filter_by(id=self.editing_result_id).first()
                if result:
                    data = json.loads(result.results) if result.results else {}
                    notes = result.notes or ""
                    self.notes.setPlainText(notes)
                    for field_widget in self.field_widgets:
                        if field_widget.field_name in data:
                            field_widget.set_value(data[field_widget.field_name])

            # Setup calculations
            self.setup_calculation_dependencies(test.code, template)
            # Perform initial calculations
            self.perform_calculations()

        except Exception as e:
            logger.error(f"Error loading order: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load order: {str(e)}")
        finally:
            session.close()

    def collect_form_data(self):
        """Collect and validate form data"""
        data = {}
        self.validation_errors = []
        
        for field_widget in self.field_widgets:
            value = field_widget.get_value()
            if value:
                try:
                    if field_widget.field_type == 'float':
                        data[field_widget.field_name] = float(value)
                    elif field_widget.field_type == 'int':
                        data[field_widget.field_name] = int(value)
                    else:
                        data[field_widget.field_name] = value
                except ValueError:
                    self.validation_errors.append(f"'{field_widget.field_name}' must be a valid number")
        
        return data

    def _save_result(self):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate progress
        
        data = self.collect_form_data()
        
        if self.validation_errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(self.validation_errors))
            self.validation_errors.clear()
            self.progress.setVisible(False)
            return

        notes = self.notes.toPlainText().strip()
        session = Session()
        try:
            if self.editing_result_id:
                result = session.query(Result).filter_by(id=self.editing_result_id).first()
                if result:
                    result.results = json.dumps(data)  # ✅ FIXED: Use 'results' instead of 'data'
                    result.notes = notes
                    session.commit()
                    QMessageBox.information(self, "Success", "Result updated successfully!")
            else:
                result = Result(
                    order_id=self.order_id,
                    results=json.dumps(data),  # ✅ FIXED: Use 'results' instead of 'data'
                    notes=notes,
                    result_date=datetime.now()
                )
                session.add(result)
                # Update order status
                order = session.query(Order).filter_by(id=self.order_id).first()
                if order:
                    order.status = 'Completed'
                session.commit()
                QMessageBox.information(self, "Success", "Result saved successfully!")
            self.accept()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving result: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save result: {str(e)}")
        finally:
            session.close()
            self.progress.setVisible(False)


# The rest of the ResultTab class remains unchanged from the previous version
class ResultTab(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_patient_id = None
        self.editing_result_id = None
        self.current_user_id = 1  # Replace with actual user ID from login
        self._init_ui()
        self.load_tests()  # Load test list
        self.load_orders()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Laboratory Results Management")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #1e293b;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Search & Filters
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by patient, PID, test name...")
        self.search_input.setToolTip("Enter search terms to find patients (e.g., patient name, PID). Press Enter to search.")
        self.search_input.setAccessibleName("Search Patients Input")
        self.search_input.textChanged.connect(self.load_orders)
        search_layout.addWidget(self.search_input)

        self.patient_search_btn = QPushButton("🔍 Search Patient")
        self.patient_search_btn.setIcon(QIcon("icons/search_icon.png"))
        self.patient_search_btn.setToolTip("Open patient search dialog (Ctrl+P)")
        self.patient_search_btn.setAccessibleName("Patient Search Button")
        self.patient_search_btn.setShortcut("Ctrl+P")
        self.patient_search_btn.clicked.connect(self.open_patient_search)
        search_layout.addWidget(self.patient_search_btn)

        self.clear_patient_btn = QPushButton("🗑️ Clear Patient")
        self.clear_patient_btn.setIcon(QIcon("icons/clear_icon.png"))
        self.clear_patient_btn.setToolTip("Clear selected patient filter")
        self.clear_patient_btn.clicked.connect(self.clear_patient_filter)
        search_layout.addWidget(self.clear_patient_btn)

        main_layout.addLayout(search_layout)

        filter_group = QGroupBox("Advanced Filters")
        filter_group.setStyleSheet("QGroupBox { background-color: #ffffff; border-radius: 8px; font-weight: bold; }")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # Status
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "Completed"])
        self.status_filter.setToolTip("Filter orders by status")
        self.status_filter.setAccessibleName("Status Filter")
        self.status_filter.currentTextChanged.connect(self.load_orders)
        filter_layout.addWidget(self.status_filter)

        # Department
        filter_layout.addWidget(QLabel("Department:"))
        self.department_filter = QComboBox()
        self.department_filter.addItems(["All", "Biochemistry", "Hematology", "Microbiology", "Immunology", "Clinical Pathology"])
        self.department_filter.setToolTip("Filter orders by department")
        self.department_filter.setAccessibleName("Department Filter")
        self.department_filter.currentTextChanged.connect(self.load_orders)
        filter_layout.addWidget(self.department_filter)

        # Test Filter
        filter_layout.addWidget(QLabel("Test:"))
        self.test_filter = QComboBox()
        self.test_filter.addItem("All")  # Will be populated in load_tests()
        self.test_filter.setToolTip("Filter orders by test name")
        self.test_filter.setAccessibleName("Test Filter")
        self.test_filter.currentTextChanged.connect(self.load_orders)
        filter_layout.addWidget(self.test_filter)

        # Date
        filter_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.start_date.setToolTip("Set the start date for order filtering")
        self.start_date.setAccessibleName("Start Date Filter")
        self.start_date.dateChanged.connect(self.load_orders)
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("End Date:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setToolTip("Set the end date for order filtering")
        self.end_date.setAccessibleName("End Date Filter")
        self.end_date.dateChanged.connect(self.load_orders)
        filter_layout.addWidget(self.end_date)

        self.search_btn = QPushButton("🔍 Apply Filters")
        self.search_btn.setIcon(QIcon("icons/search_icon.png"))
        self.search_btn.setToolTip("Search orders with current filters (Ctrl+R)")
        self.search_btn.setAccessibleName("Search Button")
        self.search_btn.setShortcut("Ctrl+R")
        self.search_btn.clicked.connect(self.load_orders)
        filter_layout.addWidget(self.search_btn)
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #1f2937; font-size: 13px; font-weight: 500;")
        self.status_label.setAccessibleName("Status Label")
        main_layout.addWidget(self.status_label)

        self.orders_table = TestTable([], ["ID", "Patient Name", "PID", "Test Name", "Department", "Status", "Order Date"])
        self.orders_table.table.setSortingEnabled(True)
        self.orders_table.table.itemDoubleClicked.connect(self.open_result_entry)
        self.orders_table.table.itemSelectionChanged.connect(self.enable_buttons)
        self.orders_table.setMinimumHeight(400)
        self.orders_table.setAccessibleName("Orders Table")
        main_layout.addWidget(self.orders_table, stretch=1)

        button_layout = QGridLayout()
        button_layout.setSpacing(10)
        self.enter_result_btn = QPushButton("➕ Enter Result")
        self.enter_result_btn.setIcon(QIcon("icons/add_icon.png"))
        self.enter_result_btn.setToolTip("Enter result for selected order (Ctrl+E)")
        self.enter_result_btn.setAccessibleName("Enter Result Button")
        self.enter_result_btn.setShortcut("Ctrl+E")
        self.enter_result_btn.clicked.connect(self.open_result_entry)
        button_layout.addWidget(self.enter_result_btn, 0, 0)
        self.edit_btn = QPushButton("✏️ Edit Result")
        self.edit_btn.setIcon(QIcon("icons/edit_icon.png"))
        self.edit_btn.setToolTip("Edit the selected result (Ctrl+Shift+E)")
        self.edit_btn.setAccessibleName("Edit Button")
        self.edit_btn.setShortcut("Ctrl+Shift+E")
        self.edit_btn.clicked.connect(self.edit_result)
        button_layout.addWidget(self.edit_btn, 0, 1)
        self.delete_btn = QPushButton("🗑️ Delete Result")
        self.delete_btn.setIcon(QIcon("icons/delete_icon.png"))
        self.delete_btn.setToolTip("Delete the selected result (Ctrl+Del)")
        self.delete_btn.setAccessibleName("Delete Button")
        self.delete_btn.setShortcut("Ctrl+Del")
        self.delete_btn.clicked.connect(self.delete_result)
        button_layout.addWidget(self.delete_btn, 0, 2)
        main_layout.addLayout(button_layout)

        self.enter_result_btn.setEnabled(False)
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

        self.setLayout(main_layout)

    def load_tests(self):
        """Load all test names into the test filter dropdown."""
        session = Session()
        try:
            tests = session.query(Test).order_by(Test.name).all()
            self.test_filter.clear()
            self.test_filter.addItem("All")
            for test in tests:
                self.test_filter.addItem(test.name, test.id)
        except Exception as e:
            logger.error(f"Error loading tests: {e}")
        finally:
            session.close()

    def open_patient_search(self):
        dialog = PatientSearchDialog(self)
        if dialog.exec():
            patient_id = dialog.get_selected_patient_id()
            if patient_id:
                self.selected_patient_id = patient_id
                self.search_input.clear()
                self.load_orders()
                self.status_label.setText(f"Filtered to orders for patient ID {patient_id}")
                self.status_label.setStyleSheet("color: #16a34a; font-weight: bold;")

    def clear_patient_filter(self):
        self.selected_patient_id = None
        self.search_input.clear()
        self.load_orders()
        self.status_label.setText("Patient filter cleared")
        self.status_label.setStyleSheet("color: #16a34a; font-weight: bold;")

    def load_orders(self):
        session = Session()
        try:
            query = session.query(Order).join(Order.patient).outerjoin(Order.test)

            # === APPLY FILTERS ===
            status = self.status_filter.currentText()
            if status == "Pending":
                # Use more flexible filtering for pending status
                query = query.filter(Order.status.in_(['Pending', 'pending', 'PENDING']))
            elif status == "Completed":
                # Use more flexible filtering for completed status
                query = query.filter(Order.status.in_(['Completed', 'completed', 'COMPLETED']))

            department = self.department_filter.currentText()
            if department != "All":
                query = query.filter(Test.department == department)

            test_name = self.test_filter.currentText()
            if test_name != "All":
                query = query.filter(Test.name == test_name)

            start = self.start_date.date().toPyDate()
            end = self.end_date.date().toPyDate()
            start_dt = datetime.combine(start, datetime.min.time())
            end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time()) - timedelta(microseconds=1)
            query = query.filter(Order.order_date.between(start_dt, end_dt))

            if self.selected_patient_id:
                query = query.filter(Order.patient_id == self.selected_patient_id)

            # === ADD SEARCH FILTER ===
            search_text = self.search_input.text().strip()
            if search_text:
                # Search in patient name, PID, or test name
                query = query.join(Patient).join(Test).filter(
                    cast(Order.id, String).ilike(f'%{search_text}%') |
                    Patient.pid.ilike(f'%{search_text}%') |
                    Test.name.ilike(f'%{search_text}%')
                )

            # === EXECUTE QUERY ===
            orders = query.order_by(Order.order_date.desc()).all()

            # === DEBUG: Check what orders are being fetched ===
            print(f"DEBUG: Found {len(orders)} orders")
            for order in orders:
                print(f"  Order {order.id}: Status='{order.status}', Patient={order.patient_id}, Test={order.test_id}")

            # === POPULATE TABLE ===
            self._populate_orders_table(orders)

            # === STATUS UPDATE ===
            count = len(orders)
            filters = []
            if status != "All": filters.append(status)
            if department != "All": filters.append(department)
            if test_name != "All": filters.append(f"'{test_name}'")
            filter_text = f" ({', '.join(filters)})" if filters else ""
            patient_text = f" (Patient ID: {self.selected_patient_id})" if self.selected_patient_id else ""

            self.status_label.setText(f"Loaded {count} order(s){patient_text}{filter_text}")
            self.status_label.setStyleSheet("color: #16a34a; font-weight: bold;")

        except Exception as e:
            logger.error(f"Error loading orders: {e}")
            self.status_label.setText(f"Error: {str(e)[:60]}")
            self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
            QMessageBox.critical(self, "Database Error", f"Failed to load orders:\n{e}")
        finally:
            session.close()

    def _populate_orders_table(self, orders):
        data = []
        for order in orders:
            # === ULTRA-SAFE PATIENT NAME ===
            try:
                patient_name = order.patient.decrypted_name
            except Exception as e:
                logger.warning(f"Decryption failed for patient {order.patient_id}: {e}")
                patient_name = f"[Encrypted] PID-{order.patient_id}"

            # === SAFE FALLBACKS ===
            patient_pid = getattr(order.patient, 'pid', 'N/A') or 'N/A'
            test_name = getattr(order.test, 'name', 'Unknown Test')
            department = getattr(order.test, 'department', 'N/A')
            status = order.status or "Pending"
            order_date = order.order_date.strftime("%Y-%m-%d %H:%M") if order.order_date else "N/A"

            data.append((
                order.id,
                patient_name,
                patient_pid,
                test_name,
                department,
                status,
                order_date
            ))

        self.orders_table.update_data(data)
        print(f"DEBUG: Populated {len(data)} orders in table")  # Remove later

    def open_result_entry(self, item=None):
        selected_row = self.orders_table.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Warning", "Please select an order to enter results.")
            return
        order_id = int(self.orders_table.table.item(selected_row, 0).text())
        session = Session()
        try:
            has_result = session.query(Result).filter_by(order_id=order_id).first() is not None
            if has_result and not self.editing_result_id:
                reply = QMessageBox.question(
                    self, "Result Exists",
                    "This order already has a result. Do you want to edit it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.edit_result()
                    return
                else:
                    return
            dialog = ResultEntryDialog(self, order_id, self.editing_result_id)
            if dialog.exec():
                self.load_orders()
                self.clear_form()
        except Exception as e:
            logger.error(f"Error opening result entry: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open result entry: {str(e)}")
        finally:
            session.close()

    def edit_result(self):
        selected_row = self.orders_table.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Error", "Please select an order to edit")
            return
        order_id = int(self.orders_table.table.item(selected_row, 0).text())
        session = Session()
        try:
            result = session.query(Result).filter_by(order_id=order_id).first()
            if result:
                self.editing_result_id = result.id
                dialog = ResultEntryDialog(self, order_id, self.editing_result_id)
                if dialog.exec():
                    self.load_orders()
                    self.clear_form()
            else:
                QMessageBox.warning(self, "Warning", "No result found for this order. Please enter a result first.")
        except Exception as e:
            logger.error(f"Failed to load result: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load result: {str(e)}")
        finally:
            session.close()

    def delete_result(self):
        selected_row = self.orders_table.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Error", "Please select an order to delete result")
            return
        order_id = int(self.orders_table.table.item(selected_row, 0).text())
        test_name = self.orders_table.table.item(selected_row, 3).text()
        session = Session()
        try:
            result = session.query(Result).filter_by(order_id=order_id).first()
            if not result:
                QMessageBox.warning(self, "Warning", "No result found for this order.")
                return
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the result for {test_name}?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                user_id = self.current_user_id
                if isinstance(user_id, User):
                    user_id = user_id.id
                if not isinstance(user_id, int):
                    raise ValueError(f"Invalid user_id type: {type(user_id).__name__}")

                user = session.query(User).get(user_id)
                if not user:
                    raise ValueError(f"User ID {user_id} not found")
                order = session.query(Order).get(order_id)
                order.status = 'Pending'
                session.add(AuditLog(
                    user_id=user_id,
                    action='delete_result',
                    entity_id=result.id,
                    entity_type='Result',
                    details=json.dumps({'test': test_name})
                ))
                session.delete(result)
                session.commit()
                QMessageBox.information(self, "Success", "Result deleted successfully!")
                self.load_orders()
                self.clear_form()
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting result: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete result: {str(e)}")
        finally:
            session.close()

    def enable_buttons(self):
        selected = self.orders_table.table.currentRow() >= 0
        self.enter_result_btn.setEnabled(selected)
        if selected:
            order_id = int(self.orders_table.table.item(self.orders_table.table.currentRow(), 0).text())
            session = Session()
            try:
                result = session.query(Result).filter_by(order_id=order_id).first()
                self.edit_btn.setEnabled(result is not None)
                self.delete_btn.setEnabled(result is not None)
            except Exception as e:
                logger.error(f"Error checking result: {e}")
                self.edit_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)
            finally:
                session.close()
        else:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

    def clear_form(self):
        self.editing_result_id = None