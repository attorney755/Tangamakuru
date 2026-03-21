from datetime import datetime, timedelta
from flask import make_response
from app.models import Report, User
from app import db
import io
import csv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import base64
from io import BytesIO

def generate_monthly_report(user, month=None, year=None):
    """Generate monthly report PDF for admin or officer"""
    
    # Use current month/year if not specified
    if month is None or year is None:
        today = datetime.now()
        month = month or today.month
        year = year or today.year
    
    # Calculate date range
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    month_name = start_date.strftime('%B %Y')
    
    # Get reports based on user role
    if user['role'] == 'admin':
        # Admin sees reports in their district
        reports = Report.query.filter(
            Report.district == user['district'],
            Report.created_at >= start_date,
            Report.created_at <= end_date
        ).all()
        
        # Get officers in district
        officers = User.query.filter_by(
            role='officer',
            district=user['district']
        ).all()
        
        title = f"Monthly Report - {user['district']} District"
        
    elif user['role'] == 'officer':
        # Officer sees reports in their sector
        reports = Report.query.filter(
            Report.sector == user['sector'],
            Report.created_at >= start_date,
            Report.created_at <= end_date
        ).all()
        
        officers = []
        title = f"Monthly Report - {user['sector']} Sector"
    
    else:
        return None
    
    # Calculate statistics
    total_reports = len(reports)
    pending = sum(1 for r in reports if r.status == 'pending')
    in_progress = sum(1 for r in reports if r.status == 'in_progress')
    resolved = sum(1 for r in reports if r.status == 'resolved')
    
    # Priority breakdown
    urgent = sum(1 for r in reports if r.priority == 'urgent')
    high = sum(1 for r in reports if r.priority == 'high')
    medium = sum(1 for r in reports if r.priority == 'medium')
    low = sum(1 for r in reports if r.priority == 'low')
    
    # Category breakdown
    categories = {}
    for report in reports:
        cat = report.category
        categories[cat] = categories.get(cat, 0) + 1
    
    # Officer performance
    officer_stats = []
    for officer in officers:
        assigned = sum(1 for r in reports if r.assigned_officer_id == officer.id)
        resolved_by_officer = sum(1 for r in reports if r.assigned_officer_id == officer.id and r.status == 'resolved')
        if assigned > 0:
            officer_stats.append({
                'name': f"{officer.first_name} {officer.last_name}",
                'sector': officer.sector,
                'assigned': assigned,
                'resolved': resolved_by_officer,
                'rate': round((resolved_by_officer / assigned) * 100, 1)
            })
    
    # Sort officer stats by resolution rate
    officer_stats.sort(key=lambda x: x['rate'], reverse=True)
    
    return {
        'title': title,
        'month': month_name,
        'period': f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}",
        'stats': {
            'total': total_reports,
            'pending': pending,
            'in_progress': in_progress,
            'resolved': resolved,
            'urgent': urgent,
            'high': high,
            'medium': medium,
            'low': low
        },
        'categories': categories,
        'officer_stats': officer_stats,
        'reports': reports[:50]  # Limit to 50 reports in report
    }


