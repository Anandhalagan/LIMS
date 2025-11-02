from reportlab.platypus.doctemplate import BaseDocTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus import PageTemplate
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import os
import json
from datetime import datetime
from contextlib import contextmanager
from database import Session
from models import Order, Result
from sqlalchemy.orm import joinedload
import re
from io import BytesIO
import webbrowser


# -----------------------------------------------------------------
# Custom RoundedTable Flowable with Shadow
# -----------------------------------------------------------------
class RoundedTable(Table):
    def draw(self):
        canv = self.canv
        w, h = self._width, self._height

        r = 10      # corner radius
        offset = 3  # shadow offset

        # Shadow rectangle (slightly offset)
        canv.saveState()
        canv.setFillColorRGB(0, 0, 0, 0.12)  # semi-transparent grey
        canv.roundRect(offset, -offset, w, h, r, stroke=0, fill=1)
        canv.restoreState()

        # Clip to rounded rect for content (to make backgrounds curved)
        canv.saveState()
        p = canv.beginPath()
        p.roundRect(0, 0, w, h, r)
        canv.clipPath(p, stroke=0, fill=0)
        # Draw the actual table content (backgrounds and text will be clipped to curved shape)
        super().draw()
        canv.restoreState()

        # Main rounded rectangle border (drawn after content to sit on top)
        canv.saveState()
        canv.setStrokeColor(colors.HexColor("#1565c0"))
        canv.setLineWidth(1)
        canv.roundRect(0, 0, w, h, r, stroke=1, fill=0)
        canv.restoreState()


# -----------------------------------------------------------------
# GLOBAL FONT DEFINITION
# -----------------------------------------------------------------
bold_font_name = 'Helvetica-Bold'


