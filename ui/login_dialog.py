# login_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from database import Session
from models import User

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LOGIN")
        self.layout = QVBoxLayout()
        self.setGeometry(600, 200, 400, 300)

        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)

        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)
        self.layout.addWidget(self.login_btn)

        self.setLayout(self.layout)
        self.current_user = None
        print("LoginDialog initialized")  # Debug

        self.setStyleSheet("""
            QWidget {
                background-color: #e6f3ff;
                color: #000000;
                font-family: 'Calibri', Arial, sans-serif;
                font-size: 12px;
            }
            QLabel {
                font-size: 14px;
            }
            QLineEdit {
                border: 2px solid #b3d9ff;
                border-radius: 10px;
                padding: 8px;
                background-color: #ffffff;
                color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #6272a4;
            }
            QPushButton {
                background-color: #007bff;
                border-radius: 12px;
                padding: 10px;
                font-size: 14px;
                color: white;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        print(f"Login attempt: username={username}, password={password}")  # Debug
        session = Session()
        try:
            user = session.query(User).filter_by(username=username, password=password).first()
            if user:
                print(f"User found: {user.username}, role={user.role}")  # Debug
                self.current_user = user
                self.accept()
            else:
                print("No user found with provided credentials")  # Debug
                QMessageBox.warning(self, "Error", "Invalid username or password")
        except Exception as e:
            print(f"Login error: {e}")  # Debug
            QMessageBox.critical(self, "Error", f"Login failed: {str(e)}")
        finally:
            session.close()