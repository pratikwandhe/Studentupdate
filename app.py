import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# ✅ Google Sheets setup with OAuth Scopes
def get_worksheet(sheet_name):
    try:
        # Load credentials from Streamlit secrets
        service_account_info = st.secrets["SERVICE_ACCOUNT_JSON"]
        
        # Define required OAuth scopes
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials with the specified scopes
        credentials = Credentials.from_service_account_info(
            json.loads(service_account_info),
            scopes=scopes
        )
        
        # Authorize the credentials with gspread
        client = gspread.authorize(credentials)
        
        # Open the specified Google Sheet
        return client.open(sheet_name).sheet1
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheets: {e}")
        st.stop()

# ✅ Load data from Google Sheets
def load_data(sheet):
    try:
        records = sheet.get_all_records()
        if records:
            return pd.DataFrame(records)
        else:
            return pd.DataFrame(columns=["Student Name", "Phone Number", "Date", "Update", "Update Count"])
    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=["Student Name", "Phone Number", "Date", "Update", "Update Count"])

# ✅ Save data to Google Sheets
def save_data(sheet, data):
    try:
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data to Google Sheets: {e}")

# ✅ Check for inactivity and generate alerts
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

# ✅ Main Streamlit App
st.title("📌 Real-Time Student Update System with Alerts")

# Google Sheet name
SHEET_NAME = "Student_Updates"  # Replace with your actual Google Sheet name
sheet = get_worksheet(SHEET_NAME)

# ✅ Load existing data
students_data = load_data(sheet)

# ✅ Initialize DataFrame if Empty
if students_data.empty:
    students_data = pd.DataFrame(columns=["Student Name", "Phone Number", "Date", "Update", "Update Count"])

# ✅ Debugging: Display column names
st.write("🛠 Column Names:", students_data.columns.tolist())

# ✅ Sidebar: Add New Update
st.sidebar.header("➕ Add New Student Update")
with st.sidebar.form("entry_form"):
    student_name = st.text_input("👤 Student Name")
    phone_number = st.text_input("📞 Phone Number")
    update_date = st.date_input("📅 Update Date", value=datetime.today())
    update_text = st.text_area("📝 Update")
    submit_button = st.form_submit_button("✅ Add Update")

if submit_button:
    if student_name and phone_number and update_text:
        # Check if the student already exists
        if student_name in students_data.get("Student Name", pd.Series()).values:
            existing_student = students_data[students_data["Student Name"] == student_name]
            update_count = existing_student["Update Count"].max() + 1
        else:
            update_count = 1

        # ✅ Add New Update
        new_data = {
            "Student Name": student_name,
            "Phone Number": phone_number,
            "Date": update_date.strftime("%Y-%m-%d"),
            "Update": update_text,
            "Update Count": update_count,
        }
        students_data = pd.concat([students_data, pd.DataFrame([new_data])], ignore_index=True)
        save_data(sheet, students_data)
        st.success(f"✅ Update #{update_count} added for {student_name}")
    else:
        st.error("❌ Please fill in all fields.")

# ✅ Display Student Updates
st.markdown("## 📜 Student_Updates")
if not students_data.empty:
    st.dataframe(students_data, use_container_width=True)
else:
    st.info("ℹ️ No updates added yet.")

# ✅ Generate Inactivity Alerts
alerts = check_inactivity(students_data)

st.markdown("## ⚠️ Alerts for Inactivity")
if alerts:
    st.warning("🚨 The following students have no updates in over a week:")
    for alert in alerts:
        student_name = alert["Student Name"]
        days_since_last_update = alert["Days Since Last Update"]
        st.write(f"🔴 **{student_name}** - Last update was {days_since_last_update} days ago")

        # Form to add a new update for flagged students
        with st.form(f"update_form_{student_name}"):
            st.text(f"✏️ Add a new update for {student_name}")
            next_update_date = st.date_input("📅 Update Date", value=datetime.today(), key=f"date_{student_name}")
            next_update_text = st.text_area("📝 Update", key=f"text_{student_name}")
            next_submit = st.form_submit_button(f"✅ Add Update for {student_name}")

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
                save_data(sheet, students_data)
                st.success(f"✅ Update #{current_count + 1} added for {student_name}")
else:
    st.success("✅ All students have recent updates.")

# ✅ Footer
st.markdown("<hr><p style='text-align: center;'>© 2025 SPH Team</p>", unsafe_allow_html=True)