# -----------------------------------------------------------------
# Custom DocTemplate for Repeating Headers
# -----------------------------------------------------------------
class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        self.current_patient = None
        self.current_styles = create_styles()
        self.current_order = None
        # Adjust frame to accommodate patient details in header
        frame = Frame(15*mm, 20*mm, 180*mm, A4[1] - 20*mm - 70*mm, id='normal')
        template = PageTemplate(id='all', frames=[frame], onPage=self.draw_header, onPageEnd=self.draw_footer)
        self.addPageTemplates([template])

    def draw_header(self, canvas, doc):
        canvas.saveState()
        page_height = A4[1]
        y = page_height - 10 * mm  # Start near top

        # Lab logo - positioned at top right
        logo_path = os.path.join(os.path.dirname(__file__), "lab_logo.png")
        if os.path.exists(logo_path):
            # Draw logo on the right side
            canvas.drawImage(logo_path, 165 * mm, y - 20 * mm, width=30*mm, height=30*mm)
        title_x = 15 * mm  # Keep title on the left

        # Lab title with premium styling - positioned after logo
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(colors.HexColor("#0d47a1"))
        canvas.drawString(title_x, y - 5 * mm, "SENTHIL CLINICAL LABORATORY")

        y -= 8 * mm
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.black)
        canvas.drawString(title_x, y, "Accurate | Caring | Instant")

        y -= 6 * mm
        canvas.drawString(title_x, y, "#5 MRR buliding,Near Police Checkpost,Linga Nagar,Woraiyur,Trichy-620102")

        y -= 6 * mm
        canvas.drawString(title_x, y, "Phone: 8667626117 | WhatsApp: 9176403894")

        # Patient details section - ALWAYS SHOW PATIENT DETAILS
        if self.current_patient:
            y -= 10 * mm
            
            # Create patient details table directly in header
            patient = self.current_patient
            order = self.current_order
            
            # Patient details table data - LEFT SIDE
            left_col_x = 15 * mm
            right_col_x = 110 * mm
            line_height = 4 * mm
            
            # Left Column - Patient Basic Info
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(colors.HexColor("#1565c0"))
            
            # Row 1 - Title and Patient
            canvas.drawString(left_col_x, y, f"Title: {patient['title'] or 'N/A'}")
            canvas.drawString(left_col_x, y - line_height, f"Patient: {patient['name']}")
            
            # Row 2 - Age and Sex
            canvas.drawString(left_col_x, y - 2*line_height, f"Age: {patient['age'] or 'N/A'} Years")
            canvas.drawString(left_col_x, y - 3*line_height, f"Sex: {patient['gender']}")
            
            # Row 3 - PID
            canvas.drawString(left_col_x, y - 4*line_height, f"PID: {patient['pid']}")
            
            # Right Column - Dates and Referral Info
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(colors.HexColor("#1565c0"))
            
            # Row 1 - Registered on
            canvas.drawString(right_col_x, y, f"Registered on: {order['order_date'].strftime('%I:%M %p %d %b, %y')}")
            
            # Row 2 - Collected on
            canvas.drawString(right_col_x, y - line_height, f"Collected on: {order['order_date'].strftime('%I:%M %p %d %b, %y')}")
            
            # Row 3 - Reported on
            canvas.drawString(right_col_x, y - 2*line_height, f"Reported on: {datetime.now().strftime('%I:%M %p %d %b, %y')}")
            
            # Row 4 - Referred by
            referring_physician = order.get('referring_physician', 'N/A')
            canvas.drawString(right_col_x, y - 3*line_height, f"Referred by: {referring_physician}")
            
            y -= 5 * line_height  # Adjust for next section (now 5 lines)

        # Divider line with gradient effect
        canvas.setStrokeColor(colors.HexColor("#1565c0"))
        canvas.setLineWidth(1)
        canvas.line(15 * mm, y, 195 * mm, y)
        canvas.setStrokeColor(colors.HexColor("#90caf9"))
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, y - 0.5 * mm, 195 * mm, y - 0.5 * mm)

        canvas.restoreState()

    def draw_footer(self, canvas, doc):
        canvas.saveState()

        # Page number
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")

        # Footer branding
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(105 * mm, 15 * mm, "Home Care Service Available")

        canvas.restoreState()


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_styles():
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            name='title', fontSize=16, alignment=1,
            textColor=colors.HexColor("#0d47a1"), fontName=bold_font_name,
            spaceAfter=6
        ),
        'subtitle': ParagraphStyle(
            name='subtitle', fontSize=10, alignment=1,
            spaceBefore=0, spaceAfter=6
        ),
        'normal': ParagraphStyle(
            name='normal', fontSize=10, alignment=0
        ),
        'section_title': ParagraphStyle(
            name='section_title', fontSize=12, alignment=0,
            textColor=colors.HexColor("#1565c0"), fontName=bold_font_name
        ),
        'dept_header': ParagraphStyle(
            name='dept_header', fontSize=11, alignment=0,
            textColor=colors.white, fontName=bold_font_name
        ),
        'table_header': ParagraphStyle(
            name='table_header', fontSize=9, alignment=0,
            fontName=bold_font_name, textColor=colors.white
        ),
        'table_cell': ParagraphStyle(
            name='table_cell', fontSize=9, alignment=0
        ),
        'date_style': ParagraphStyle(
            name='date_style', fontSize=9, alignment=2
        ),
        'sig_style': ParagraphStyle(
            name='sig_style', fontSize=9, alignment=2
        ),
        'center_style': ParagraphStyle(
            name='center_style', fontSize=9, alignment=1
        ),
        'test_header': ParagraphStyle(
            name='test_header', fontSize=10, alignment=0,
            textColor=colors.HexColor("#0d47a1"), fontName=bold_font_name,
            spaceBefore=12, spaceAfter=6
        )
    }


def get_patient_info(order):
    try:
        patient = order['patient']
        return {
            'name': patient['decrypted_name'],
            'contact': patient['decrypted_contact'],
            'address': patient['decrypted_address'],
            'pid': patient.get('pid', "N/A"),
            'age': patient.get('age'),
            'gender': (patient.get('gender', "Unknown")).capitalize(),
            'title': patient.get('decrypted_title')
        }
    except Exception:
        return {
            'name': "Decryption Failed",
            'contact': "Decryption Failed",
            'address': "Decryption Failed",
            'pid': "N/A",
            'age': None,
            'gender': "Unknown",
            'title': "N/A"
        }


