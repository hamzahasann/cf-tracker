import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import datetime as dt
from fpdf import FPDF
import tempfile
import os
import base64

# Set page config
st.set_page_config(
    page_title="Codeforces Activity Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS to increase heading font sizes
st.markdown("""
<style>
h1 {
    font-size: 2.8rem !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
}
h2 {
    font-size: 2.2rem !important;
    font-weight: 500 !important;
    margin-bottom: 0.8rem !important;
}
h3 {
    font-size: 1.8rem !important;
    font-weight: 500 !important;
    margin-bottom: 0.6rem !important;
}
h4 {
    font-size: 1.4rem !important;
    font-weight: 500 !important;
    margin-bottom: 0.5rem !important;
}
.sidebar .block-container {
    padding-top: 2rem !important;
}
.sidebar h1, .sidebar h2 {
    font-size: 1.8rem !important;
}
</style>
""", unsafe_allow_html=True)

# Load data from data.json
@st.cache_data
def load_data():
    with open("data.json", "r") as f:
        return json.load(f)
    
# Data Normalization
@st.cache_data
def normalize_data(data):
    # Problems DataFrame
    problems_list = []
    for student_data in data:
        handle = student_data["handle"]
        stats = student_data["stats"]
        
        # Extract problems
        for problem in stats["problems"]:
            problem_dict = {
                "student": handle,
                "contest_id": problem["contest_id"],
                "index": problem["index"],
                "name": problem["name"],
                "rating": problem["rating"],
                "tags": problem["tags"]
            }
            problems_list.append(problem_dict)
            
    problems_df = pd.DataFrame(problems_list)
    
    # Explode tags column to have one tag per row
    tags_df = problems_df.explode("tags").rename(columns={"tags": "tag"})
    
    # Contests DataFrame
    contests_list = []
    for student_data in data:
        handle = student_data["handle"]
        stats = student_data["stats"]
        
        # Extract contest results
        for contest in stats["contest_result"]:
            contest_dict = {
                "student": handle,
                "contest_id": contest["contest_id"],
                "name": contest["name"],
                "old_rating": contest["old_rating"],
                "new_rating": contest["new_rating"],
                "rank": contest["rank"],
            }
            contests_list.append(contest_dict)
            
    contests_df = pd.DataFrame(contests_list)
    
    # Daily Activity DataFrame
    activity_list = []
    for student_data in data:
        handle = student_data["handle"]
        stats = student_data["stats"]
        
        # Extract daily activity
        for day, count in stats["freq_days"].items():
            # Convert "DD MM" to a full date in current year
            day_parts = day.split()
            if len(day_parts) == 2:
                day_str = f"{day_parts[0]}-{day_parts[1]}-{datetime.now().year}"
                date_obj = datetime.strptime(day_str, "%d-%m-%Y")
                
                activity_dict = {
                    "student": handle,
                    "date": date_obj,
                    "count": count
                }
                activity_list.append(activity_dict)
    
    activity_df = pd.DataFrame(activity_list)
    
    # Calculate tag frequencies
    tag_counts = {}
    for student_data in data:
        handle = student_data["handle"]
        stats = student_data["stats"]
        tag_counts[handle] = stats["freq_tags"]
    
    return problems_df, tags_df, contests_df, activity_df, tag_counts

def create_pdf(selected_students, date_range, fig1, fig2, fig3, contest_df):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Codeforces Activity Dashboard", ln=True, align="C")
    
    # Selected students
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, f"Students: {', '.join(selected_students)}", ln=True)
    
    # Date range
    pdf.cell(190, 10, f"Date Range: {date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}", ln=True)
    
    # Save plot images to temp files
    plot_paths = []
    
    # Use temporary directory for plots
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Rating progression
        if fig1:
            plot_path1 = os.path.join(tmpdirname, "rating_plot.png")
            fig1.write_image(plot_path1, width=800, height=400)
            plot_paths.append({"title": "Rating Progression", "path": plot_path1})
        
        # Activity calendar
        if fig2:
            plot_path2 = os.path.join(tmpdirname, "activity_plot.png")
            fig2.write_image(plot_path2, width=800, height=400)
            plot_paths.append({"title": "Activity Calendar", "path": plot_path2})
        
        # Tag frequency
        if fig3:
            plot_path3 = os.path.join(tmpdirname, "tag_plot.png")
            fig3.write_image(plot_path3, width=800, height=400)
            plot_paths.append({"title": "Tag Frequency", "path": plot_path3})
        
        # Add plots to PDF
        for plot in plot_paths:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(190, 10, plot["title"], ln=True)
            pdf.image(plot["path"], x=10, y=30, w=190)
        
        # Add contest table to PDF
        if not contest_df.empty:
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(190, 10, "Contest Participation", ln=True)
            
            # Table header
            pdf.set_font("Arial", "B", 10)
            pdf.cell(20, 10, "Student", border=1)
            pdf.cell(20, 10, "Contest ID", border=1)
            pdf.cell(80, 10, "Name", border=1)
            pdf.cell(25, 10, "Old Rating", border=1)
            pdf.cell(25, 10, "New Rating", border=1)
            pdf.cell(20, 10, "Rank", border=1, ln=True)
            
            # Table data
            pdf.set_font("Arial", "", 8)
            for _, row in contest_df.iterrows():
                pdf.cell(20, 10, str(row["student"]), border=1)
                pdf.cell(20, 10, str(row["contest_id"]), border=1)
                # Truncate contest name if too long
                name = row["name"]
                if len(name) > 40:
                    name = name[:37] + "..."
                pdf.cell(80, 10, name, border=1)
                pdf.cell(25, 10, str(row["old_rating"]), border=1)
                pdf.cell(25, 10, str(row["new_rating"]), border=1)
                pdf.cell(20, 10, str(row["rank"]), border=1, ln=True)
        
        # Save PDF to a bytes buffer
        pdf_buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf_output = pdf_buffer.name
        pdf.output(pdf_output)
        
        # Read the buffer
        with open(pdf_output, "rb") as f:
            pdf_data = f.read()
        
        # Clean up
        os.unlink(pdf_output)
    
    return pdf_data

