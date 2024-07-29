from datetime import datetime
from data_handler import fetch_data
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import os

fixed_metrics = {
    'modbus': [
        "allarmi_ibt_129",
        "stato_macchina",
        "numero_ricetta_attuale",
    ],
    'opcua': [
        "xAcquaCaldaSt",
        "rTT102Set",
        "rTT102Val",
    ],
    'api_request': [
        "9CGX505109-----10:21220004",
        "9VTX110547-----04:22120002",
    ]
}

def generate_daily_report():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"📊 Daily Report Summary\nGenerated on: {timestamp}\n",
        "----------------------------------------\n"
    ]
    pdf_data = [["Category", "Metric", "Mean", "Max", "Min", "Last"]]

    for category, metrics_list in fixed_metrics.items():
        report_lines.append(f"Category: {category}\n")
        report_lines.append("| Metric | Mean | Max | Min | Last |")
        report_lines.append("|------------|-----------|---------|--------|---------|")
        
        for metric in metrics_list:
            try:
                df = fetch_data(category, metric, period='-24h')
                if not df.empty:
                    mean_value = df['_value'].mean()
                    max_value = df['_value'].max()
                    min_value = df['_value'].min()
                    last_value = df['_value'].iloc[-1]
                    report_lines.append(
                        f"| {metric} | {mean_value:.2f} | {max_value:.2f} | {min_value:.2f} | {last_value:.2f} |"
                    )
                    pdf_data.append([category, metric, f"{mean_value:.2f}", f"{max_value:.2f}", f"{min_value:.2f}", f"{last_value:.2f}"])
                else:
                    report_lines.append(f"| {metric} | No data available | No data available | No data available | No data available |")
                    pdf_data.append([category, metric, "No data", "No data", "No data", "No data"])
            except Exception as e:
                report_lines.append(f"| {metric} | Error: {str(e)} | Error | Error | Error |")
                pdf_data.append([category, metric, f"Error: {str(e)}", "Error", "Error", "Error"])
        report_lines.append("\n")
    
    text_report = "\n".join(report_lines)
    
    
    return text_report, generate_pdf_report(pdf_data, timestamp)

def generate_pdf_report(data, timestamp):
    filename = f"daily_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title = Paragraph(f"Daily Report Summary - Generated on: {timestamp}", styles['Title'])
    elements.append(title)
    
    table = Table(data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    print(f"PDF report saved as '{filename}'")
    return filename
# Example usage
text_report = generate_daily_report()
print(text_report)