def generate_pdf_report(data, user):
    """Generate PDF from report data"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    
    story = []
    
    # Title
    title_text = f"<font size=20><b>{data['title']}</b></font>"
    story.append(Paragraph(title_text, styles['Center']))
    story.append(Spacer(1, 0.25*inch))
    
    # Month and period
    month_text = f"<font size=14>{data['month']}</font>"
    story.append(Paragraph(month_text, styles['Center']))
    story.append(Spacer(1, 0.1*inch))
    
    period_text = f"<font size=10>Period: {data['period']}</font>"
    story.append(Paragraph(period_text, styles['Center']))
    story.append(Spacer(1, 0.3*inch))
    
    # Generated by
    generated_text = f"<font size=9>Generated by: {user['first_name']} {user['last_name']} ({user['role'].title()})</font>"
    story.append(Paragraph(generated_text, styles['Right']))
    story.append(Spacer(1, 0.2*inch))
    
    # Statistics Summary
    story.append(Paragraph("<b>SUMMARY STATISTICS</b>", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    stats_data = [
        ['Total Reports', 'Pending', 'In Progress', 'Resolved'],
        [
            str(data['stats']['total']),
            str(data['stats']['pending']),
            str(data['stats']['in_progress']),
            str(data['stats']['resolved'])
        ]
    ]
    
    stats_table = Table(stats_data, colWidths=[1.5*inch]*4)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Priority Breakdown
    story.append(Paragraph("<b>PRIORITY BREAKDOWN</b>", styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    
    priority_data = [
        ['Urgent', 'High', 'Medium', 'Low'],
        [
            str(data['stats']['urgent']),
            str(data['stats']['high']),
            str(data['stats']['medium']),
            str(data['stats']['low'])
        ]
    ]
    
    priority_table = Table(priority_data, colWidths=[1.5*inch]*4)
    priority_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(priority_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Category Breakdown
    if data['categories']:
        story.append(Paragraph("<b>CATEGORY BREAKDOWN</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        category_data = [['Category', 'Count']]
        for cat, count in data['categories'].items():
            category_data.append([cat, str(count)])
        
        category_table = Table(category_data, colWidths=[3*inch, 1*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(category_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Officer Performance (for admin reports)
    if data['officer_stats']:
        story.append(Paragraph("<b>OFFICER PERFORMANCE</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        officer_data = [['Officer', 'Sector', 'Assigned', 'Resolved', 'Rate']]
        for stat in data['officer_stats'][:10]:  # Top 10 officers
            officer_data.append([
                stat['name'],
                stat['sector'],
                str(stat['assigned']),
                str(stat['resolved']),
                f"{stat['rate']}%"
            ])
        
        officer_table = Table(officer_data, colWidths=[1.5*inch, 1.2*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        officer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(officer_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Recent Reports
    if data['reports']:
        story.append(Paragraph("<b>RECENT REPORTS</b>", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
        
        report_data = [['ID', 'Title', 'Category', 'Status', 'Priority', 'Date']]
        for report in data['reports'][:20]:  # Show only 20 most recent
            report_data.append([
                report.report_id,
                report.title[:30] + '...' if len(report.title) > 30 else report.title,
                report.category,
                report.status,
                report.priority,
                report.created_at.strftime('%d/%m/%Y')
            ])
        
        report_table = Table(report_data, colWidths=[1*inch, 1.5*inch, 1*inch, 1*inch, 0.8*inch, 1*inch])
        report_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(report_table)
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_text = f"<font size=8>Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}</font>"
    story.append(Paragraph(footer_text, styles['Right']))
    
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf


def generate_csv_report(data, user):
    """Generate CSV report from data"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['TANGAMAKURU MONTHLY REPORT'])
    writer.writerow([data['title']])
    writer.writerow([data['month']])
    writer.writerow([f"Generated by: {user['first_name']} {user['last_name']}"])
    writer.writerow([])
    
    # Statistics
    writer.writerow(['STATISTICS'])
    writer.writerow(['Total Reports', data['stats']['total']])
    writer.writerow(['Pending', data['stats']['pending']])
    writer.writerow(['In Progress', data['stats']['in_progress']])
    writer.writerow(['Resolved', data['stats']['resolved']])
    writer.writerow([])
    
    # Priority
    writer.writerow(['PRIORITY'])
    writer.writerow(['Urgent', data['stats']['urgent']])
    writer.writerow(['High', data['stats']['high']])
    writer.writerow(['Medium', data['stats']['medium']])
    writer.writerow(['Low', data['stats']['low']])
    writer.writerow([])
    
    # Categories
    if data['categories']:
        writer.writerow(['CATEGORIES'])
        for cat, count in data['categories'].items():
            writer.writerow([cat, count])
        writer.writerow([])
    
    # Officer stats
    if data['officer_stats']:
        writer.writerow(['OFFICER PERFORMANCE'])
        writer.writerow(['Name', 'Sector', 'Assigned', 'Resolved', 'Rate'])
        for stat in data['officer_stats']:
            writer.writerow([stat['name'], stat['sector'], stat['assigned'], stat['resolved'], f"{stat['rate']}%"])
        writer.writerow([])
    
    # Recent reports
    if data['reports']:
        writer.writerow(['RECENT REPORTS'])
        writer.writerow(['ID', 'Title', 'Category', 'Status', 'Priority', 'Date'])
        for report in data['reports']:
            writer.writerow([
                report.report_id,
                report.title,
                report.category,
                report.status,
                report.priority,
                report.created_at.strftime('%Y-%m-%d')
            ])
    
    return output.getvalue()