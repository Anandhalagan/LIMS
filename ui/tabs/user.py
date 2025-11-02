from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, 
    QHBoxLayout, QLabel, QTabWidget, QDialog, QLineEdit
)
from PyQt6.QtCore import Qt
from database import Session
from models import User, ReferringPhysician, Location

class EditUserDialog(QDialog):
    def __init__(self, username, role, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit User")
        layout = QVBoxLayout()
        self.username_edit = QLineEdit(username)
        self.role_edit = QLineEdit(role)
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_edit)
        layout.addWidget(QLabel("Role:"))
        layout.addWidget(self.role_edit)
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        return self.username_edit.text(), self.role_edit.text()

class UserTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()

        # Main Title
        self.title_label = QLabel("User Management")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.title_label)

        # Tab Widget for Sub-Tabs
        self.tab_widget = QTabWidget()
        self.create_user_tab()
        self.create_physician_tab()
        self.create_location_tab()
        self.layout.addWidget(self.tab_widget)

        self.load_all_data()
        self.setLayout(self.layout)

    def create_user_tab(self):
        user_widget = QWidget()
        user_layout = QVBoxLayout()

        # Title
        title1 = QLabel("Add User")
        title1.setStyleSheet("font-size: 14px; font-weight: bold;")
        user_layout.addWidget(title1)

        # User Table
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Role"])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        user_layout.addWidget(self.user_table)

        # Buttons
        button_layout1 = QHBoxLayout()
        self.add_user_btn = QPushButton("Add User")
        self.add_user_btn.clicked.connect(self.add_user)
        self.edit_user_btn = QPushButton("Edit User")
        self.edit_user_btn.clicked.connect(self.edit_user)
        self.delete_user_btn = QPushButton("Delete User")
        self.delete_user_btn.clicked.connect(self.delete_user)
        button_layout1.addWidget(self.add_user_btn)
        button_layout1.addWidget(self.edit_user_btn)
        button_layout1.addWidget(self.delete_user_btn)
        user_layout.addLayout(button_layout1)

        user_widget.setLayout(user_layout)
        self.tab_widget.addTab(user_widget, "Add User")

    def create_physician_tab(self):
        physician_widget = QWidget()
        physician_layout = QVBoxLayout()

        # Title
        title2 = QLabel("Add Referring Physician")
        title2.setStyleSheet("font-size: 14px; font-weight: bold;")
        physician_layout.addWidget(title2)

        # Physician Table
        self.physician_table = QTableWidget()
        self.physician_table.setColumnCount(3)
        self.physician_table.setHorizontalHeaderLabels(["ID", "Name", "Specialty"])
        self.physician_table.horizontalHeader().setStretchLastSection(True)
        physician_layout.addWidget(self.physician_table)

        # Buttons
        button_layout2 = QHBoxLayout()
        self.add_physician_btn = QPushButton("Add Referring Physician")
        self.add_physician_btn.clicked.connect(self.add_referring_physician)
        self.edit_physician_btn = QPushButton("Edit Referring Physician")
        self.edit_physician_btn.clicked.connect(self.edit_referring_physician)
        self.delete_physician_btn = QPushButton("Delete Referring Physician")
        self.delete_physician_btn.clicked.connect(self.delete_referring_physician)
        button_layout2.addWidget(self.add_physician_btn)
        button_layout2.addWidget(self.edit_physician_btn)
        button_layout2.addWidget(self.delete_physician_btn)
        physician_layout.addLayout(button_layout2)

        physician_widget.setLayout(physician_layout)
        self.tab_widget.addTab(physician_widget, "Add Referring Physician")

    def create_location_tab(self):
        location_widget = QWidget()
        location_layout = QVBoxLayout()

        # Title
        title3 = QLabel("Add Location")
        title3.setStyleSheet("font-size: 14px; font-weight: bold;")
        location_layout.addWidget(title3)

        # Location Table
        self.location_table = QTableWidget()
        self.location_table.setColumnCount(3)
        self.location_table.setHorizontalHeaderLabels(["ID", "Name", "Address"])
        self.location_table.horizontalHeader().setStretchLastSection(True)
        location_layout.addWidget(self.location_table)

        # Buttons
        button_layout3 = QHBoxLayout()
        self.add_location_btn = QPushButton("Add Location")
        self.add_location_btn.clicked.connect(self.add_location)
        self.edit_location_btn = QPushButton("Edit Location")
        self.edit_location_btn.clicked.connect(self.edit_location)
        self.delete_location_btn = QPushButton("Delete Location")
        self.delete_location_btn.clicked.connect(self.delete_location)
        button_layout3.addWidget(self.add_location_btn)
        button_layout3.addWidget(self.edit_location_btn)
        button_layout3.addWidget(self.delete_location_btn)
        location_layout.addLayout(button_layout3)

        location_widget.setLayout(location_layout)
        self.tab_widget.addTab(location_widget, "Add Location")

    def load_all_data(self):
        self.load_users()
        self.load_physicians()
        self.load_locations()

    def load_users(self):
        session = Session()
        users = session.query(User).all()
        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            item_id = QTableWidgetItem(str(user.id))
            item_username = QTableWidgetItem(user.username)
            item_role = QTableWidgetItem(user.role)
            # Optionally enable inline editing: item_username.setFlags(item_username.flags() | Qt.ItemFlag.ItemIsEditable)
            self.user_table.setItem(row, 0, item_id)
            self.user_table.setItem(row, 1, item_username)
            self.user_table.setItem(row, 2, item_role)
        session.close()

    def load_physicians(self):
        session = Session()
        physicians = session.query(ReferringPhysician).all()
        self.physician_table.setRowCount(len(physicians))
        for row, phys in enumerate(physicians):
            item_id = QTableWidgetItem(str(phys.id))
            item_name = QTableWidgetItem(phys.decrypted_name)
            item_specialty = QTableWidgetItem(phys.specialty or "")
            item_specialty.setFlags(item_specialty.flags() | Qt.ItemFlag.ItemIsEditable)
            self.physician_table.setItem(row, 0, item_id)
            self.physician_table.setItem(row, 1, item_name)
            self.physician_table.setItem(row, 2, item_specialty)
        session.close()

    def load_locations(self):
        session = Session()
        locations = session.query(Location).all()
        self.location_table.setRowCount(len(locations))
        for row, loc in enumerate(locations):
            item_id = QTableWidgetItem(str(loc.id))
            item_name = QTableWidgetItem(loc.name)
            item_address = QTableWidgetItem(loc.address or "")
            item_name.setFlags(item_name.flags() | Qt.ItemFlag.ItemIsEditable)
            item_address.setFlags(item_address.flags() | Qt.ItemFlag.ItemIsEditable)
            self.location_table.setItem(row, 0, item_id)
            self.location_table.setItem(row, 1, item_name)
            self.location_table.setItem(row, 2, item_address)
        session.close()

    def add_user(self):
        print("Add user clicked")

    def edit_user(self):
        row = self.user_table.currentRow()
        if row < 0:
            print("No user row selected")
            return
        user_id = int(self.user_table.item(row, 0).text())
        username = self.user_table.item(row, 1).text()
        role = self.user_table.item(row, 2).text()
        print(f"Edit user {user_id}: username={username}, role={role}")

    def delete_user(self):
        print("Delete user clicked")

    def add_referring_physician(self):
        print("Add referring physician clicked")

    def edit_referring_physician(self):
        row = self.physician_table.currentRow()
        if row < 0:
            print("No physician row selected")
            return
        phys_id = int(self.physician_table.item(row, 0).text())
        name = self.physician_table.item(row, 1).text()
        specialty = self.physician_table.item(row, 2).text()
        print(f"Edit physician {phys_id}: name={name}, specialty={specialty}")

    def delete_referring_physician(self):
        print("Delete referring physician clicked")

    def add_location(self):
        print("Add location clicked")

    def edit_location(self):
        row = self.location_table.currentRow()
        if row < 0:
            print("No location row selected")
            return
        loc_id = int(self.location_table.item(row, 0).text())
        name = self.location_table.item(row, 1).text()
        address = self.location_table.item(row, 2).text()
        print(f"Edit location {loc_id}: name={name}, address={address}")

    def delete_location(self):
        print("Delete location clicked")
