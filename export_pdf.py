import json
import sys
from datetime import datetime, timedelta
import pytz
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
import os
from process import load_submissions, load_contest_data, process, convert_to_unix_time
from utils import load_handles

pakistan_tz = pytz.timezone("Asia/Karachi")
USER_FILE = "users.txt"

def parse_date(date_str):
    return datetime.strptime(date_str, "%d%m%Y").date()

def load_user_real_names():
    """Load mapping of handles to real names from users.txt file"""
    user_map = {}
    try:
        with open("users.txt", "r") as f:
            for line in f:
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 2:
                    real_name = parts[0]
                    handle = parts[1]
                    user_map[handle] = real_name
    except Exception as e:
        print(f"Warning: Could not load user names from users.txt: {e}")
    return user_map

def generate_calendar_data(student, start_date, end_date):
    """Generate calendar data for activity visualization from freq_days"""
    result = []
    
    for day_key, count in student["stats"]["freq_days"].items():
        try:
            parts = day_key.split()
            if len(parts) != 2:
                continue
            
            day, month = map(int, parts)
            current_year = datetime.now().year
            date = datetime(current_year, month, day)
            
            if date.date() < start_date or date.date() > end_date:
                continue
                
            result.append({
                "date": day_key,
                "day": day,
                "month": month,
                "datetime": date,
                "count": count
            })
        except (ValueError, IndexError):
            continue
    
    return result

