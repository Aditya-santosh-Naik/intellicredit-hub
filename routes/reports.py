from flask import Blueprint, jsonify, send_file
from pymongo import MongoClient
import io
import os

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

reports_bp = Blueprint('reports', __name__)

MONGO_URI = "mongodb://localhost:27017/"
try:
    client = MongoClient(MONGO_URI)
    db = client["intellicredit"]
    cases_col = db["cases"]
except Exception as e:
    print("Warning: Could not connect to MongoDB:", e)

@reports_bp.route('/api/cases/<case_id>/report.pdf', methods=['GET'])
def generate_report(case_id):
    """
    Stage 10: Investment Report Generation.
    Compiles all gathered entity intelligence, financial metrics, SWOT, 
    and scoring into a downloadable PDF document.
    """
    doc_data = cases_col.find_one({"case_id": case_id})
    if not doc_data:
        return jsonify({"error": "Case not found"}), 404
        
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterTitle', alignment=1, fontSize=18, spaceAfter=20, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name='SectionHeader', fontSize=14, spaceAfter=10, spaceBefore=15, fontName="Helvetica-Bold", textColor=colors.HexColor("#1A365D")))
    
    story = []
    
    # ── 1. Executive Summary ──
    story.append(Paragraph(f"IntelliCredit Investment Report", styles['CenterTitle']))
    story.append(Paragraph(f"Case ID: {doc_data.get('case_id')} | Entity: {doc_data.get('company', 'Unknown')} | Sector: {doc_data.get('sector', 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 12))
    
    req_loan = doc_data.get('loan_amount', 0)
    score = doc_data.get('composite_score', 'N/A')
    
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))
    story.append(Paragraph(f"The entity is requesting a facility of INR {req_loan:,.2f}. Based on automated Intelligence extraction and cross-triangulation, the system has assigned a composite score of {score}/100.", styles['Normal']))
    
    # Recommendation
    recommendation = doc_data.get('scoring', {}).get('recommendation', 'Pending')
    reasoning = doc_data.get('scoring', {}).get('reasoning', '')
    rec_color = colors.green if recommendation == "Approve" else colors.red if recommendation == "Reject" else colors.orange
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>System Recommendation:</b> <font color='{rec_color}'>{recommendation.upper()}</font>", styles['Normal']))
    story.append(Paragraph(f"<b>Reasoning:</b> {reasoning}", styles['Normal']))

    # ── 2. Financial Analysis ──
    story.append(Spacer(1, 20))
    story.append(Paragraph("Financial Health Overview", styles['SectionHeader']))
    
    financials = doc_data.get("financial_metrics", {})
    fin_data = [['Metric', 'Value']]
    for k, v in financials.items():
        val_str = f"INR {v:,.2f}" if isinstance(v, (int, float)) and v > 1000 else str(v)
        fin_data.append([k.capitalize(), val_str])
        
    if len(fin_data) > 1:
        t = Table(fin_data, colWidths=[200, 200])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#EBF8FF")),
            ('GRID', (0,0), (-1,-1), 1, colors.white)
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No financial metrics extracted.", styles['Normal']))

    # ── 3. Triangulation Alerts ──
    story.append(Spacer(1, 20))
    story.append(Paragraph("Secondary Intelligence & Triangulation", styles['SectionHeader']))
    
    triangulation = doc_data.get("triangulation", [])
    for t_alert in triangulation:
        flag_color = "red" if t_alert['flag'] in ["Warning", "Critical"] else "green" if t_alert['flag'] == "Positive" else "black"
        story.append(Paragraph(f"• <b><font color='{flag_color}'>[{t_alert['flag']}]</font></b>: {t_alert['message']}", styles['Normal']))
        story.append(Spacer(1, 6))

    # ── 4. SWOT Analysis ──
    story.append(Spacer(1, 12))
    story.append(Paragraph("SWOT Analysis", styles['SectionHeader']))
    
    swot = doc_data.get("swot", {})
    for category in ["strengths", "weaknesses", "opportunities", "threats"]:
        items = swot.get(category, [])
        if items:
            story.append(Paragraph(f"<b>{category.capitalize()}</b>", styles['Normal']))
            for item in items:
                story.append(Paragraph(f" - {item}", styles['Normal']))
            story.append(Spacer(1, 6))

    # Build PDF
    pdf.build(story)
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name=f"Report_{case_id}.pdf", mimetype='application/pdf')
