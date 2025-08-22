import json
import sys
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from utils import dict_to_model, get_contest_timestamp, load_users, convert_to_unix_time
from structs import Submission, Problem, ContestParticipation
from typing import Any, Dict, List

pakistan_tz = pytz.timezone("Asia/Karachi")
USER_FILE = "users.txt"
DATA_FOLDER = "data"

def load_contest_data(handle: str, start_time: int, end_time: int, data_folder: str) -> List[ContestParticipation]:
    with open(f"{data_folder}/{handle}_rating.json", "r") as f:
        contest_participations = json.load(f)
    result = []
    for cp in contest_participations:
        cp["timestamp"] = get_contest_timestamp(cp["contestId"])
        if start_time <= cp["timestamp"] < end_time:
            result.append(dict_to_model(ContestParticipation, cp))
    return result
    
def load_submissions(handle: str, start_time: int, end_time: int, data_folder: str) -> List[Submission]:
    with open(f"{data_folder}/{handle}_submissions.json") as f:
        submissions = json.load(f)
    result = []
    for submission in submissions:
        if not (start_time <= submission["creationTimeSeconds"] < end_time):
            continue
        if "verdict" not in submission:
            # unjudged due to cf system testing, skip
            continue
        submission["problem"] = dict_to_model(Problem, submission["problem"])
        submission["inContest"] = submission["author"]["participantType"] == "CONTESTANT"
        s = dict_to_model(Submission, submission)
        result.append(s)
    return result
    
def get_daily_activity(stats, start_date, end_date):
    result = []
    for date, count in stats["daily_solves"].items():
        if date < start_date or date > end_date:
            continue
        result.append({
            "date_str": date.strftime("%d %b %Y"),
            "day": date.strftime("%A"),
            "count": count
        })
    return result

class PDFWithFooter(BaseDocTemplate):
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