def create_patient_info_table(patient_info, order, styles):
    # REMOVED QR CODE - Using simplified patient info table
    data = [
        [Paragraph(f"Title: {patient_info['title'] or 'N/A'}", styles['normal']), 
         Paragraph(f"Registered on: {order['order_date'].strftime('%I:%M %p %d %b, %y')}", styles['date_style'])],
        [Paragraph(f"Patient: {patient_info['name']}", styles['normal']), 
         Paragraph(f"Collected on: {order['order_date'].strftime('%I:%M %p %d %b, %y')}", styles['date_style'])],
        [Paragraph(f"Age: {patient_info['age'] or 'N/A'} Years", styles['normal']), 
         Paragraph(f"Reported on: {datetime.now().strftime('%I:%M %p %d %b, %y')}", styles['date_style'])],
        [Paragraph(f"Sex: {patient_info['gender']}", styles['normal']), 
         Paragraph(f"PID: {patient_info['pid']}", styles['date_style'])]
    ]

    table = RoundedTable(data, colWidths=[90*mm, 90*mm])  # Increased width
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E3F2FD")),
        ('GRID', (0,0), (-1,-1), 0, colors.transparent),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))

    return table


def get_reference_range(ref, patient_gender, is_child):
    if isinstance(ref, dict):
        gender_ref = ref.get(patient_gender.lower(), ref.get("default", "N/A"))
        age_ref = ref.get("age_based", {})
        if age_ref:
            if is_child and "child" in age_ref:
                gender_ref = age_ref.get("child", gender_ref)
            elif not is_child and "adult" in age_ref:
                gender_ref = age_ref.get("adult", gender_ref)
        return str(gender_ref)
    return str(ref) if ref not in ('N/A', None) else 'N/A'


def create_department_content(patient_info, order, dept, dept_orders, all_results_data, all_test_notes, styles):
    elements = []

    # Department header
    elements.append(RoundedTable(
        [[Paragraph(dept, styles['dept_header'])]],
        colWidths=[180*mm],  # Increased width
        style=[('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#1565c0")),
               ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
               ('TEXTCOLOR', (0, 0), (-1, -1), colors.white)]
    ))
    elements.append(Spacer(1, 4*mm))

    # Create combined table for all tests in this department
    combined_table = create_combined_results_table(dept_orders, all_results_data, styles)
    elements.append(combined_table)
    elements.append(Spacer(1, 6*mm))
    
    # Add test notes if any
    if all_test_notes:
        for test_name, test_note in all_test_notes:
            elements.append(Paragraph(f"<b>{test_name} Notes:</b> {test_note}", styles['normal']))
            elements.append(Spacer(1, 2*mm))

    return elements


def create_combined_results_table(dept_orders, all_results_data, styles):
    # Start with table headers
    combined_data = [[
        Paragraph("Investigation", styles['table_header']),
        Paragraph("Result", styles['table_header']),
        Paragraph("Reference Value", styles['table_header']),
        Paragraph("Unit", styles['table_header'])
    ]]

    # Add all test data to the combined table
    test_header_rows = []  # Track which rows are test headers
    current_row = 1  # Start after the main header row
    
    for i, (order, results_data) in enumerate(zip(dept_orders, all_results_data)):
        # Add test name as a header row
        test_name = order['test'].get('name', "Unknown Test")
        if len(results_data) == 1 and results_data[0][0].text.split('<br/>')[0] == test_name:
            method = results_data[0][0].text.split('<br/>')[1]
            combined_data.append([
                Paragraph(f"<b>{test_name}</b><br/>{method}", styles['test_header']),
                results_data[0][1],
                results_data[0][2],
                results_data[0][3]
            ])
            test_header_rows.append(current_row)
            current_row += 1
        else:
            combined_data.append([
                Paragraph(f"<b>{test_name}</b>", styles['test_header']),
                Paragraph("", styles['table_cell']),
                Paragraph("", styles['table_cell']),
                Paragraph("", styles['table_cell'])
            ])
            test_header_rows.append(current_row)
            current_row += 1
            for row in results_data:
                combined_data.append(row)
                current_row += 1

    # Create the combined table with increased width
    combined_table = RoundedTable(combined_data, colWidths=[85*mm, 35*mm, 40*mm, 20*mm])  # Increased widths
    
    # Build table style
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d47a1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
    ]
    
    # Add styling for test header rows
    for row_idx in test_header_rows:
        table_style.extend([
            ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor("#e3f2fd")),
            ('LINEBELOW', (0, row_idx), (-1, row_idx), 1, colors.HexColor("#90caf9")),
        ])
    
    # Alternating row colors for premium look
    for row in range(1, len(combined_data)):
        if row % 2 == 1 and row not in test_header_rows:
            table_style.append(('BACKGROUND', (0, row), (-1, row), colors.HexColor("#f5f5f5")))
    
    combined_table.setStyle(TableStyle(table_style))
    
    return combined_table


