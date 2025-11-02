from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QSpinBox, QComboBox, QPushButton, QMessageBox
from database import Session
from models import Patient, generate_pid, cipher

class PatientForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout()

        self.title = QComboBox()
        self.title.addItems(["Mr.", "Mrs.", "Miss", "Baby"])
        self.pid = QLineEdit()
        self.pid.setPlaceholderText("Leave blank to auto-generate (e.g., ABC00001)")
        self.name = QLineEdit()
        self.age = QSpinBox()
        self.age.setRange(0, 150)
        self.gender = QComboBox()
        self.gender.addItems(['Male', 'Female', 'Other'])
        self.contact = QLineEdit()
        self.address = QLineEdit()

        layout.addRow("Title:", self.title)
        layout.addRow("PID:", self.pid)
        layout.addRow("Name:", self.name)
        layout.addRow("Age:", self.age)
        layout.addRow("Gender:", self.gender)
        layout.addRow("Contact:", self.contact)
        layout.addRow("Address:", self.address)

        self.save_btn = QPushButton("Save Patient")
        self.save_btn.clicked.connect(self.save_patient)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def save_patient(self):
        if not self.name.text():
            QMessageBox.warning(self, "Error", "Name is required")
            return

        session = Session()
        patient = Patient()

        pid = self.pid.text().strip()
        if not pid:
            pid = generate_pid()
            while session.query(Patient).filter_by(pid=pid).first():
                pid = generate_pid()
        elif not (len(pid) == 8 and pid[:3].isalpha() and pid[3:].isdigit() and int(pid[3:]) < 100000):
            QMessageBox.warning(self, "Error", "PID must be 8 characters, start with 3 letters, and end with 5 digits (e.g., ABC00001)")
            session.close()
            return
        patient.pid = pid

        patient.title = cipher.encrypt(self.title.currentText().encode()).decode() if self.title.currentText() else None
        patient.name = cipher.encrypt(self.name.text().encode()).decode()
        patient.age = self.age.value()
        patient.gender = self.gender.currentText()
        patient.contact = cipher.encrypt(self.contact.text().encode()).decode() if self.contact.text() else None
        patient.address = cipher.encrypt(self.address.text().encode()).decode() if self.address.text() else None

        session.add(patient)
        try:
            session.commit()
            QMessageBox.information(self, "Success", f"Patient saved with PID: {pid}")
            self.clear_form()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save patient: {str(e)}")
        finally:
            session.close()

    def clear_form(self):
        self.title.setCurrentIndex(0)
        self.pid.clear()
        self.name.clear()
        self.age.setValue(0)
        self.gender.setCurrentIndex(0)
        self.contact.clear()
        self.address.clear()
