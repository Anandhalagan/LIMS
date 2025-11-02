from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QMessageBox, QHeaderView, QLabel
)
from PyQt6.QtCore import Qt
from database import Session
from models import ArchiveEntry, User, Patient, Order, Result, OrderComment
import json


class ArchiveTab(QWidget):
    """Admin-only tab to view archive entries and restore or purge them."""
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        self.setup_ui()
        self.load_archives()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        header = QLabel("Archive Viewer")
        header.setStyleSheet("font-size:16px; font-weight:bold;")
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Entity", "Entity ID", "Deleted By", "Deleted At", "Summary"])
        self.table.hideColumn(0)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.restore_btn = QPushButton("Restore")
        self.restore_btn.clicked.connect(self.restore_selected)
        btn_layout.addWidget(self.restore_btn)

        self.purge_btn = QPushButton("Permanently Delete")
        self.purge_btn.clicked.connect(self.purge_selected)
        btn_layout.addWidget(self.purge_btn)

        layout.addLayout(btn_layout)

    def load_archives(self):
        session = Session()
        try:
            entries = session.query(ArchiveEntry).order_by(ArchiveEntry.deleted_at.desc()).all()
            self.table.setRowCount(len(entries))
            for row, e in enumerate(entries):
                self.table.setItem(row, 0, QTableWidgetItem(str(e.id)))
                self.table.setItem(row, 1, QTableWidgetItem(e.entity_type))
                self.table.setItem(row, 2, QTableWidgetItem(str(e.entity_id)))
                deleted_by = str(e.deleted_by) if e.deleted_by else "-"
                self.table.setItem(row, 3, QTableWidgetItem(deleted_by))
                self.table.setItem(row, 4, QTableWidgetItem(e.deleted_at.isoformat() if e.deleted_at else "-"))
                # Summary: small preview of patient name or JSON first keys
                try:
                    data = e.data
                    summary = ""
                    if isinstance(data, dict) and 'patient' in data:
                        pname = data['patient'].get('name')
                        summary = pname if pname else json.dumps(list(data.keys()))
                    else:
                        summary = json.dumps(list(data.keys()))
                except Exception:
                    summary = "(unable to preview)"
                self.table.setItem(row, 5, QTableWidgetItem(str(summary)))
        finally:
            session.close()

    def _selected_entry_id(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Error", "Please select an archive entry.")
            return None
        row = rows[0].row()
        return int(self.table.item(row, 0).text())

    def restore_selected(self):
        entry_id = self._selected_entry_id()
        if entry_id is None:
            return
        session = Session()
        try:
            entry = session.query(ArchiveEntry).filter_by(id=entry_id).first()
            if not entry:
                QMessageBox.warning(self, "Error", "Archive entry not found.")
                return

            if entry.entity_type != 'patient':
                QMessageBox.information(self, "Not supported", "Restore only supports patient archives for now.")
                return

            # Confirm
            reply = QMessageBox.question(self, "Restore", "Restore this patient from archive? This will create new records.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

            # Perform restore: create new Patient and related orders/results/comments
            payload = entry.data
            patient_data = payload.get('patient')
            if not patient_data:
                QMessageBox.critical(self, "Error", "Archive payload missing patient data.")
                return

            # Create patient object from archived column values
            new_patient = Patient()
            for col, val in patient_data.items():
                if col == 'id':
                    continue
                try:
                    setattr(new_patient, col, val)
                except Exception:
                    pass

            session.add(new_patient)
            session.flush()  # get new_patient.id

            # Restore orders
            for order_obj in payload.get('orders', []):
                order = Order()
                for k, v in order_obj.items():
                    if k in ('id', 'result', 'comments'):
                        continue
                    try:
                        setattr(order, k, v)
                    except Exception:
                        pass
                order.patient_id = new_patient.id
                session.add(order)
                session.flush()

                # restore result
                if 'result' in order_obj and order_obj['result']:
                    r = order_obj['result']
                    res = Result()
                    for k, v in r.items():
                        if k == 'id':
                            continue
                        try:
                            setattr(res, k, v)
                        except Exception:
                            pass
                    res.order_id = order.id
                    session.add(res)

                # restore comments
                for c in order_obj.get('comments', []):
                    com = OrderComment()
                    for k, v in c.items():
                        if k == 'id':
                            continue
                        try:
                            setattr(com, k, v)
                        except Exception:
                            pass
                    com.order_id = order.id
                    session.add(com)

            session.commit()
            QMessageBox.information(self, "Success", "Patient restored (new records created).")
            self.load_archives()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Restore failed: {e}")
        finally:
            session.close()

    def purge_selected(self):
        entry_id = self._selected_entry_id()
        if entry_id is None:
            return
        reply = QMessageBox.question(self, "Purge", "Permanently delete this archive entry? This cannot be undone.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        session = Session()
        try:
            entry = session.query(ArchiveEntry).filter_by(id=entry_id).first()
            if not entry:
                QMessageBox.warning(self, "Error", "Archive entry not found.")
                return
            session.delete(entry)
            session.commit()
            QMessageBox.information(self, "Deleted", "Archive entry deleted permanently.")
            self.load_archives()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Purge failed: {e}")
        finally:
            session.close()
