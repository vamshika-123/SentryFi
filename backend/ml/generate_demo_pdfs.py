import os
from reportlab.pdfgen import canvas

DEMO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../demo_samples'))
os.makedirs(DEMO_DIR, exist_ok=True)

def create_invoice_clean_inr(filepath):
    c = canvas.Canvas(filepath)
    c.drawString(100, 750, "INVOICE - TECH SOLUTIONS PVT LTD")
    c.drawString(100, 730, "GSTIN: 27AACCT1234E1Z9")
    c.drawString(100, 710, "Date: 23 Aug 2026")
    
    c.drawString(100, 670, "Line Item 1: Web Development   Rs. 20,150.50")
    c.drawString(100, 650, "Line Item 2: Cloud Hosting     Rs. 30,225.00")
    
    c.drawString(100, 610, "Subtotal:                      Rs. 50,375.50")
    c.drawString(100, 590, "IGST (18%):                    Rs. 9,067.59")
    c.drawString(100, 570, "Grand Total:                   Rs. 59,443.09")
    
    c.save()

def create_invoice_fraud_tampered_inr(filepath):
    c = canvas.Canvas(filepath)
    c.drawString(100, 750, "INVOICE - SHADOW SERVICES LTD")
    c.drawString(100, 730, "GSTIN: ")
    c.drawString(100, 710, "Date: 12 Aug 2026")
    
    # Mathematical anomaly: items don't sum to subtotal, GST is wrong percentage
    c.drawString(100, 670, "Line Item 1: Consulting        Rs. 15,000.00")
    c.drawString(100, 650, "Line Item 2: Maintenance       Rs. 25,000.00")
    
    c.drawString(100, 610, "Subtotal:                      Rs. 95,000.00")
    c.drawString(100, 590, "IGST (45%):                    Rs. 42,750.00")
    c.drawString(100, 570, "Total Due:                     Rs. 137,750.00")
    
    c.save()

def create_compliance_clean(filepath):
    c = canvas.Canvas(filepath)
    
    text = (
        "All terms standard as per company policy and Companies Act 2013. "
        "Tax forms filed and completed according to income tax rules."
    )
    
    # Split text for basic wrapping
    y = 690
    for i in range(0, len(text), 70):
        c.drawString(100, y, text[i:i+70])
        y -= 20
        
    c.save()

def create_compliance_violation_aml(filepath):
    c = canvas.Canvas(filepath)
    
    text = (
        "This agreement outlines the unrecorded liabilities for Q3. "
        "Payments shall be routed via non-disclosed shell companies in Mauritius "
        "without standard PMLA source verification. "
        "Beneficial owner information will remain obscured violating standard KYC norms."
    )
    
    y = 690
    for i in range(0, len(text), 70):
        c.drawString(100, y, text[i:i+70])
        y -= 20
        
    c.save()

if __name__ == "__main__":
    print(f"Generating test PDFs in {DEMO_DIR}...")
    create_invoice_clean_inr(os.path.join(DEMO_DIR, 'invoice_clean_inr.pdf'))
    create_invoice_fraud_tampered_inr(os.path.join(DEMO_DIR, 'invoice_fraud_tampered_inr.pdf'))
    create_compliance_clean(os.path.join(DEMO_DIR, 'compliance_clean.pdf'))
    create_compliance_violation_aml(os.path.join(DEMO_DIR, 'compliance_violation_aml.pdf'))
    print("Done generating test PDFs.")
