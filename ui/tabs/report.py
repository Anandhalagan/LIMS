from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QDateEdit, QPushButton, QLabel, QMessageBox, QListWidget,
    QListWidgetItem, QComboBox, QLineEdit, QProgressBar, QDialog,
    QSpacerItem, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QIcon
from database import Session
from models import Order, Result, Patient
from reports.pdf_generator import generate_pdf_report
from sqlalchemy.orm import joinedload
import csv
from PyQt6.QtWidgets import QApplication

class ReportTab(QWidget):
    """Completely redesigned reporting GUI with better space-use, bulk
    selection, statistics panel, progress feedback, and export stubs."""

    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QWidget          { 
                background-color: #f4f6f9; 
                font-size: 14px; 
            }
            QGroupBox        { 
                border: 1px solid #e1e6eb; 
                border-radius: 6px;
                margin-top: 12px; 
                padding: 10px; 
            }
            QGroupBox::title  { 
                subcontrol-origin: margin;
                left: 10px; 
                padding: 2px 6px;
                font-weight: bold; 
                background: #f4f6f9; 
            }
            QLineEdit, QDateEdit, QComboBox {
                padding: 6px; 
                border: 1px solid #cfd7e0; 
                border-radius: 4px;
                background: #ffffff;
            }
            QPushButton {
                background: #3973ac; 
                color: #fff; 
                font-weight: 600;
                padding: 8px 16px; 
                border: none; 
                border-radius: 4px;
            }
            QPushButton:hover   { 
                background: #16519a; 
            }
            QPushButton:disabled { 
                background: #c1c8d0; 
            }
            QListWidget         { 
                border: 1px solid #d2d9e3; 
                border-radius: 4px; 
            }
            QListWidget::item:selected { 
                background: #5b8edc; 
                color: #fff; 
            }
            QProgressBar {
                border: 1px solid #c0c6d0;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(18)

        left_pane = QVBoxLayout()
        left_pane.setSpacing(12)
        root.addLayout(left_pane, 1)

        heading = QLabel("Report Generation")
        heading.setStyleSheet("font-size: 26px; font-weight: 600; color: #1a2733;")
        left_pane.addWidget(heading)

        filter_box = QGroupBox("Filters")
        filter_form = QFormLayout(filter_box)
        filter_form.setSpacing(10)

        self.start_date = QDateEdit(calendarPopup=True)
        self.start_date.setDate(QDate.currentDate())
        filter_form.addRow("Start date:", self.start_date)

        self.end_date = QDateEdit(calendarPopup=True)
        self.end_date.setDate(QDate.currentDate().addDays(1))
        filter_form.addRow("End date:", self.end_date)

        self.patient_filter = QComboBox()
        self.patient_filter.addItem("All patients", None)
        filter_form.addRow("Patient:", self.patient_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Completed", "Pending"])
        filter_form.addRow("Status:", self.status_filter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by order / patient / test …")
        self.search_input.textChanged.connect(self.search_orders)
        filter_form.addRow("Search:", self.search_input)

        left_pane.addWidget(filter_box)

        stats_box = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_box)
        self.stats_loaded = QLabel("Loaded orders : 0")
        self.stats_selected = QLabel("Selected orders : 0")
        self.stats_date_range = QLabel("Date range : —")
        stats_layout.addWidget(self.stats_loaded)
        stats_layout.addWidget(self.stats_selected)
        stats_layout.addWidget(self.stats_date_range)
        left_pane.addWidget(stats_box)

        left_pane.addStretch()

        right_pane = QVBoxLayout()
        right_pane.setSpacing(12)
        root.addLayout(right_pane, 2)

        header_row = QHBoxLayout()
        header_lbl = QLabel("Available Orders")
        header_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #21384a;")
        header_row.addWidget(header_lbl)
        header_row.addStretch()

        self.select_all_btn = QPushButton("Select all")
        self.select_none_btn = QPushButton("Clear")
        self.invert_sel_btn = QPushButton("Invert")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_none_btn.clicked.connect(self.select_none)
        self.invert_sel_btn.clicked.connect(self.invert_selection)
        header_row.addWidget(self.select_all_btn)
        header_row.addWidget(self.select_none_btn)
        header_row.addWidget(self.invert_sel_btn)
        right_pane.addLayout(header_row)

        self.order_list = QListWidget()
        self.order_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.order_list.itemChanged.connect(self.update_selected_stats)
        right_pane.addWidget(self.order_list, 1)

        actions_row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        try:
            self.refresh_btn.setIcon(QIcon("icons/refresh_icon.png"))
        except:
            pass
        self.refresh_btn.clicked.connect(self.load_orders)
        actions_row.addWidget(self.refresh_btn)

        self.export_pdf_btn = QPushButton("PDF")
        try:
            self.export_pdf_btn.setIcon(QIcon("icons/pdf_icon.png"))
        except:
            pass
        self.export_pdf_btn.clicked.connect(self.generate_pdf)
        actions_row.addWidget(self.export_pdf_btn)

        self.export_csv_btn = QPushButton("CSV")
        try:
            self.export_csv_btn.setIcon(QIcon("icons/csv_icon.png"))
        except:
            pass
        self.export_csv_btn.clicked.connect(self.export_csv)
        actions_row.addWidget(self.export_csv_btn)

        actions_row.addStretch()
        right_pane.addLayout(actions_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 100)
        right_pane.addWidget(self.progress)

        self.load_patients()
        self.load_orders()

    def load_patients(self):
        """Load patients into the filter dropdown"""
        session = Session()
        try:
            patients = session.query(Patient).all()
            self.patient_filter.clear()
            self.patient_filter.addItem("All patients", None)
            for p in patients:
                try:
                    name = p.decrypted_name
                except Exception:
                    name = "Decryption failed"
                self.patient_filter.addItem(name, p.id)
        except Exception as e:
            QMessageBox.warning(self, "Database Error", f"Failed to load patients: {str(e)}")
        finally:
            session.close()

    def load_orders(self):
        """Load orders based on current filters"""
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()
        if start > end:
            QMessageBox.warning(self, "Invalid range", "Start date must be before end date.")
            return

        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate progress

        session = Session()
        try:
            q = (session.query(Order)
                 .options(joinedload(Order.patient), joinedload(Order.test))
                 .outerjoin(Result, Order.id == Result.order_id))

            pid = self.patient_filter.currentData()
            if pid:
                q = q.filter(Order.patient_id == pid)

            status = self.status_filter.currentText()
            if status == "Completed":
                q = q.filter(Result.id.isnot(None))
            elif status == "Pending":
                q = q.filter(Result.id.is_(None))

            q = q.filter(Order.order_date.between(start, end))
            orders = q.order_by(Order.order_date.desc()).all()

            self.order_list.blockSignals(True)
            self.order_list.clear()
            for order in orders:
                try:
                    patient_name = order.patient.decrypted_name
                except Exception:
                    patient_name = "Decryption failed"
                test_name = order.test.name if order.test else "—"
                txt = f"#{order.id} | {patient_name} – {test_name} ({order.order_date:%Y-%m-%d})"
                item = QListWidgetItem(txt)
                item.setData(Qt.ItemDataRole.UserRole, order.id)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.order_list.addItem(item)
            self.order_list.blockSignals(False)

            self.stats_loaded.setText(f"Loaded orders : {len(orders)}")
            self.stats_date_range.setText(f"Date range : {start} → {end}")
            self.update_selected_stats()

            if not orders:
                QMessageBox.information(self, "No data", "No orders match the current filters.")

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load orders: {str(e)}")
        finally:
            session.close()
            self.progress.setVisible(False)
            self.progress.setRange(0, 100)

    def search_orders(self):
        """Filter orders list based on search text"""
        txt = self.search_input.text().lower()
        for i in range(self.order_list.count()):
            item = self.order_list.item(i)
            item.setHidden(txt not in item.text().lower() if txt else False)

    def select_all(self):
        """Select all orders in the list"""
        self.order_list.blockSignals(True)
        for i in range(self.order_list.count()):
            self.order_list.item(i).setCheckState(Qt.CheckState.Checked)
        self.order_list.blockSignals(False)
        self.update_selected_stats()

    def select_none(self):
        """Deselect all orders in the list"""
        self.order_list.blockSignals(True)
        for i in range(self.order_list.count()):
            self.order_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.order_list.blockSignals(False)
        self.update_selected_stats()

    def invert_selection(self):
        """Invert the current selection"""
        self.order_list.blockSignals(True)
        for i in range(self.order_list.count()):
            item = self.order_list.item(i)
            new_state = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new_state)
        self.order_list.blockSignals(False)
        self.update_selected_stats()

    def update_selected_stats(self):
        """Update the selected orders count in statistics"""
        selected = sum(
            1 for i in range(self.order_list.count())
            if self.order_list.item(i).checkState() == Qt.CheckState.Checked
        )
        self.stats_selected.setText(f"Selected orders : {selected}")

    def _get_selected_orders(self):
        """Get list of selected order IDs"""
        ids = [
            self.order_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.order_list.count())
            if self.order_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        if not ids:
            QMessageBox.warning(self, "No selection", "Please tick at least one order.")
        return ids

    def generate_pdf(self):
        """Generate PDF report for selected orders"""
        ids = self._get_selected_orders()
        if not ids:
            return

        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate progress
        QApplication.processEvents()

        session = Session()
        patient_orders = {}
        try:
            for oid in ids:
                order = (session.query(Order)
                         .options(joinedload(Order.patient), joinedload(Order.test))
                         .get(oid))
                if order and order.patient:
                    patient_orders.setdefault(order.patient_id, []).append(order)

            if not patient_orders:
                QMessageBox.warning(self, "No Data", "No valid orders found for selected items.")
                return

            pdf_path = generate_pdf_report(patient_orders)
            QMessageBox.information(self, "Report Complete", f"PDF saved to:\n{pdf_path}")

        except Exception as e:
            QMessageBox.critical(self, "PDF Generation Error", f"Failed to generate PDF: {str(e)}")
        finally:
            session.close()
            self.progress.setVisible(False)
            self.progress.setRange(0, 100)

    def export_csv(self):
        """Export selected orders to CSV"""
        ids = self._get_selected_orders()
        if not ids:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "orders_export.csv", "CSV Files (*.csv)"
        )

        if not file_path:
            return

        self.progress.setVisible(True)
        self.progress.setRange(0, len(ids))

        session = Session()
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Order ID", "Patient Name", "Test Name", "Order Date", "Status"])

                for i, oid in enumerate(ids):
                    order = (session.query(Order)
                             .options(joinedload(Order.patient), joinedload(Order.test))
                             .get(oid))
                    if order:
                        try:
                            patient_name = order.patient.decrypted_name
                        except Exception:
                            patient_name = "Decryption failed"
                        test_name = order.test.name if order.test else ""
                        status = "Completed" if order.results else "Pending"
                        writer.writerow([
                            order.id,
                            patient_name,
                            test_name,
                            order.order_date.isoformat(),
                            status
                        ])
                    
                    self.progress.setValue(i + 1)
                    QApplication.processEvents()

            QMessageBox.information(self, "Export Complete", f"CSV exported to:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {str(e)}")
        finally:
            session.close()
            self.progress.setVisible(False)
            self.progress.setRange(0, 100)

    def refresh_data(self):
        """Public method to refresh data (called from main window)"""
        self.load_patients()
        self.load_orders()