def create_results_data(order, results_dict, template, patient_gender, is_child, styles):
    results_data = []

    for field in template:
        name = field.get('name', 'N/A')
        value = str(results_dict.get(name, 'N/A'))
        ref = field.get('reference', {})
        unit = field.get('unit', 'N/A')
        test_method = field.get('method', '')
        # Clean up method display - remove duplicate "Method:" and parentheses
        if test_method:
            test_method = test_method.replace('(Method:', '').replace(')', '').strip()
        ref_range = get_reference_range(ref, patient_gender, is_child)

        display_value = value
        value_style = ParagraphStyle(
            name="normal_value", parent=styles['table_cell'],
            textColor=colors.black
        )

        if ref_range != 'N/A' and value not in ('N/A', ''):
            try:
                # Handle different types of reference ranges
                if isinstance(ref_range, str):
                    ref_range_clean = ref_range.strip()
                    
                    # Handle range format (e.g., "80-100")
                    if '-' in ref_range_clean:
                        low, high = map(float, ref_range_clean.split('-'))
                        val = float(value)
                        if val < low or val > high:
                            display_value = f"{value}"
                            value_style = ParagraphStyle(
                                name="abnormal_value", parent=styles['table_cell'],
                                textColor=colors.red, fontName=bold_font_name
                            )
                        else:
                            display_value = f"{value}"
                            value_style = ParagraphStyle(
                                name="normal_value", parent=styles['table_cell'],
                                textColor=colors.green, fontName=bold_font_name
                            )
                    
                    # Handle less than format (e.g., "<200")
                    elif ref_range_clean.startswith('<'):
                        threshold = float(ref_range_clean[1:])
                        val = float(value)
                        if val >= threshold:
                            display_value = f"{value}"
                            value_style = ParagraphStyle(
                                name="abnormal_value", parent=styles['table_cell'],
                                textColor=colors.red, fontName=bold_font_name
                            )
                        else:
                            display_value = f"{value}"
                            value_style = ParagraphStyle(
                                name="normal_value", parent=styles['table_cell'],
                                textColor=colors.green, fontName=bold_font_name
                            )
                    
                    # Handle greater than format (e.g., ">40")
                    elif ref_range_clean.startswith('>'):
                        threshold = float(ref_range_clean[1:])
                        val = float(value)
                        if val <= threshold:
                            display_value = f"{value}"
                            value_style = ParagraphStyle(
                                name="abnormal_value", parent=styles['table_cell'],
                                textColor=colors.red, fontName=bold_font_name
                            )
                        else:
                            display_value = f"{value}"
                            value_style = ParagraphStyle(
                                name="normal_value", parent=styles['table_cell'],
                                textColor=colors.green, fontName=bold_font_name
                            )
                            
            except (ValueError, TypeError):
                # If conversion fails, keep normal styling
                pass

        # Build the method display text
        method_display = ""
        if test_method:
            method_display = f"<br/><font size='7' color='#666666'>Method: {test_method}</font>"
            
        results_data.append([
            Paragraph(f"{name}{method_display}", styles['table_cell']),
            Paragraph(display_value, value_style),
            Paragraph(str(ref_range), styles['table_cell']),
            Paragraph(unit, styles['table_cell'])
        ])

    return results_data


def add_signature_section(elements, styles):
    elements.append(Spacer(1, 10*mm))
    sig_data = [
        [Paragraph("SENTHIL. R", styles['sig_style'])],
        [Paragraph("(Senior Lab techinician)", styles['sig_style'])]
    ]
    sig_table = Table(sig_data, colWidths=[180*mm], hAlign='RIGHT')  # Increased width
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT')
    ]))
    elements.append(KeepTogether([
        sig_table,
        Spacer(1, 6*mm),
        Paragraph("Thanks for Reference", styles['center_style']),
        Paragraph("**** End of Report ****", styles['center_style']),
        Spacer(1, 12*mm)
    ]))


