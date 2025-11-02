# invoice_generator.py

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from datetime import datetime
import os
from database import Session, get_app_data_dir
from models import Order, Patient, Test
from sqlalchemy.orm import joinedload

class InvoiceGenerator:
    def __init__(self, order_ids):
        self.order_ids = order_ids
        self.reports_path = os.path.join(get_app_data_dir(), "reports")
        os.makedirs(self.reports_path, exist_ok=True)
        self.styles = getSampleStyleSheet()

        # Custom styles
        self.centered = ParagraphStyle(
            name="centered", parent=self.styles['Normal'], alignment=1
        )
        self.bold = ParagraphStyle(
            name="bold", parent=self.styles['Normal'], fontName='Helvetica-Bold'
        )
        self.right_align = ParagraphStyle(
            name="right_align", parent=self.styles['Normal'], alignment=2
        )
        self.bold_centered = ParagraphStyle(
            name="bold_centered", parent=self.styles['Normal'], 
            fontName='Helvetica-Bold', alignment=1
        )

        self.data = self.fetch_data()

    def fetch_data(self):
        with Session() as session:
            orders = session.query(Order).options(
                joinedload(Order.patient),
                joinedload(Order.test)
            ).filter(Order.id.in_(self.order_ids)).all()

            if not orders:
                raise ValueError("No orders found")

            patient = orders[0].patient  # Assume all orders for the same patient
            referring_physician = orders[0].referring_physician or "N/A"
            payment_method = orders[0].payment_method or "Cash"
            discount = orders[0].discount or 0.0

            # Group tests by department
            tests_by_dept = {}
            total_price = 0.0
            for order in orders:
                test = order.test
                price = test.rate_inr  # Use actual price from test model
                total_price += price
                dept = test.department or "Other"
                if dept not in tests_by_dept:
                    tests_by_dept[dept] = []
                tests_by_dept[dept].append((test.name, price))

            # Calculate discount and final amount
            discount_amount = total_price * (discount / 100)
            final_amount = total_price - discount_amount

            # Parse payments for multiple rows
            receipts = []
            if ';' in payment_method:
                payments = payment_method.split(';')
                for p in payments:
                    if ':' in p:
                        method, amount_str = p.split(':')
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            amount = 0.0
                    else:
                        method = p
                        amount = 0.0
                    receipts.append(f"{amount:.2f} {method}")
            else:
                # Handle case where payment method might include amount
                if ':' in payment_method:
                    method, amount_str = payment_method.split(':')
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        amount = final_amount
                    receipts.append(f"{amount:.2f} {method}")
                else:
                    receipts.append(f"{final_amount:.2f} {payment_method}")

            # Generate invoice number
            invoice_date = datetime.now().strftime('%Y-%m-%d')
            invoice_seq = f"{orders[0].id:03d}"  # Use first order ID padded to 3 digits
            invoice_no = f"{invoice_date}-{invoice_seq}"

            return {
                'lab_name': "SENTHIL CLINICAL LABORATORY",
                'lab_contact': "Phone: 8667626117 | WhatsApp: 9176403894",
                'lab_address': "#5 MRR buliding, Near Police Checkpost,Linga Nagar, Woraiyur, Trichy - 620102",
                'invoice_no': invoice_no,
                'patient_name': patient.decrypted_name,
                'patient_age': patient.age,
                'patient_sex': patient.gender,
                'patient_pid': patient.pid or "N/A",  # Changed from patient_uhid to patient_pid
                'patient_contact': patient.decrypted_contact or "N/A",
                'patient_address': patient.decrypted_address or "N/A",
                'booking_date': orders[0].order_date.strftime("%d/%m/%Y %H:%M"),
                'reference_doctor': referring_physician,
                'tests_by_dept': tests_by_dept,
                'bill_amount': total_price,
                'discount_percent': discount,
                'discount_amount': discount_amount,
                'final_amount': final_amount,
                'payment_method': payment_method,
                'paid_amount': final_amount,
                'due_amount': 0.00,
                'receipts': receipts,
                'cashier_signature': "..... (Cashier)",
            }

    def generate_pdf(self):
        pdf_path = os.path.join(
            self.reports_path,
            f"invoice_orders_{'_'.join(map(str, self.order_ids))}.pdf"
        )
        doc = SimpleDocTemplate(
            pdf_path, pagesize=letter,
            rightMargin=0.5*inch, leftMargin=0.5*inch,
            topMargin=0.5*inch, bottomMargin=0.5*inch
        )
        elements = []

        # Create a table for header with logo
        logo_path = os.path.join(os.path.dirname(__file__), "lab_logo.png")
        if os.path.exists(logo_path):
            header_data = [[
                Table([
                    [Paragraph(self.data['lab_name'], ParagraphStyle(
                        name="Title", parent=self.styles['Heading1'], alignment=1
                    ))],
                    [Paragraph(self.data['lab_contact'], ParagraphStyle(
                        name="NormalCentered", parent=self.styles['Normal'], alignment=1
                    ))],
                    [Paragraph(self.data['lab_address'], ParagraphStyle(
                        name="NormalCentered", parent=self.styles['Normal'], alignment=1
                    ))]
                ], colWidths=[5.5*inch]),
                Image(logo_path, width=1.2*inch, height=1.2*inch)
            ]]
            header_table = Table(header_data, colWidths=[5.5*inch, 1.5*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
                ('VALIGN', (0,0), (1,0), 'TOP'),
            ]))
            elements.append(header_table)
        else:
            # Fallback to centered header without logo
            elements.append(Paragraph(self.data['lab_name'], ParagraphStyle(
                name="Title", parent=self.styles['Heading1'], alignment=1
            )))
            elements.append(Paragraph(self.data['lab_contact'], ParagraphStyle(
                name="NormalCentered", parent=self.styles['Normal'], alignment=1
            )))
            elements.append(Paragraph(self.data['lab_address'], ParagraphStyle(
                name="NormalCentered", parent=self.styles['Normal'], alignment=1
            )))
        elements.append(Spacer(1, 0.2*inch))

        # Add a line separator
        line_table = Table([[""]], colWidths=[7*inch])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.black),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 0.2*inch))

        # Patient Details Table - Fixed layout
        patient_data = [
            [Paragraph("Patient:", self.bold), self.data['patient_name'], 
             Paragraph("Booking Date:", self.bold), self.data['booking_date']],
            [Paragraph("Age:", self.bold), f"{self.data['patient_age']} Years", 
             Paragraph("Invoice No.:", self.bold), self.data['invoice_no']],
            [Paragraph("Sex:", self.bold), self.data['patient_sex'], 
             Paragraph("Referring Doctor:", self.bold), self.data['reference_doctor']],
            [Paragraph("PID:", self.bold), self.data['patient_pid'],  # Changed from UHID to PID
             Paragraph("Address:", self.bold), self.data['patient_address']],
            [Paragraph("Contact:", self.bold), self.data['patient_contact'], "", ""],
        ]
        patient_table = Table(patient_data, colWidths=[1.0*inch, 2.0*inch, 1.2*inch, 2.8*inch])
        patient_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('SPAN', (3,3), (3,4)),  # Address spans two rows
        ]))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.3*inch))

        # Invoice Section
        elements.append(Paragraph("INVOICE", ParagraphStyle(
            name="InvoiceTitle", parent=self.styles['Heading2'], alignment=1
        )))
        elements.append(Spacer(1, 0.1*inch))

        # Tests Table - Fixed structure
        all_test_data = []
        headers = [Paragraph(h, self.bold_centered) for h in ['S.No', 'Test Name', 'Rate', 'QTY', 'Amount']]
        all_test_data.append(headers)
        
        sno = 1
        for dept, tests in self.data['tests_by_dept'].items():
            # Add department as a merged row with special styling
            dept_row = [Paragraph(dept, self.bold_centered)] + ["" for _ in range(4)]
            all_test_data.append(dept_row)
            for name, price in tests:
                test_row = [
                    str(sno),  # S.No without Paragraph for better alignment
                    Paragraph(name, self.styles['Normal']),
                    Paragraph(f"{price:.2f}", self.right_align),
                    "1",  # QTY without Paragraph for better alignment
                    Paragraph(f"{price:.2f}", self.right_align)
                ]
                all_test_data.append(test_row)
                sno += 1

        test_table = Table(all_test_data, colWidths=[0.5*inch, 3.5*inch, 1.0*inch, 0.5*inch, 1.0*inch])
        # Create list to track department row indices
        dept_rows = []
        for i, row in enumerate(all_test_data):
            if isinstance(row[0], Paragraph) and row[1] == "":  # This is a department row
                dept_rows.append(i)
        
        style_commands = [
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,-1), 'CENTER'),  # Center S.No column
            ('ALIGN', (2,0), (-1,-1), 'RIGHT'),  # Right align amount columns
            ('ALIGN', (3,0), (3,-1), 'CENTER'),  # Center QTY column
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),  # Basic grid for all cells
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),  # Header bottom line
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),  # Header background
        ]
        
        # Add department row styling
        for i in dept_rows:
            style_commands.append(('SPAN', (0,i), (-1,i)))  # Span all columns
            style_commands.append(('BACKGROUND', (0,i), (-1,i), colors.whitesmoke))  # Department background
            
        test_table.setStyle(TableStyle(style_commands))
        elements.append(test_table)
        elements.append(Spacer(1, 0.3*inch))

        # Bill Summary - Fixed table structure
        summary_data = [
            [Paragraph("Bill Amount:", self.bold), Paragraph(f"{self.data['bill_amount']:.2f}", self.right_align)],
            [Paragraph(f"Discount ({self.data['discount_percent']}%):", self.bold), Paragraph(f"-{self.data['discount_amount']:.2f}", self.right_align)],
            [Paragraph("Final Amount:", self.bold), Paragraph(f"{self.data['final_amount']:.2f}", self.right_align)],
        ]
        summary_table = Table(summary_data, colWidths=[4*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEABOVE', (0,2), (-1,2), 1, colors.black),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.1*inch))

        # Payment Method and Status
        payment_data = [
            [Paragraph("Payment Method:", self.bold), 
             Paragraph(self.data['payment_method'].split(':')[0] if ':' in self.data['payment_method'] else self.data['payment_method'], self.styles['Normal'])],
            [Paragraph("Status:", self.bold), 
             Paragraph("Paid" if self.data['due_amount'] == 0 else "Pending", self.styles['Normal'])],
        ]
        payment_table = Table(payment_data, colWidths=[4*inch, 3*inch])
        elements.append(payment_table)
        elements.append(Spacer(1, 0.2*inch))

        # Payment Details - Only show if there are receipts
        if self.data['receipts']:
            elements.append(Paragraph("Payment Details:", self.bold))
            for receipt in self.data['receipts']:
                elements.append(Paragraph(receipt, self.styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))

        # Cashier's Signature - Right aligned
        signature_data = [
            ["", ""],
            ["", Paragraph("Cashier's Signature", self.bold)],
            ["", self.data['cashier_signature']]
        ]
        signature_table = Table(signature_data, colWidths=[5*inch, 2*inch])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ]))
        elements.append(signature_table)

        doc.build(elements)
        return pdf_path

def generate_invoice(order_ids):
    generator = InvoiceGenerator(order_ids)
    pdf_path = generator.generate_pdf()
    return pdf_path