import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd

# ✅ Google Sheets setup
def get_worksheet(sheet_name):
    try:
        service_account_info = st.secrets["SERVICE_ACCOUNT_JSON"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(json.loads(service_account_info), scopes=scopes)
        client = gspread.authorize(credentials)
        return client.open(sheet_name).sheet1
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheets: {e}")
        st.stop()

# ✅ Load data from Google Sheets
def load_data(sheet):
    try:
        records = sheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["Student Name", "Phone Number", "Update Count"])
    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=["Student Name", "Phone Number", "Update Count"])

# ✅ Save data to Google Sheets
def save_data(sheet, data):
    try:
        # Convert all NaN/None values to empty strings
        data = data.fillna("")
        
        # Ensure all values are strings before saving (Google Sheets expects string-like values)
        data = data.astype(str)
        
        # Save data to Google Sheets
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data to Google Sheets: {e}")

# ✅ Highlight inactive students (No update in 14 days)
def highlight_inactivity(data):
    today = datetime.today()
    
    # 🔹 Find the latest update date for each student
    update_date_columns = [col for col in data.columns if "Update" in col and "Date" in col]
    if update_date_columns:
        data["Last Update Date"] = data[update_date_columns].max(axis=1)
        data["Last Update Date"] = pd.to_datetime(data["Last Update Date"], errors='coerce')
        data["Days Since Last Update"] = (today - data["Last Update Date"]).dt.days

        # 🔹 Mark as inactive if last update was more than 14 days ago
        data["Inactive"] = data["Days Since Last Update"] > 14
    else:
        data["Inactive"] = False  # If no updates, don't mark inactive

    return data

# ✅ Main Streamlit App
st.title("📌 Real-Time Student Update System with Alerts")

# Google Sheet name
SHEET_NAME = "Student_Updates"
sheet = get_worksheet(SHEET_NAME)

# ✅ Load existing data
students_data = load_data(sheet)

# ✅ Initialize DataFrame if Empty
if students_data.empty:
    students_data = pd.DataFrame(columns=["Student Name", "Phone Number", "Update Count"])

# ✅ Name Auto-Suggestion
existing_names = students_data["Student Name"].unique().tolist()

# 🔹 Implement Name Autocomplete
selected_name = st.sidebar.text_input("👤 Start typing a Student Name", "").strip()

# 🔹 Show matching suggestions inline
if selected_name:
    matching_names = [name for name in existing_names if selected_name.lower() in name.lower()]
    if matching_names:
        selected_name = st.sidebar.selectbox("📝 Select or Confirm Name", matching_names + [selected_name], index=0)

# ✅ Sidebar: Add New Update (Only Ask for Update if Name Exists)
st.sidebar.header("➕ Add New Student Update")

if selected_name in students_data["Student Name"].values:
    # 🔹 Student Exists → Only Ask for Update
    with st.sidebar.form("update_form"):
        update_text = st.text_area("📝 Enter Update")
        update_date = st.date_input("📅 Update Date", value=datetime.today())
        submit_button = st.form_submit_button("✅ Add Update")

    if submit_button and update_text:
        student_row = students_data[students_data["Student Name"] == selected_name]
        update_count = int(student_row["Update Count"].values[0]) + 1
        update_text_col = f"Update {update_count} Text"
        update_date_col = f"Update {update_count} Date"

        # 🔹 Append new update and date as new columns
        if update_text_col not in students_data.columns:
            students_data[update_text_col] = ""
            students_data[update_date_col] = ""

        students_data.loc[students_data["Student Name"] == selected_name, update_text_col] = update_text
        students_data.loc[students_data["Student Name"] == selected_name, update_date_col] = update_date.strftime('%Y-%m-%d')
        students_data.loc[students_data["Student Name"] == selected_name, "Update Count"] = update_count

        # ✅ Highlight inactivity
        students_data = highlight_inactivity(students_data)

        # ✅ Save updated data
        save_data(sheet, students_data)
        st.success(f"✅ Update #{update_count} added for {selected_name}")

else:
    # 🔹 New Student → Ask for Full Details
    with st.sidebar.form("entry_form"):
        phone_number = st.text_input("📞 Phone Number", value="")
        update_text = st.text_area("📝 First Update")
        update_date = st.date_input("📅 Update Date", value=datetime.today())
        submit_button = st.form_submit_button("✅ Add Student")

    if submit_button and selected_name and phone_number and update_text:
        update_text_col = "Update 1 Text"
        update_date_col = "Update 1 Date"

        # 🔹 Add New Student Entry
        new_data = {
            "Student Name": selected_name,
            "Phone Number": phone_number,
            "Update Count": 1,
            update_text_col: update_text,
            update_date_col: update_date.strftime('%Y-%m-%d')
        }
        
        students_data = pd.concat([students_data, pd.DataFrame([new_data])], ignore_index=True)
        
        # ✅ Highlight inactivity
        students_data = highlight_inactivity(students_data)

        # ✅ Save updated data
        save_data(sheet, students_data)
        st.success(f"✅ Student {selected_name} added with first update")

# ✅ Display Student Updates (Single Row per Student)
st.markdown("## 📜 Student Updates")
if not students_data.empty:
    st.dataframe(students_data, use_container_width=True)
else:
    st.info("ℹ️ No updates added yet.")

# ✅ Generate Inactivity Alerts (Highlight & Display in UI)
students_data = highlight_inactivity(students_data)  # Ensure 'Inactive' column is added

st.markdown("## ⚠️ Alerts for Inactivity")
if "Inactive" in students_data.columns:
    alerts = students_data[students_data["Inactive"] == True]
    if not alerts.empty:
        st.warning("🚨 The following students have no updates in over 14 days:")
        st.dataframe(alerts[["Student Name", "Days Since Last Update"]])
    else:
        st.success("✅ All students have recent updates.")
else:
    st.error("❌ Unable to generate inactivity alerts.")

# ✅ Footer
st.markdown("<hr><p style='text-align: center;'>© 2025 SPH Team</p>", unsafe_allow_html=True)