def generate_pdf_report(patient_orders):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reports')
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_file = os.path.join(output_dir, f'report_{timestamp}.pdf')

    doc = MyDocTemplate(
        pdf_file, pagesize=A4,
        topMargin=90*mm, bottomMargin=20*mm, leftMargin=15*mm, rightMargin=15*mm  # Adjusted margins
    )
    doc.title = "Patient Report"
    doc.author = "Ram's Lab"
    doc.subject = "Clinical Laboratory Test Report"

    elements = []

    with session_scope() as session:
        # Fetch all orders with joinedload to avoid lazy loading issues
        order_ids = [order.id for patient_id, orders in patient_orders.items() for order in orders]
        orders = session.query(Order).options(
            joinedload(Order.patient), joinedload(Order.test)
        ).filter(Order.id.in_(order_ids)).all()

        # Convert orders to dictionaries with related data
        order_dicts = [
            {
                'id': order.id,
                'patient': {
                    'decrypted_name': order.patient.decrypted_name if order.patient else "N/A",
                    'decrypted_contact': order.patient.decrypted_contact if order.patient and order.patient.contact else "N/A",
                    'decrypted_address': order.patient.decrypted_address if order.patient and order.patient.address else "N/A",
                    'pid': order.patient.pid if order.patient else "N/A",
                    'age': order.patient.age,
                    'gender': order.patient.gender if order.patient else "Unknown",
                    'decrypted_title': order.patient.decrypted_title if order.patient else "N/A"
                },
                'test': {
                    'name': order.test.name if order.test else "Unknown Test",
                    'department': order.test.department if order.test else "Unknown",
                    'template': json.loads(order.test.template) if order.test and order.test.template else [],
                    'notes': order.test.notes if order.test and order.test.notes else ""
                },
                'order_date': order.order_date,
                'referring_physician': order.referring_physician,  # Added referring physician
                'results': session.query(Result).filter_by(order_id=order.id).first()
            }
            for order in orders
        ]

        # Group by PID to merge same patient
        pid_to_orders = {}
        for order in order_dicts:
            pid = order['patient']['pid']
            if pid not in pid_to_orders:
                pid_to_orders[pid] = []
            pid_to_orders[pid].append(order)

        first_patient = True
        for pid, all_orders in pid_to_orders.items():
            if not all_orders:
                continue

            if not first_patient:
                elements.append(PageBreak())
            first_patient = False

            # Sort orders by date
            all_orders.sort(key=lambda o: o['order_date'])

            first_order = all_orders[0]
            patient_info = get_patient_info(first_order)
            try:
                is_child = int(patient_info['age']) < 18
            except:
                is_child = False

            doc.current_patient = patient_info
            doc.current_order = first_order

            # Group orders by department
            orders_by_department = {}
            for order in all_orders:
                dept = order['test'].get('department', "Unknown")
                if dept not in orders_by_department:
                    orders_by_department[dept] = []
                orders_by_department[dept].append(order)

            # Create content for each department
            first_department = True
            for dept, dept_orders in orders_by_department.items():
                if not first_department:
                    elements.append(PageBreak())  # Separate page for each department
                first_department = False

                all_results_data = []
                all_test_notes = []
                
                for order in dept_orders:
                    results_dict = json.loads(order['results'].results) if order['results'] and order['results'].results else {}
                    template = order['test'].get('template', [])
                    test_notes = order['test'].get('notes', "")

                    results_data = create_results_data(order, results_dict, template, patient_info['gender'], is_child, doc.current_styles)
                    all_results_data.append(results_data)
                    
                    if test_notes:
                        all_test_notes.append((order['test'].get('name', "Unknown Test"), test_notes))

                dept_content = create_department_content(patient_info, dept_orders[0], dept, dept_orders, all_results_data, all_test_notes, doc.current_styles)
                
                for element in dept_content:
                    elements.append(element)

            # Add signature section at the end of the patient's report
            add_signature_section(elements, doc.current_styles)

    doc.build(elements)
    
    # Automatically open the PDF in the default browser
    try:
        # Convert the file path to a file URL
        pdf_url = f"file://{os.path.abspath(pdf_file)}"
        webbrowser.open(pdf_url)
        print(f"Report generated and opened in browser: {pdf_file}")
    except Exception as e:
        print(f"Error opening PDF in browser: {str(e)}")
        # Fallback: try to open with system default application
        try:
            import subprocess
            import platform
            system = platform.system()
            if system == "Windows":
                os.startfile(pdf_file)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", pdf_file])
            else:  # Linux
                subprocess.run(["xdg-open", pdf_file])
            print(f"Report generated and opened with system default: {pdf_file}")
        except Exception as e2:
            print(f"Error opening PDF with system default: {str(e2)}")
    
    return pdf_file