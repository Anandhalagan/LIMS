import os
import sys
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# Ensure project root is on sys.path so imports like `database` resolve when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from database import Session
from models import Patient, Test, Order, cipher
import tempfile
import ui.tabs.order as order_mod

# Create QApplication if needed
app = QApplication.instance() or QApplication(sys.argv)

# Monkeypatch UI/modal side-effects to keep test headless
QMessageBox.information = lambda *a, **k: None
QMessageBox.warning = lambda *a, **k: None
QMessageBox.critical = lambda *a, **k: None
QMessageBox.question = lambda *a, **k: QMessageBox.StandardButton.Yes

# Prevent opening external files
os.startfile = lambda *a, **k: None

# Monkeypatch generate_invoice to write a harmless temp file and return its path
def fake_generate_invoice(order_ids):
    tf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    tf.write(b'PDF-DUMMY')
    tf.close()
    return tf.name

order_mod.generate_invoice = fake_generate_invoice

# Monkeypatch PaymentDialog to auto-accept and return simple data
from ui.tabs.order import PaymentDialog
PaymentDialog.exec = lambda self: True
PaymentDialog.get_data = lambda self: (0.0, "Cash:0.00")


def main():
    # Ensure there are at least 1-2 tests available
    with Session() as s:
        tests = s.query(Test).limit(2).all()
        if not tests:
            print("No tests available in DB, cannot run fast_checkable_order test.")
            sys.exit(2)
        test_ids = [t.id for t in tests]

    # Create a temporary patient
    with Session() as s:
        enc_name = cipher.encrypt(b"Fast Test User").decode()
        enc_contact = cipher.encrypt(b"9990001111").decode()
        p = Patient(name=enc_name, contact=enc_contact, pid=f"FT{int(os.getpid())}")
        s.add(p)
        s.commit()
        patient_id = p.id

    try:
        tab = order_mod.OrderTab()
        # reload combos to ensure the new patient appears
        tab.load_combos()
        idx = tab.patient_combo.findData(patient_id)
        if idx < 0:
            print("Created patient not found in combo; failing test")
            sys.exit(3)
        tab.patient_combo.setCurrentIndex(idx)
        tab.referring_physician.setText("Dr. Fast")

        # Use TestSelectionDialog to check first two items
        dlg = order_mod.TestSelectionDialog(tab, [])
        # Ensure tests are loaded
        if dlg.test_list.count() == 0:
            print("Test list empty in dialog; failing test")
            sys.exit(4)
        # Check up to 2 tests
        for i in range(min(2, dlg.test_list.count())):
            itm = dlg.test_list.item(i)
            itm.setCheckState(Qt.CheckState.Checked)
        selected = dlg.get_selected_test_ids()
        if not selected:
            print("No tests selected via dialog; failing test")
            sys.exit(5)

        tab.selected_test_ids = selected
        tab.update_selected_tests_summary()

        # Count orders before
        with Session() as s:
            before = s.query(Order).count()

        # Place order (PaymentDialog is patched to accept)
        tab.place_order()

        # Count orders after
        with Session() as s:
            after = s.query(Order).count()

        created = after - before
        expected = len(selected)
        if created != expected:
            print(f"Expected {expected} orders to be created, but {created} were created.")
            sys.exit(6)

        print("FAST TEST PASSED")
        sys.exit(0)

    finally:
        # Cleanup: delete created orders and patient
        try:
            with Session() as s:
                s.query(Order).filter(Order.patient_id == patient_id).delete()
                p = s.get(Patient, patient_id)
                if p:
                    s.delete(p)
                s.commit()
        except Exception:
            pass


if __name__ == '__main__':
    main()
