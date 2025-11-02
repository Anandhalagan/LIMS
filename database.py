# database.py
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_app_data_dir():
    """Get the application data directory for both dev and packaged mode"""
    if getattr(sys, 'frozen', False):
        # Running in packaged mode - use user data directory
        if sys.platform == 'win32':
            app_data = Path(os.environ['APPDATA']) / 'ClinicalLabSoftware'
        elif sys.platform == 'darwin':
            app_data = Path.home() / 'Library' / 'Application Support' / 'ClinicalLabSoftware'
        else:
            app_data = Path.home() / '.local' / 'share' / 'ClinicalLabSoftware'
        
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data
    else:
        # Development mode - use current directory
        return Path(__file__).parent

def get_database_path():
    """Get the database path"""
    app_data_dir = get_app_data_dir()
    return app_data_dir / 'lab.db'

def get_key_file_path():
    """Get the encryption key file path"""
    app_data_dir = get_app_data_dir()
    return app_data_dir / 'encryption_key.key'

# Database setup using dynamic paths
DB_PATH = get_database_path()
KEY_FILE = get_key_file_path()

print(f"Database path: {DB_PATH}")  # Debug info
print(f"Key file path: {KEY_FILE}")  # Debug info

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

# Fixed Encryption key management
def load_or_create_key():
    """Load existing key or create a new one with proper encoding"""
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, 'rb') as f:
                key = f.read()
            # Test if the key is valid
            test_fernet = Fernet(key)
            test_fernet.encrypt(b"test")
            return key
        except Exception as e:
            print(f"Existing key invalid, generating new one: {e}")
            os.remove(KEY_FILE)  # Remove corrupted key file
    
    # Generate new key
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    print("New encryption key generated")
    return key

KEY = load_or_create_key()
cipher = Fernet(KEY)

def init_db():
    Base.metadata.create_all(engine)

def encrypt_data(data):
    """Encrypt data with proper error handling"""
    if not data:
        return ""
    try:
        if isinstance(data, str):
            return cipher.encrypt(data.encode('utf-8')).decode('utf-8')
        else:
            return cipher.encrypt(str(data).encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"Encryption error: {e}")
        return data  # Return original data if encryption fails

def decrypt_data(encrypted_data):
    """Decrypt data with proper error handling"""
    if not encrypted_data:
        return ""
    
    # Check if data is already decrypted (not starting with gAAAA)
    if not encrypted_data.startswith('gAAAA'):
        return encrypted_data
    
    try:
        decrypted = cipher.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
        return decrypted
    except Exception as e:
        print(f"Decryption error for data '{encrypted_data[:50]}...': {e}")
        # Try to return the original data if it might not be encrypted
        try:
            # If it's valid UTF-8 text, return it
            encrypted_data.encode('utf-8').decode('utf-8')
            return encrypted_data
        except:
            return "Decryption Failed"