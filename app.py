import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import os

# Constants
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "Student_Updates"  # Replace with your Google Sheet name

# Load Google Sheets Credentials from Secrets
CREDENTIALS_FILE = "studentupdate-449023-babe5a875351.json"
if not os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, "w") as f:
        f.write(st.secrets["SERVICE_ACCOUNT_JSON"])

@st.experimental_singleton
def get_worksheet():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
    client = gspread.authorize(credentials)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

# Load data from Google Sheets
def load_data():
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

# Save data to Google Sheets
def save_data(data):
    worksheet = get_worksheet()
    worksheet.clear()  # Clear existing data
    worksheet.update([data.columns.values.tolist()] + data.values.tolist())  # Write new data

# Check for inactivity and generate alerts
def check_inactivity(data):
    today = datetime.today()
    alerts = []
    if not data.empty:
        grouped_data = data.groupby("Student Name")["Date"].max().reset_index()
        grouped_data["Days Since Last Update"] = (today - pd.to_datetime(grouped_data["Date"])).dt.days
        inactive_students = grouped_data[grouped_data["Days Since Last Update"] > 7]
        if not inactive_students.empty:
            alerts = inactive_students[["Student Name", "Days Since Last Update"]].to_dict("records")
    return alerts

# Load existing data
try:
    students_data = load_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    students_data = pd.DataFrame(columns=["Student Name", "Phone Number", "Date", "Update", "Update Count"])

# Streamlit App
st.title("Real-Time Student Update System with Alerts")

# Add new student update
st.sidebar.header("Add New Student Update")
with st.sidebar.form("entry_form"):
    student_name = st.text_input("Student Name")
    phone_number = st.text_input("Phone Number")
    update_date = st.date_input("Update Date", value=datetime.today())
    update_text = st.text_area("Update")
    submit_button = st.form_submit_button("Add Update")

if submit_button:
    if student_name and phone_number and update_text:
        # Check if the student already exists and increment the update count
        if student_name in students_data["Student Name"].values:
            existing_student = students_data[students_data["Student Name"] == student_name]
            update_count = existing_student["Update Count"].max() + 1
        else:
            update_count = 1

        # Add new update
        new_data = {
            "Student Name": student_name,
            "Phone Number": phone_number,
            "Date": update_date.strftime("%Y-%m-%d"),
            "Update": update_text,
            "Update Count": update_count,
        }
        students_data = pd.concat([students_data, pd.DataFrame([new_data])], ignore_index=True)
        try:
            save_data(students_data)
            st.success(f"Update #{update_count} added for {student_name}")
        except Exception as e:
            st.error(f"Error saving data: {e}")
    else:
        st.error("Please fill in all fields.")

# Display all student updates
st.markdown("## Student Updates")
if not students_data.empty:
    st.dataframe(students_data, use_container_width=True)
else:
    st.info("No updates added yet.")

# Generate inactivity alerts
alerts = check_inactivity(students_data)

st.markdown("## Alerts for Inactivity")
if alerts:
    st.warning("The following students have no updates in over a week:")
    for alert in alerts:
        student_name = alert["Student Name"]
        days_since_last_update = alert["Days Since Last Update"]
        st.write(f"**{student_name}** - Last update was {days_since_last_update} days ago")

        # Form to add a new update for flagged students
        with st.form(f"update_form_{student_name}"):
            st.text(f"Add a new update for {student_name}")
            next_update_date = st.date_input("Update Date", value=datetime.today(), key=f"date_{student_name}")
            next_update_text = st.text_area("Update", key=f"text_{student_name}")
            next_submit = st.form_submit_button(f"Add Update for {student_name}")

            if next_submit:
                current_count = students_data[students_data["Student Name"] == student_name]["Update Count"].max()
                new_update = {
                    "Student Name": student_name,
                    "Phone Number": students_data[students_data["Student Name"] == student_name]["Phone Number"].iloc[0],
                    "Date": next_update_date.strftime("%Y-%m-%d"),
                    "Update": next_update_text,
                    "Update Count": current_count + 1,
                }
                students_data = pd.concat([students_data, pd.DataFrame([new_update])], ignore_index=True)
                try:
                    save_data(students_data)
                    st.success(f"Update #{current_count + 1} added for {student_name}")
                except Exception as e:
                    st.error(f"Error saving data: {e}")
else:
    st.success("All students have recent updates.")

# Footer
st.markdown("<hr><p style='text-align: center;'>© 2025 SPH Team</p>", unsafe_allow_html=True)