def generate_pdf_report(results, start_date, end_date, output_filename):
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
    
    elements = []
    
    for result in results:
        real_name, handle, stats = result["real_name"], result["handle"], result["stats"]
        elements.append(Paragraph(f"Name: {real_name}", title_style))
        elements.append(Paragraph(f"CF: {handle}", subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("Stats Overview", section_style))
        stats_data = [
            ["Problems Attempted", "Problems Solved", "Average Difficulty", "Contests Participated"],
            [
                str(stats["attempted"]),
                str(stats["solved"]),
                str(stats["avg_difficulty"]),
                str(stats["num_contests"])
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

        if stats["daily_solves"]:
            daily_table = [["Date", "Day of Week", "Problems Solved"]] 
            for date, count in stats["daily_solves"].items():
                if date < start_date or date > end_date:
                    continue
                daily_table.append([
                    date.strftime("%d %b %Y"),
                    date.strftime("%A"),
                    count
                ])
                activity_table = Table(daily_table, colWidths=[1.5*inch, 2*inch, 2*inch])
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

        elements.append(Paragraph("Problem Tags", section_style))
        tags = sorted(
            stats["tag_solves"].items(), 
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
        contest_result = stats["contest_result"]

        if contest_result:
            contest_activity_table = [["Date", "Contest", "Rank", "Rating", "Change"]]
            for c in contest_result:
                rating_change = c.newRating - c.oldRating
                change_text = f"+{rating_change}" if rating_change > 0 else str(rating_change)
                contest_activity_table.append([
                    datetime.fromtimestamp(c.timestamp, tz=pakistan_tz).strftime("%b %d %H:%M"),
                    c.contestName,
                    str(c.rank),
                    str(c.newRating),
                    change_text
                ])
            table_style = ParagraphStyle(
                'TableContent',
                parent=styles['Normal'],
                fontSize=9,
                leading=12
            )
            for i in range(1, len(contest_activity_table)):
                contest_activity_table[i][1] = Paragraph(contest_activity_table[i][1], table_style)
            contest_table = Table(contest_activity_table, colWidths=[1*inch, 3*inch, 0.7*inch, 0.7*inch, 0.7*inch])
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

        if result != results[-1]:
            elements.append(PageBreak())
    
    doc.build(elements)

def compute_stats(submissions: List[Submission], contest_participations: List[ContestParticipation]) -> Dict[str, Any]:
    num_solved = 0
    sum_difficulty = 0
    problems_calculated = 0
    solved_problems = []
    daily_solves = dict()
    tag_solves = dict()
    contest_ids = set()
    for submission in submissions:
        if submission.verdict != "OK":
            continue
        num_solved += 1
        sum_difficulty += submission.problem.rating
        if submission.problem.rating > 0:
            problems_calculated += 1
        solved_problems.append(submission.problem)
        date = datetime.fromtimestamp(submission.creationTimeSeconds, tz=pakistan_tz).date()
        if date not in daily_solves:
            daily_solves[date] = 0
        daily_solves[date] += 1
        for tag in submission.problem.tags:
            if tag not in tag_solves:
                tag_solves[tag] = 0
            tag_solves[tag] += 1
        if submission.inContest:
            contest_ids.add(submission.contestId)

    if problems_calculated == 0:
        avg_difficulty = 0
    else:
        avg_difficulty = sum_difficulty / problems_calculated
    avg_difficulty = round(avg_difficulty / 50) * 50
    contest_activity = [cp for cp in contest_participations if cp.contestId in contest_ids]
    return {
        "attempted": len(submissions),
        "solved": num_solved,
        "avg_difficulty": avg_difficulty,
        "problems": solved_problems,
        "daily_solves": daily_solves,
        "tag_solves": tag_solves,
        "num_contests": len(contest_ids),
        "contest_result": contest_activity
    }

def load_and_compute_stats(handle: str, start_timestamp: int, end_timestamp: int, data_folder: str):
    submission_data = load_submissions(handle, start_timestamp, end_timestamp, data_folder)
    contest_data = load_contest_data(handle, start_timestamp, end_timestamp, data_folder)
    stats = compute_stats(submission_data, contest_data)
    return stats

def main():
    if len(sys.argv) != 3:
        print("Usage: python export_pdf.py start_date end_date")
        print("Date format: DDMMYYYY (e.g., 01012025 for January 1, 2025)")
        sys.exit(1)

    start_date = datetime.strptime(sys.argv[1], "%d%m%Y").date()
    end_date = datetime.strptime(sys.argv[2], "%d%m%Y").date()
    if start_date > end_date:
        print("Error: Start date must be before or equal to end date")
        sys.exit(1)
    print(f"Generating PDF report for period: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
    
    real_names, handles = load_users(USER_FILE)
    if not handles:
        print(f"Error: No handles in {USER_FILE}")
        sys.exit(1)
    
    print(f"Found {len(handles)} handles: {', '.join(handles)}")
    
    start_timestamp = convert_to_unix_time(start_date.strftime("%Y-%m-%d 00:00:00"), pakistan_tz)
    end_timestamp = convert_to_unix_time(end_date.strftime("%Y-%m-%d 23:59:59"), pakistan_tz)
    
    results = []
    for real_name, handle in zip(real_names, handles):
        print(f"Processing {handle}...")
        results.append({
            "real_name": real_name,
            "handle": handle,
            "stats": load_and_compute_stats(handle, start_timestamp, end_timestamp, DATA_FOLDER)
        })
    
    if not results:
        print("Error: No user data could be processed")
        sys.exit(1)
    
    # Generate PDF
    output_filename = f"codeforces_report_{start_date.strftime('%d%m%Y')}_{end_date.strftime('%d%m%Y')}.pdf"
    generate_pdf_report(results, start_date, end_date, output_filename)
    print(f"PDF report generated successfully: {output_filename}")

if __name__ == "__main__":
    main()