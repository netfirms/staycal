import csv
from io import StringIO, BytesIO
from datetime import date
from ..models import Booking, User

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_csv_report(bookings: list[Booking], rooms_map: dict) -> str:
    """Generates a CSV report from a list of bookings."""
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Booking ID", "Guest Name", "Room", "Start Date", "End Date", "Price", "Status"])

    # Data
    for b in bookings:
        writer.writerow([
            b.id,
            b.guest_name,
            rooms_map.get(b.room_id).name if rooms_map.get(b.room_id) else f"Room #{b.room_id}",
            b.start_date.isoformat(),
            b.end_date.isoformat(),
            f"{b.price:.2f}" if b.price is not None else "0.00",
            b.status.value
        ])

    return output.getvalue()

def generate_pdf_report(bookings: list[Booking], rooms_map: dict, user: User, period_start: date, period_end: date) -> bytes:
    """Generates a PDF report from a list of bookings using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title = f"Booking Report for {user.homestay.name if user.homestay else 'Your Property'}"
    elements.append(Paragraph(title, styles['h1']))

    # Subtitle with date range
    subtitle = f"Period: {period_start.isoformat()} to {period_end.isoformat()}"
    elements.append(Paragraph(subtitle, styles['h2']))
    elements.append(Spacer(1, 0.25*inch))

    # Table Data
    data = [["Guest", "Room", "Check-in", "Check-out", "Price", "Status"]]
    for b in bookings:
        price_str = f"{user.currency|get_currency_symbol(user.currency)}{b.price:.2f}" if b.price is not None else "-"
        data.append([
            b.guest_name,
            rooms_map.get(b.room_id).name if rooms_map.get(b.room_id) else f"#{b.room_id}",
            b.start_date.isoformat(),
            b.end_date.isoformat(),
            price_str,
            b.status.value.title()
        ])

    # Create Table
    table = Table(data, colWidths=[1.5*inch, 1.2*inch, 1*inch, 1*inch, 0.8*inch, 1*inch])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.teal),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()

# Helper for currency symbol in PDF, since filters aren't available here
CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "THB": "฿",
}
def get_currency_symbol(currency_code: str) -> str:
    return CURRENCY_SYMBOLS.get(currency_code.upper(), "")
