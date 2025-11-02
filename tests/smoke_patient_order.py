import os
import sys
import time

# Run headless
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication

# Ensure project root is on sys.path so local packages (ui, models) can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.main_window import MainWindow
from database import Session
from models import Patient, cipher, generate_pid

class DummyUser:
    def __init__(self):
        self.username = 'smoke'
        self.role = 'admin'
        self.id = 1


def create_patient_directly():
    with Session() as session:
        pid = generate_pid()
        # ensure uniqueness
        while session.query(Patient).filter_by(pid=pid).first():
            pid = generate_pid()
        p = Patient()
        p.pid = pid
        p.title = cipher.encrypt(b'Mr.').decode()
        p.name = cipher.encrypt(b'Smoke Test').decode()
        p.age = 30
        p.gender = 'Male'
        p.contact = cipher.encrypt(b'9999999999').decode()
        p.address = cipher.encrypt(b'Test Address').decode()
        session.add(p)
        session.commit()
        return p.id


def main():
    app = QApplication(sys.argv)
    user = DummyUser()
    mw = MainWindow(user)

    # get tabs
    patient_tab = mw.tab_instances.get('patientTab')
    order_tab = mw.tab_instances.get('orderTab')
    assert patient_tab is not None, 'patientTab not found'
    assert order_tab is not None, 'orderTab not found'

    # create a DB patient and emit signal
    pid = create_patient_directly()

    # Emit signal as if saved
    patient_tab.patient_open_in_order.emit(pid)

    # Allow event loop to process
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    # Determine order tab index
    idx = None
    for i, (_, _, _, obj_name, _) in enumerate(mw.TAB_CONFIG):
        if obj_name == 'orderTab':
            idx = i
            break
    assert idx is not None, 'orderTab index not found'

    if mw.tabs.currentIndex() != idx:
        print('SMOKE TEST FAILED: Orders tab not selected')
        sys.exit(2)

    # Verify patient combo selection
    current = order_tab.patient_combo.currentData()
    if current != pid:
        print(f'SMOKE TEST FAILED: patient not selected in order tab (expected {pid}, got {current})')
        sys.exit(3)

    print('SMOKE TEST PASSED')
    sys.exit(0)


if __name__ == '__main__':
    main()