def main():
    # Title
    st.title("Codeforces Activity Dashboard")
    st.markdown("<p style='font-size: 1.4rem; margin-top: -0.8rem;'>Track and compare Codeforces activity for students</p>", unsafe_allow_html=True)
    
    # Load and normalize data
    data = load_data()
    problems_df, tags_df, contests_df, activity_df, tag_counts = normalize_data(data)
    
    # Sidebar
    with st.sidebar:
        st.header("Filters")
        
        # Student selector
        all_students = sorted(list(set([s["handle"] for s in data])))
        selected_students = st.multiselect(
            "Select Students (max 2):",
            all_students,
            default=all_students[:1] if all_students else []
        )
        
        if len(selected_students) > 2:
            st.warning("Please select at most 2 students for comparison")
            selected_students = selected_students[:2]
        
        # Date range picker
        min_date = activity_df["date"].min() if not activity_df.empty else datetime.now() - timedelta(days=30)
        max_date = activity_df["date"].max() if not activity_df.empty else datetime.now()
        
        date_range = st.date_input(
            "Select Date Range:",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
        
        # If only one date is selected, use it for both start and end
        if isinstance(date_range, dt.date):
            date_range = (date_range, date_range)
        
        # Make sure we have two dates
        if len(date_range) < 2:
            date_range = (date_range[0], date_range[0])
        
        # Tag filter
        all_tags = sorted(list(set(tags_df["tag"].dropna())))
        selected_tags = st.multiselect(
            "Filter by Tags:",
            all_tags
        )
        
        # Contest ID filter
        all_contest_ids = sorted(list(set(contests_df["contest_id"])))
        selected_contests = st.multiselect(
            "Filter by Contest IDs:",
            all_contest_ids
        )
    
    # Filter data based on selections
    if not selected_students:
        st.warning("Please select at least one student")
        return
    
    # Filter by students
    filtered_problems = problems_df[problems_df["student"].isin(selected_students)]
    filtered_tags = tags_df[tags_df["student"].isin(selected_students)]
    filtered_contests = contests_df[contests_df["student"].isin(selected_students)]
    filtered_activity = activity_df[activity_df["student"].isin(selected_students)]
    
    # Filter by date range
    date_start = datetime.combine(date_range[0], datetime.min.time())
    date_end = datetime.combine(date_range[1], datetime.max.time())
    filtered_activity = filtered_activity[(filtered_activity["date"] >= date_start) & (filtered_activity["date"] <= date_end)]
    
    # Filter by tags if any selected
    if selected_tags:
        filtered_tags = filtered_tags[filtered_tags["tag"].isin(selected_tags)]
        # Get contest_ids from filtered tags
        contest_ids_with_tags = filtered_tags["contest_id"].unique().tolist()
        filtered_problems = filtered_problems[filtered_problems["contest_id"].isin(contest_ids_with_tags)]
    
    # Filter by contest IDs if any selected
    if selected_contests:
        filtered_contests = filtered_contests[filtered_contests["contest_id"].isin(selected_contests)]
        filtered_problems = filtered_problems[filtered_problems["contest_id"].isin(selected_contests)]
    
    # Main panel
    # Create two columns for the main panel
    col1, col2 = st.columns(2)
    
    # Rating progression (col1)
    with col1:
        st.markdown("<h3>Rating Progression</h3>", unsafe_allow_html=True)
        if filtered_contests.empty:
            st.info("No contest data available for the selected filters")
            rating_fig = None
        else:
            # Prepare data for rating plot
            rating_data = []
            for student in selected_students:
                student_contests = filtered_contests[filtered_contests["student"] == student].sort_values("contest_id")
                
                if not student_contests.empty:
                    # Add initial rating point
                    rating_data.append({
                        "student": student,
                        "contest_id": student_contests.iloc[0]["contest_id"] - 0.5,
                        "rating": student_contests.iloc[0]["old_rating"],
                        "name": "Initial"
                    })
                    
                    # Add rating points from contests
                    for _, row in student_contests.iterrows():
                        rating_data.append({
                            "student": row["student"],
                            "contest_id": row["contest_id"],
                            "rating": row["new_rating"],
                            "name": row["name"]
                        })
            
            rating_df = pd.DataFrame(rating_data)
            
            if not rating_df.empty:
                rating_fig = px.line(
                    rating_df,
                    x="contest_id",
                    y="rating",
                    color="student",
                    markers=True,
                    hover_data=["name"],
                    title="Codeforces Rating Progression"
                )
                rating_fig.update_layout(
                    xaxis_title="Contest ID", 
                    yaxis_title="Rating",
                    title_font=dict(size=18),
                    legend_title_font=dict(size=14),
                    legend_font=dict(size=12)
                )
                st.plotly_chart(rating_fig, use_container_width=True)
            else:
                st.info("No rating data available for the selected filters")
                rating_fig = None
    
    # Activity calendar (col2)
    with col2:
        st.markdown("<h3>Activity Calendar</h3>", unsafe_allow_html=True)
        if filtered_activity.empty:
            st.info("No activity data available for the selected filters")
            activity_fig = None
        else:
            # Prepare data for activity calendar
            activity_pivot = filtered_activity.pivot_table(
                index="student",
                columns="date",
                values="count",
                aggfunc="sum",
                fill_value=0
            )
            
            if activity_pivot.empty:
                st.info("No activity data available for the selected date range")
                activity_fig = None
            else:
                # Convert to long format for plotting
                activity_long = filtered_activity.copy()
                
                # Format date for better display
                activity_long["date_str"] = activity_long["date"].dt.strftime("%Y-%m-%d")
                
                activity_fig = px.bar(
                    activity_long,
                    x="date_str",
                    y="count",
                    color="student",
                    barmode="group",
                    title="Daily Problems Solved"
                )
                activity_fig.update_layout(
                    xaxis_title="Date", 
                    yaxis_title="Problems Solved",
                    title_font=dict(size=18),
                    legend_title_font=dict(size=14),
                    legend_font=dict(size=12)
                )
                st.plotly_chart(activity_fig, use_container_width=True)
    
    # Tag frequency (full width)
    st.markdown("<h3>Tag Frequency</h3>", unsafe_allow_html=True)
    if filtered_tags.empty:
        st.info("No tag data available for the selected filters")
        tag_fig = None
    else:
        # Count tags by student
        tag_freq = filtered_tags.groupby(["student", "tag"]).size().reset_index(name="count")
        
        if tag_freq.empty:
            st.info("No tag data available for the selected filters")
            tag_fig = None
        else:
            tag_fig = px.bar(
                tag_freq,
                x="tag",
                y="count",
                color="student",
                barmode="group",
                title="Problem Tags Frequency"
            )
            tag_fig.update_layout(
                xaxis_title="Tag", 
                yaxis_title="Count",
                title_font=dict(size=18),
                legend_title_font=dict(size=14),
                legend_font=dict(size=12)
            )
            st.plotly_chart(tag_fig, use_container_width=True)
    
    # Contest participation table (full width)
    st.markdown("<h3>Contest Participation</h3>", unsafe_allow_html=True)
    if filtered_contests.empty:
        st.info("No contest data available for the selected filters")
    else:
        # Calculate rating change
        filtered_contests["rating_change"] = filtered_contests["new_rating"] - filtered_contests["old_rating"]
        
        # Style the dataframe
        st.dataframe(
            filtered_contests[["student", "contest_id", "name", "old_rating", "new_rating", "rating_change", "rank"]],
            use_container_width=True,
            column_config={
                "rating_change": st.column_config.NumberColumn(
                    "Rating Change",
                    format="%d",
                    help="Change in rating from the contest"
                )
            }
        )
    
    # PDF export button
    st.markdown("<h3>Export Dashboard</h3>", unsafe_allow_html=True)
    if selected_students and not (rating_fig is None and activity_fig is None and tag_fig is None and filtered_contests.empty):
        pdf_data = create_pdf(selected_students, date_range, rating_fig, activity_fig, tag_fig, filtered_contests)
        
        st.download_button(
            label="Download PDF Report",
            data=pdf_data,
            file_name=f"codeforces_report_{date_range[0].strftime('%Y%m%d')}-{date_range[1].strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Select at least one student and ensure there is data to include in the report")

if __name__ == "__main__":
    main() 