# AI Agent Instructions for LIMS Codebase

## Project Overview
This is a Clinical Laboratory Information Management System (LIMS) built with Python and PyQt6. The application provides a GUI interface for managing patients, tests, orders, results, and user data in a medical laboratory setting.

## Key Architecture Components

### Database Layer
- Uses SQLAlchemy ORM with SQLite backend (`database.py`)
- Data encryption for sensitive fields using Fernet symmetric encryption
- Database files stored in platform-specific app data directories
- Core models: Patient, Test, Order, Result, User (`models.py`)

### UI Layer
- PyQt6-based desktop application with modular tab structure (`ui/` directory)
- Main tabs: Dashboard, Patients, Orders, Tests, Results, Users, Reports
- Premium UI features including themes, animations, and glass morphism effects
- Role-based access control (admin vs user permissions)

### File Organization
```
main.py              # Application entry point
database.py          # Database configuration and encryption
models.py            # SQLAlchemy models
ui/                  # UI components
├── main_window.py   # Main application window
├── login_dialog.py  # Authentication dialog
├── tabs/           # Individual tab implementations
└── components/     # Reusable UI components
```

## Common Development Tasks

### Adding a New Feature
1. If database changes needed:
   - Add model in `models.py`
   - Call `init_db()` to create tables
2. For UI changes:
   - Add new tab class in `ui/tabs/` if needed
   - Register in `MainWindow.TAB_CONFIG` for navigation
3. Update role permissions in `TAB_CONFIG` array

### Database Operations
- Always use SQLAlchemy session management:
```python
session = Session()
try:
    # database operations
    session.commit()
finally:
    session.close()
```
- Use encryption for sensitive data:
```python
from database import encrypt_data, decrypt_data
encrypted = encrypt_data(sensitive_info)
decrypted = decrypt_data(encrypted_data)
```

### Packaging
- PyInstaller configuration in `ClinicalLabSoftware.spec`
- Build commands:
  ```powershell
  # Development build
  python -m PyInstaller ClinicalLabSoftware.spec
  # Production build
  .\build_final_complete.ps1
  ```

## UI Patterns
- Use `GlassFrame` for container styling with transparency effects
- Tab implementations should inherit from appropriate Qt widget class
- Theme switching handled via `PREMIUM_LIGHT_STYLESHEET`/`PREMIUM_DARK_STYLESHEET`

## Project-Specific Conventions
1. Patient IDs follow format: TRY00001, TRY00002, etc.
2. All database timestamps stored in UTC
3. Role hierarchy: admin > user
4. Tab access controlled by user role
5. Auto-logout after 30 minutes of inactivity

## Integration Points
1. PDF Report Generation: `reports/pdf_generator.py`
2. Data Export: CSV export functionality in `MainWindow`
3. Encryption key storage: Application data directory
4. Session analytics tracking in `MainWindow`

## Common Issues & Solutions
1. Missing PyQt6 plugins:
   ```python
   os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
   ```
2. Database access errors:
   - Check app data directory permissions
   - Verify encryption key exists and is valid
3. UI scaling on different resolutions:
   - Use dynamic layout management
   - Check `resizeEvent` handlers

## Testing
- Add tests under appropriate module directories
- Test both UI interactions and database operations
- Verify encryption/decryption for sensitive data
- Test role-based access controls