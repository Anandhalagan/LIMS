# main.py
import os
import sys

# Add the project root directory to Python path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Qt6 compatibility fixes
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
os.environ["QT_API"] = "pyqt6"

# Add this before any Qt imports
try:
    from PyQt6 import QtCore, QtWidgets
    print("PyQt6 imported successfully")
except ImportError as e:
    print(f"PyQt6 import failed: {e}")
    sys.exit(1)

# Rest of your imports
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QFontDatabase
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from database import Session, Base, engine, init_db
from models import User, Result, Order, Patient

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def main():
    # Set up paths for packaged mode
    if getattr(sys, 'frozen', False):
        # Add the temp directory to Python path for dynamic imports
        sys.path.append(sys._MEIPASS)
    
    try:
        # Initialize database
        init_db()
        
        # Create default admin user if needed
        session = Session()
        try:
            if not session.query(User).filter_by(username="admin").first():
                default_user = User(username="admin", password="admin", role="admin")
                session.add(default_user)
                session.commit()
                print("Default user created: admin/admin")
            else:
                print("Admin user already exists")
        except Exception as e:
            print(f"Error creating default user: {e}")
            session.rollback()
        finally:
            session.close()
    except Exception as e:
        print(f"Database initialization error: {e}")
        sys.exit(1)

    # Create application
    app = QApplication(sys.argv)
    
    # Register Inter fonts after QApplication creation
    def register_inter_fonts():
        """Load only a minimal set of Inter fonts required by the UI."""
        try:
            fonts_dir = resource_path("fonts")
            if not os.path.isdir(fonts_dir):
                print(f"Fonts directory not found: {fonts_dir}")
                return

            # Minimal set of required Inter fonts (18pt versions)
            required = ["Inter_18pt-Regular.ttf", "Inter_18pt-Bold.ttf"]
            loaded = 0
            for fn in required:
                path = os.path.join(fonts_dir, fn)
                if not os.path.exists(path):
                    print(f"Required font not found: {path}")
                    continue
                try:
                    print(f"Loading font: {fn}")
                    res = QFontDatabase.addApplicationFont(path)
                    if res != -1:
                        loaded += 1
                        print(f"Successfully loaded font: {fn}")
                except Exception as e:
                    print(f"Failed to load font {fn}: {e}")

            print(f"Loaded {loaded} Inter fonts from {fonts_dir}")
        except Exception as e:
            print(f"Error registering Inter fonts: {e}")

    register_inter_fonts()
    
    # Set application properties
    app.setApplicationName("Clinical Laboratory Software")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ClinicalLab")
    
    # Show login dialog
    login = LoginDialog()
    print("Showing LoginDialog")
    result = login.exec()
    print(f"LoginDialog result: {result}")
    
    if result == QDialog.DialogCode.Accepted:
        try:
            print(f"Opening MainWindow for user: {login.current_user.username}")
            window = MainWindow(login.current_user)
            window.show()
            print("MainWindow shown")
            sys.exit(app.exec())
        except Exception as e:
            print(f"MainWindow initialization error: {e}")
            sys.exit(1)
    else:
        print("Login dialog not accepted")
        sys.exit(0)

if __name__ == "__main__":
    main()