class PDFWithFooter(BaseDocTemplate):
    """Custom PDF document template with footer on each page"""
    
    def __init__(self, filename, footer_text, date_range=None, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        self.footer_text = footer_text
        self.date_range = date_range
        self.page_width, self.page_height = A4
        
        frame = Frame(
            self.leftMargin, 
            self.bottomMargin, 
            self.width, 
            self.height - 0.5*inch,
            id='normal'
        )
        
        template = PageTemplate(
            id='with_footer',
            frames=frame,
            onPage=self.add_footer
        )
        
        self.addPageTemplates([template])
    
    def add_footer(self, canvas, doc):
        """Add footer to each page"""
        canvas.saveState()
        canvas.setFont('Helvetica-Oblique', 8)
        
        footer_y = 0.25*inch
        canvas.drawCentredString(self.page_width/2.0, footer_y, self.footer_text)
        
        if self.date_range:
            date_text = f"Period: {self.date_range}"
            canvas.setFont('Helvetica', 8)
            canvas.drawRightString(self.page_width - 0.5*inch, footer_y, date_text)
        
        canvas.restoreState()

def generate_pdf_report(students, start_date, end_date, output_filename):
    """Generate PDF report for all students"""
    
    date_range_text = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    footer_text = "This report was automatically generated and is for informational purposes only."
    
    doc = PDFWithFooter(
        output_filename, 
        footer_text,
        date_range=date_range_text,
        pagesize=A4,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.75*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    normal_style = styles["Normal"]
    
    user_real_names = load_user_real_names()
    elements = []
    
    for student in students:
        handle = student["handle"]
        real_name = user_real_names.get(handle, "Unknown")
        
        elements.append(Paragraph(f"Name: {real_name}", title_style))
        elements.append(Paragraph(f"CF: {handle}", subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Stats overview
        elements.append(Paragraph("Stats Overview", section_style))
        
        stats_data = [
            ["Problems Attempted", "Problems Solved", "Average Difficulty", "Contests Participated"],
            [
                str(student["stats"]["attempted"]),
                str(student["stats"]["solved"]),
                str(student["stats"]["avg_difficulty"]),
                str(student["stats"]["num_contests"])
            ]
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(stats_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Daily Activity
        elements.append(Paragraph("Daily Activity", section_style))
        
        calendar_data = generate_calendar_data(student, start_date, end_date)
        
        activity_by_date = {}
        for entry in calendar_data:
            if "day" in entry and "month" in entry:
                date_key = f"{entry['day']:02d} {entry['month']:02d}"
                activity_by_date[date_key] = entry["count"]
        
        activity_data = [["Date", "Day of Week", "Problems Solved"]]
        
        current_date = start_date
        days_with_activity = 0
        
        while current_date <= end_date:
            date_key = current_date.strftime("%d %m")
            count = activity_by_date.get(date_key, 0)
            
            if count > 0:
                days_with_activity += 1
                formatted_date = current_date.strftime("%d %b %Y")
                day_of_week = current_date.strftime("%A")
                
                activity_data.append([
                    formatted_date,
                    day_of_week,
                    str(count)
                ])
            
            current_date += timedelta(days=1)
        
        if days_with_activity > 0:
            activity_table = Table(activity_data, colWidths=[1.5*inch, 2*inch, 2*inch])
            activity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(activity_table)
        else:
            elements.append(Paragraph("No activity data available for the selected period", normal_style))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Problem Tags
        elements.append(Paragraph("Problem Tags", section_style))
        
        tags = sorted(
            student["stats"]["freq_tags"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        if tags:
            tag_data = [["Tag", "Count"]]
            for tag, count in tags:
                tag_data.append([tag, str(count)])
            
            tag_table = Table(tag_data, colWidths=[4*inch, 2*inch])
            tag_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(tag_table)
        else:
            elements.append(Paragraph("No tag data available", normal_style))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Contest participation
        elements.append(Paragraph("Contest Participation", section_style))
        
        contest_data = student["stats"]["contest_result"]
        
        if contest_data:
            try:
                sorted_contests = sorted(
                    contest_data,
                    key=lambda x: datetime.strptime(x["date_time"], "%b %d %H:%M") if x["date_time"] else datetime.now(),
                    reverse=True
                )
            except:
                sorted_contests = contest_data
                
            contest_table_data = [["Date", "Contest", "Rank", "Rating", "Change"]]
            
            for contest in sorted_contests[:15]:
                rating_change = contest["new_rating"] - contest["old_rating"]
                change_text = f"+{rating_change}" if rating_change > 0 else str(rating_change)
                if contest["old_rating"] == 0 and contest["new_rating"] > 0:
                    change_text = f"+{contest['new_rating']}"
                
                contest_table_data.append([
                    contest["date_time"] if contest["date_time"] else "Unknown",
                    contest["name"],
                    str(contest["rank"]),
                    str(contest["new_rating"]) if contest["new_rating"] > 0 else "Unrated",
                    change_text if contest["new_rating"] > 0 else "Unrated"
                ])
            
            table_style = ParagraphStyle(
                'TableContent',
                parent=styles['Normal'],
                fontSize=9,
                leading=12
            )
            
            for i in range(1, len(contest_table_data)):
                contest_table_data[i][1] = Paragraph(contest_table_data[i][1], table_style)
            
            contest_table = Table(contest_table_data, colWidths=[1*inch, 3*inch, 0.7*inch, 0.7*inch, 0.7*inch])
            contest_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (4, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elements.append(contest_table)
        else:
            elements.append(Paragraph("No contest data available", normal_style))
        
        if student != students[-1]:
            elements.append(PageBreak())
    
    doc.build(elements)

def main():
    if len(sys.argv) != 3:
        print("Usage: python export_pdf.py start_date end_date")
        print("Date format: DDMMYYYY (e.g., 01012025 for January 1, 2025)")
        sys.exit(1)

    start_date = parse_date(sys.argv[1])
    end_date = parse_date(sys.argv[2])
    if start_date > end_date:
        print("Error: Start date must be before or equal to end date")
        sys.exit(1)
    print(f"Generating PDF report for period: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
    
    handles = load_handles(USER_FILE)
    if not handles:
        print(f"Error: No handles in {USER_FILE}")
        sys.exit(1)
    
    print(f"Found {len(handles)} handles: {', '.join(handles)}")
    
    start_timestamp = convert_to_unix_time(start_date.strftime("%Y-%m-%d 00:00:00"))
    end_timestamp = convert_to_unix_time(end_date.strftime("%Y-%m-%d 23:59:59"))
    
    user = []
    for handle in handles:
        try:
            print(f"Processing {handle}...")
            submission_data = load_submissions(handle, start_timestamp, end_timestamp)
            contest_data = load_contest_data(handle)
            stats = process(submission_data, contest_data)
            
            user = {
                "handle": handle,
                "stats": stats.model_dump()
            }
            user.append(user)
        except Exception as e:
            print(f"Warning: Could not process {handle}: {e}")
    
    if not user:
        print("Error: No user data could be processed")
        sys.exit(1)
    
    # Generate PDF
    output_filename = f"codeforces_report_{start_date.strftime('%d%m%Y')}_{end_date.strftime('%d%m%Y')}.pdf"
    
    try:
        generate_pdf_report(user, start_date, end_date, output_filename)
        print(f"PDF report generated successfully: {output_filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()