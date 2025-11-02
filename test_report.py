from reports.pdf_generator import generate_pdf_report
from reports.invoice_generator import generate_invoice
from database import Session
from models import Order

def test_reports():
    with Session() as session:
        # Get first order for testing
        order = session.query(Order).first()
        if order:
            order_id = order.id
            patient_id = order.patient_id
            orders = [order]
            
            # Generate test report
            print("Generating test report...")
            report_path = generate_pdf_report({patient_id: orders})
            print(f"Report generated at: {report_path}")
            
            # Generate test invoice
            print("\nGenerating test invoice...")
            invoice_path = generate_invoice([order_id])
            print(f"Invoice generated at: {invoice_path}")
        else:
            print("No orders found in database")

if __name__ == "__main__":
    test_reports()