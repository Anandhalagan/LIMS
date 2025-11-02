import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QPushButton, QGroupBox,
    QMessageBox, QCheckBox, QTextEdit, QScrollArea, QStatusBar,
    QFileDialog, QFrame, QApplication, QHeaderView,
    QDialog
)
from PyQt6.QtGui import QIcon, QFont, QDoubleValidator, QShortcut, QKeySequence
from PyQt6.QtCore import Qt
from ui.components.test_table import TestTable
from database import Session
from models import Test


class TestDialog(QDialog):
    def __init__(self, parent=None, test_data=None):
        super().__init__(parent)
        self.test_data = test_data
        self.setWindowTitle("Add New Test" if not test_data else "Edit Test")
        self.setModal(True)
        self.setMinimumSize(900, 700)
        
        self._init_ui()
        if test_data:
            self._populate_fields()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Test Details Group
        details_group = QGroupBox("Test Details")
        grid_layout = QGridLayout()
        
        grid_layout.addWidget(QLabel("Test Code*:"), 0, 0)
        self.code = QLineEdit()
        self.code.setPlaceholderText("Enter unique test code")
        grid_layout.addWidget(self.code, 0, 1)
        
        grid_layout.addWidget(QLabel("Test Name*:"), 1, 0)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Enter test name")
        grid_layout.addWidget(self.name, 1, 1)
        
        grid_layout.addWidget(QLabel("Department:"), 2, 0)
        self.department = QComboBox()
        self.department.addItems([
            'Biochemistry', 'Hematology', 'Microbiology',
            'Immunology', 'Serology', 'Clinical Pathology', 'Other'
        ])
        grid_layout.addWidget(self.department, 2, 1)
        
        grid_layout.addWidget(QLabel("Rate (INR):"), 3, 0)
        self.rate_inr = QLineEdit()
        self.rate_inr.setPlaceholderText("0.00")
        self.rate_inr.setValidator(QDoubleValidator(0, 99999, 2))
        grid_layout.addWidget(self.rate_inr, 3, 1)
        
        grid_layout.addWidget(QLabel("Notes:"), 4, 0)
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("Additional notes about the test")
        grid_layout.addWidget(self.notes, 4, 1)
        
        details_group.setLayout(grid_layout)
        layout.addWidget(details_group)
        
        # Template Fields Group
        template_group = QGroupBox("Template Fields")
        template_layout = QVBoxLayout()
        
        # Scroll area for table
        template_scroll = QScrollArea()
        template_scroll.setWidgetResizable(True)
        template_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.field_table = QTableWidget(0, 11)
        self.field_table.setHorizontalHeaderLabels([
            "Field Name*", "Type*", "Unit", "Male Ref", "Female Ref",
            "Age-Based", "Child Ref", "Adult Ref", "Decimals", "Interpretation", "Method"
        ])
        self.field_table.verticalHeader().setVisible(False)
        self.field_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.field_table.horizontalHeader().setStretchLastSection(True)
        self.field_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.field_table)
        
        template_scroll.setWidget(table_container)
        template_layout.addWidget(template_scroll)
        
        # Field buttons
        btn_layout = QHBoxLayout()
        self.add_field_btn = QPushButton("Add Field")
        self.add_field_btn.clicked.connect(self.add_field)
        btn_layout.addWidget(self.add_field_btn)
        
        self.remove_field_btn = QPushButton("Remove Field")
        self.remove_field_btn.clicked.connect(self.remove_field)
        btn_layout.addWidget(self.remove_field_btn)
        
        btn_layout.addStretch()
        
        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.clicked.connect(self.move_field_up)
        btn_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.clicked.connect(self.move_field_down)
        btn_layout.addWidget(self.move_down_btn)
        
        template_layout.addLayout(btn_layout)
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        if not self.test_data:
            self.add_field()
    
    def _populate_fields(self):
        if not self.test_data:
            return
            
        self.code.setText(self.test_data.get('code', ''))
        self.name.setText(self.test_data.get('name', ''))
        self.department.setCurrentText(self.test_data.get('department', ''))
        self.rate_inr.setText(str(self.test_data.get('rate_inr', '')))
        self.notes.setText(self.test_data.get('notes', ''))
        
        template = self.test_data.get('template', [])
        for field in template:
            self.add_field()
            row = self.field_table.rowCount() - 1
            self.field_table.item(row, 0).setText(field.get('name', ''))
            self.field_table.cellWidget(row, 1).setCurrentText(field.get('type', 'float'))
            self.field_table.item(row, 2).setText(field.get('unit', ''))
            
            ref = field.get('reference', {})
            if isinstance(ref, dict):
                self.field_table.item(row, 3).setText(ref.get('male', ''))
                self.field_table.item(row, 4).setText(ref.get('female', ''))
                
                age = ref.get('age_based', {})
                chk = self.field_table.cellWidget(row, 5)
                chk.setChecked(bool(age))
                self.toggle_age_fields(row, chk.isChecked())
                
                self.field_table.item(row, 6).setText(age.get('child', ''))
                self.field_table.item(row, 7).setText(age.get('adult', ''))
            
            if field.get('type') == 'float' and 'decimals' in field:
                self.field_table.cellWidget(row, 8).setCurrentText(str(field['decimals']))
                
            self.field_table.item(row, 9).setText(field.get('interpretation', ''))
            self.field_table.item(row, 10).setText(field.get('method', ''))
    
    def add_field(self):
        r = self.field_table.rowCount()
        self.field_table.insertRow(r)
        self.field_table.setItem(r, 0, QTableWidgetItem(""))
        
        combo = QComboBox()
        combo.addItems(["float", "int", "string"])
        combo.setToolTip("Data type")
        self.field_table.setCellWidget(r, 1, combo)
        
        for c in [2, 3, 4, 6, 7, 9, 10]:
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable)
            self.field_table.setItem(r, c, item)
        
        age_chk = QCheckBox()
        age_chk.setToolTip("Age-based ranges")
        age_chk.stateChanged.connect(lambda s, row=r: self.toggle_age_fields(row, s))
        self.field_table.setCellWidget(r, 5, age_chk)
        
        dec = QComboBox()
        dec.addItems(["0", "1", "2", "3"])
        dec.setToolTip("Decimal places")
        self.field_table.setCellWidget(r, 8, dec)
        
        self.field_table.scrollToBottom()
    
    def toggle_age_fields(self, row, state):
        for col in (6, 7):
            item = self.field_table.item(row, col)
            if item:
                flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable if state else Qt.ItemFlag.NoItemFlags
                item.setFlags(flags)
                if not state:
                    item.setText("")
    
    def remove_field(self):
        r = self.field_table.currentRow()
        if r >= 0:
            self.field_table.removeRow(r)
    
    def move_field_up(self):
        r = self.field_table.currentRow()
        if r > 0:
            self._swap_rows(r, r-1)
            self.field_table.setCurrentCell(r-1, 0)
    
    def move_field_down(self):
        r = self.field_table.currentRow()
        if r < self.field_table.rowCount()-1:
            self._swap_rows(r, r+1)
            self.field_table.setCurrentCell(r+1, 0)
    
    def _swap_rows(self, r1, r2):
        for c in range(self.field_table.columnCount()):
            w1 = self.field_table.cellWidget(r1, c)
            w2 = self.field_table.cellWidget(r2, c)
            if w1:
                self.field_table.removeCellWidget(r1, c)
                self.field_table.setCellWidget(r2, c, w1)
            if w2:
                self.field_table.removeCellWidget(r2, c)
                self.field_table.setCellWidget(r1, c, w2)
            
            i1 = self.field_table.takeItem(r1, c)
            i2 = self.field_table.takeItem(r2, c)
            if i1:
                self.field_table.setItem(r2, c, i1)
            if i2:
                self.field_table.setItem(r1, c, i2)
    
    def get_test_data(self):
        code = self.code.text().strip()
        name = self.name.text().strip()
        department = self.department.currentText()
        rate_inr = float(self.rate_inr.text()) if self.rate_inr.text() else 0.0
        notes = self.notes.toPlainText().strip()
        fields = []
        
        for row in range(self.field_table.rowCount()):
            fname = self.field_table.item(row, 0).text().strip()
            ftype = self.field_table.cellWidget(row, 1).currentText()
            if not fname or not ftype:
                continue
                
            fld = {
                "name": fname, 
                "type": ftype, 
                "unit": self.field_table.item(row, 2).text()
            }
            
            male = self.field_table.item(row, 3).text()
            female = self.field_table.item(row, 4).text()
            if male or female:
                fld["reference"] = {"male": male, "female": female}
                
            if self.field_table.cellWidget(row, 5).isChecked():
                fld.setdefault("reference", {})
                fld["reference"]["age_based"] = {
                    "child": self.field_table.item(row, 6).text(),
                    "adult": self.field_table.item(row, 7).text()
                }
                
            if ftype == "float":
                fld["decimals"] = int(self.field_table.cellWidget(row, 8).currentText())
                
            interp = self.field_table.item(row, 9).text()
            if interp:
                fld["interpretation"] = interp
            method = self.field_table.item(row, 10).text()
            if method:
                fld["method"] = method
                
            fields.append(fld)
        
        return {
            "code": code,
            "name": name,
            "department": department,
            "rate_inr": rate_inr,
            "notes": notes,
            "template": fields
        }
    
    def validate_form(self):
        if not self.code.text().strip():
            QMessageBox.warning(self, "Validation Error", "Test code is required")
            return False
        if not self.name.text().strip():
            QMessageBox.warning(self, "Validation Error", "Test name is required")
            return False
        if self.field_table.rowCount() == 0:
            QMessageBox.warning(self, "Validation Error", "At least one template field is required")
            return False
        for row in range(self.field_table.rowCount()):
            if not self.field_table.item(row, 0).text().strip():
                QMessageBox.warning(self, "Validation Error", f"Field name is required for row {row+1}")
                return False
        return True
    
    def accept(self):
        if self.validate_form():
            super().accept()


class TestTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_test_id = None
        self.is_dark_mode = False
        self._init_ui()
        self.load_tests()
        self._init_shortcuts()

    def _init_ui(self):
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Test Management")
        title_font = QFont("Calibri", 16)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.theme_btn = QPushButton()
        self.theme_btn.setIcon(QIcon("icons/theme.png"))
        self.theme_btn.setToolTip("Toggle Dark/Light Mode")
        self.theme_btn.setFixedSize(40, 40)
        self.theme_btn.setStyleSheet("QPushButton { border-radius: 20px; }")
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)
        main_layout.addLayout(header_layout)

        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        buttons = [
            ("Add Test", self.add_test, "Add New Test (Ctrl+N)", "#28a745"),  # Green
            ("Edit Test", self.edit_test, "Edit Selected Test (Ctrl+E)", "#007bff"),  # Blue
            ("Delete Test", self.delete_test, "Delete Selected Test (Del)", "#dc3545"),  # Red
            ("Refresh", self.load_tests, "Refresh Tests (F5)", "#6c757d"),  # Gray
            ("Export Test", self.export_test, "Export Selected Test (Ctrl+S)", "#17a2b8"),  # Info
            ("Import Tests", self.import_tests, "Import Test(s) (Ctrl+O)", "#fd7e14"),  # Orange
            ("Export All Tests", self.export_all_tests, "Export All Tests", "#8e44ad"),  # Purple
        ]
        
        for name, slot, tip, color in buttons:
            btn = QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-weight: bold;
                    min-width: 100px;
                }}
                QPushButton:hover {{
                    background-color: {self._adjust_color(color, 110)};
                }}
                QPushButton:pressed {{
                    background-color: {self._adjust_color(color, 90)};
                }}
                QPushButton:disabled {{
                    background-color: #6c757d;
                    color: #adb5bd;
                }}
            """)
            btn.clicked.connect(slot)
            btn.setToolTip(tip)
            actions_layout.addWidget(btn)
            # Store reference using clean attribute name
            attr_name = name.lower().replace(' ', '_') + "_btn"
            setattr(self, attr_name, btn)
        
        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by code, name, or department...")
        self.search_input.textChanged.connect(self._filter_tests)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # Table
        table_scroll = QScrollArea()
        table_scroll.setWidgetResizable(True)
        table_scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.table = TestTable([], ["ID", "Code", "Name", "Department", "Rate (INR)", "Template", "Notes"])
        self.table.table.setAlternatingRowColors(True)
        self.table.table.itemSelectionChanged.connect(self.on_test_selected)
        table_scroll.setWidget(self.table)
        main_layout.addWidget(table_scroll, 1)

        # Status
        self.status = QStatusBar()
        self.status.showMessage("Ready")
        main_layout.addWidget(self.status)

        main_scroll.setWidget(container)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(main_scroll)

        self._apply_stylesheet()

    def _adjust_color(self, color, factor):
        """Adjust color brightness by factor (percentage)"""
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r = min(255, int(r * factor / 100))
        g = min(255, int(g * factor / 100))
        b = min(255, int(b * factor / 100))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _apply_stylesheet(self):
        if self.is_dark_mode:
            self.setStyleSheet("""
                QWidget { background-color: #2d3748; color: #e2e8f0; font-family: 'Segoe UI', Arial, sans-serif; }
                QGroupBox { font-weight: bold; border: 1px solid #4a5568; border-radius: 6px; margin-top: 12px; padding-top: 12px; background-color: #2d3748; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QLineEdit, QTextEdit, QComboBox { background-color: #4a5568; color: #e2e8f0; border: 1px solid #718096; border-radius: 4px; padding: 6px; selection-background-color: #4299e1; }
                QPushButton { background-color: #4a5568; color: #e2e8f0; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
                QPushButton:hover { background-color: #5a6579; }
                QPushButton:pressed { background-color: #3a4558; }
                QPushButton:disabled { background-color: #4a5568; color: #718096; }
                QTableWidget { background-color: #2d3748; alternate-background-color: #4a5568; color: #e2e8f0; gridline-color: #4a5568; border: 1px solid #4a5568; }
                QHeaderView::section { background-color: #4a5568; color: #e2e8f0; padding: 4px; border: none; }
                QScrollArea { border: none; background-color: #2d3748; }
                QScrollBar:vertical { border: none; background: #2d3748; width: 10px; margin: 0px; }
                QScrollBar::handle:vertical { background: #4a5568; min-height: 20px; border-radius: 5px; }
                QScrollBar:horizontal { border: none; background: #2d3748; height: 10px; margin: 0px; }
                QScrollBar::handle:horizontal { background: #4a5568; min-width: 20px; border-radius: 5px; }
                QStatusBar { background-color: #2d3748; color: #e2e8f0; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background-color: #f7fafc; color: #2d3748; font-family: 'Segoe UI', Arial, sans-serif; }
                QGroupBox { font-weight: bold; border: 1px solid #cbd5e0; border-radius: 6px; margin-top: 12px; padding-top: 12px; background-color: #ffffff; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QLineEdit, QTextEdit, QComboBox { background-color: #ffffff; color: #2d3748; border: 1px solid #cbd5e0; border-radius: 4px; padding: 6px; selection-background-color: #4299e1; }
                QPushButton { background-color: #e2e8f0; color: #2d3748; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
                QPushButton:hover { background-color: #cbd5e0; }
                QPushButton:pressed { background-color: #a0aec0; }
                QPushButton:disabled { background-color: #e2e8f0; color: #a0aec0; }
                QTableWidget { background-color: #ffffff; alternate-background-color: #f7fafc; color: #2d3748; gridline-color: #e2e8f0; border: 1px solid #cbd5e0; }
                QHeaderView::section { background-color: #edf2f7; color: #2d3748; padding: 4px; border: none; }
                QScrollArea { border: none; background-color: #f7fafc; }
                QScrollBar:vertical { border: none; background: #f7fafc; width: 10px; margin: 0px; }
                QScrollBar::handle:vertical { background: #cbd5e0; min-height: 20px; border-radius: 5px; }
                QScrollBar:horizontal { border: none; background: #f7fafc; height: 10px; margin: 0px; }
                QScrollBar::handle:horizontal { background: #cbd5e0; min-width: 20px; border-radius: 5px; }
                QStatusBar { background-color: #edf2f7; color: #2d3748; }
            """)

    def _toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self._apply_stylesheet()
        mode = "Dark" if self.is_dark_mode else "Light"
        self.status.showMessage(f"{mode} mode activated", 3000)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_test)
        QShortcut(QKeySequence("Ctrl+E"), self, self.edit_test)
        QShortcut(QKeySequence("F5"), self, self.load_tests)
        QShortcut(QKeySequence("Delete"), self, self.delete_test)
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_test)
        QShortcut(QKeySequence("Ctrl+O"), self, self.import_tests)

    def add_test(self):
        dialog = TestDialog(self)
        if dialog.exec():
            test_data = dialog.get_test_data()
            self.save_test(test_data)

    def edit_test(self):
        sel = self.table.table.selectedItems()
        if not sel or len(sel) < 7:
            QMessageBox.warning(self, "Error", "Please select a test to edit.")
            return
        row = self.table.table.currentRow()
        test_id = int(self.table.table.item(row, 0).text())
        session = Session()
        try:
            test = session.query(Test).filter_by(id=test_id).first()
            if test:
                test_data = {
                    'id': test.id, 'code': test.code, 'name': test.name,
                    'department': test.department, 'rate_inr': test.rate_inr,
                    'notes': test.notes, 'template': json.loads(test.template) if test.template else []
                }
                dialog = TestDialog(self, test_data)
                if dialog.exec():
                    updated_data = dialog.get_test_data()
                    self.update_test(test_id, updated_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load test: {str(e)}")
        finally:
            session.close()

    def save_test(self, test_data):
        code = test_data['code']
        name = test_data['name']
        department = test_data['department']
        rate_inr = test_data['rate_inr']
        notes = test_data['notes']
        fields = test_data['template']

        if not code or not name or not fields:
            QMessageBox.warning(self, "Error", "Test code, name, and at least one field are required")
            return

        session = Session()
        try:
            if session.query(Test).filter_by(code=code).first():
                QMessageBox.warning(self, "Error", "Test code already exists")
                return
            test = Test(code=code, name=name, department=department, rate_inr=rate_inr, template=json.dumps(fields), notes=notes)
            session.add(test)
            session.commit()
            QMessageBox.information(self, "Success", "Test added successfully")
            self.load_tests()
            self.status.showMessage("Test saved", 2000)
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save test: {str(e)}")
        finally:
            session.close()

    def update_test(self, test_id, test_data):
        code = test_data['code']
        name = test_data['name']
        department = test_data['department']
        rate_inr = test_data['rate_inr']
        notes = test_data['notes']
        fields = test_data['template']

        if not code or not name or not fields:
            QMessageBox.warning(self, "Error", "Test code, name, and at least one field are required")
            return

        session = Session()
        try:
            test = session.query(Test).filter_by(id=test_id).first()
            if test and test.code != code and session.query(Test).filter_by(code=code).first():
                QMessageBox.warning(self, "Error", "Test code already exists")
                return
            if test:
                test.code = code
                test.name = name
                test.department = department
                test.rate_inr = rate_inr
                test.template = json.dumps(fields)
                test.notes = notes
                session.commit()
                QMessageBox.information(self, "Success", "Test updated successfully")
                self.load_tests()
                self.status.showMessage("Test updated", 2000)
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update test: {str(e)}")
        finally:
            session.close()

    def delete_test(self):
        sel = self.table.table.selectedItems()
        if not sel or len(sel) < 7:
            QMessageBox.warning(self, "Error", "Please select a test to delete.")
            return
        row = self.table.table.currentRow()
        test_id = int(self.table.table.item(row, 0).text())
        reply = QMessageBox.question(self, "Confirm Delete", "Delete this test?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = Session()
            try:
                test = session.query(Test).filter_by(id=test_id).first()
                if test:
                    session.delete(test)
                    session.commit()
                    QMessageBox.information(self, "Success", "Test deleted!")
                    self.load_tests()
                    self.status.showMessage("Test deleted", 2000)
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")
            finally:
                session.close()

    def export_test(self):
        sel = self.table.table.selectedItems()
        if not sel or len(sel) < 7:
            QMessageBox.warning(self, "Error", "Select a test to export.")
            return
        row = self.table.table.currentRow()
        test_id = int(self.table.table.item(row, 0).text())
        session = Session()
        try:
            test = session.query(Test).filter_by(id=test_id).first()
            if not test:
                return
            export_data = {
                "code": test.code, "name": test.name, "department": test.department,
                "rate_inr": float(test.rate_inr), "notes": test.notes or "",
                "template": json.loads(test.template) if test.template else []
            }
            default_name = f"{test.code}_{test.name.replace(' ', '_')}.json"
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Test", default_name, "JSON Files (*.json)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Success", f"Exported:\n{file_path}")
                self.status.showMessage("Test exported", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
        finally:
            session.close()

    def import_tests(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Import Tests", "", "JSON Files (*.json)")
        if not file_paths:
            return
        
        session = Session()
        imported = skipped = 0
        errors = []
        
        try:
            for file_path in file_paths:
                try:
                    # Read and parse JSON file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read().strip()
                    
                    if not file_content:
                        errors.append(f"{os.path.basename(file_path)}: Empty file")
                        continue
                    
                    data = json.loads(file_content)
                    
                    # Handle both single test and array of tests
                    tests_to_import = []
                    if isinstance(data, list):
                        tests_to_import = data
                    elif isinstance(data, dict):
                        tests_to_import = [data]
                    else:
                        errors.append(f"{os.path.basename(file_path)}: Invalid format - expected object or array")
                        continue
                    
                    for test_data in tests_to_import:
                        # Validate required fields
                        required_fields = ["code", "name", "template"]
                        if not all(field in test_data for field in required_fields):
                            errors.append(f"{os.path.basename(file_path)}: Missing required fields (code, name, template)")
                            continue
                        
                        if not isinstance(test_data["template"], list):
                            errors.append(f"{os.path.basename(file_path)}: Template must be an array")
                            continue
                        
                        code = test_data["code"]
                        name = test_data["name"]
                        department = test_data.get("department", "Other")
                        rate_inr = float(test_data.get("rate_inr", 0))
                        notes = test_data.get("notes", "")
                        template = test_data["template"]
                        
                        # Check if test already exists
                        existing_test = session.query(Test).filter_by(code=code).first()
                        if existing_test:
                            skipped += 1
                            continue
                        
                        # Create new test
                        test = Test(
                            code=code,
                            name=name,
                            department=department,
                            rate_inr=rate_inr,
                            notes=notes,
                            template=json.dumps(template)
                        )
                        session.add(test)
                        imported += 1
                        
                except json.JSONDecodeError as e:
                    errors.append(f"{os.path.basename(file_path)}: Invalid JSON - {str(e)}")
                except Exception as e:
                    errors.append(f"{os.path.basename(file_path)}: {str(e)}")
            
            session.commit()
            
            # Show results
            msg = f"Imported: {imported}"
            if skipped:
                msg += f", Skipped (duplicates): {skipped}"
            if errors:
                error_msg = "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    error_msg += f"\n... and {len(errors) - 10} more errors"
                QMessageBox.warning(self, "Import Completed with Errors", f"{msg}\n\nErrors:\n{error_msg}")
            else:
                QMessageBox.information(self, "Success", msg)
            
            self.load_tests()
            self.status.showMessage(f"Imported {imported} test(s)", 3000)
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")
        finally:
            session.close()

    def export_all_tests(self):
        session = Session()
        try:
            tests = session.query(Test).all()
            if not tests:
                QMessageBox.information(self, "Info", "No tests to export.")
                return
            
            export_data = []
            for test in tests:
                export_data.append({
                    "code": test.code,
                    "name": test.name,
                    "department": test.department,
                    "rate_inr": float(test.rate_inr),
                    "notes": test.notes or "",
                    "template": json.loads(test.template) if test.template else []
                })
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export All Tests", 
                "all_tests_export.json", 
                "JSON Files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Success", f"Exported {len(tests)} tests to:\n{file_path}")
                self.status.showMessage("All tests exported", 2000)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")
        finally:
            session.close()

    def on_test_selected(self):
        sel = bool(self.table.table.selectedItems())
        self.edit_test_btn.setEnabled(sel)
        self.delete_test_btn.setEnabled(sel)
        self.export_test_btn.setEnabled(sel)

    def load_tests(self):
        session = Session()
        try:
            tests = session.query(Test).all()
            data = [(t.id, t.code, t.name, t.department, t.rate_inr, t.template, t.notes) for t in tests]
            self.table.update_data(data)
            self.status.showMessage(f"Loaded {len(tests)} tests", 2000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Load failed: {str(e)}")
        finally:
            session.close()

    def _filter_tests(self, text):
        self.table.filter(text)