import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# ✅ Google Sheets setup with OAuth Scopes
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

# ✅ Highlight inactive rows (No update in 7 days)
def highlight_inactivity(data):
    today = datetime.today()
    data["Days Since Last Update"] = (today - pd.to_datetime(data["Date"])).dt.days
    data["Inactive"] = data["Days Since Last Update"] > 7
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
    students_data = pd.DataFrame(columns=["Student Name", "Phone Number", "Date", "Update", "Update Count"])

# ✅ Name Auto-Suggestion (Dropdown)
existing_names = students_data["Student Name"].unique().tolist()
selected_name = st.sidebar.text_input("👤 Start typing a Student Name", "").strip()
suggested_names = [name for name in existing_names if selected_name.lower() in name.lower()]
if suggested_names:
    selected_name = st.sidebar.selectbox("🎯 Select a Student", suggested_names, index=0)

# ✅ Sidebar: Add New Update
st.sidebar.header("➕ Add New Student Update")
with st.sidebar.form("entry_form"):
    phone_number = st.text_input("📞 Phone Number", value="")
    update_date = st.date_input("📅 Update Date", value=datetime.today())
    update_text = st.text_area("📝 Update")
    submit_button = st.form_submit_button("✅ Add Update")

if submit_button:
    if selected_name and phone_number and update_text:
        if selected_name in students_data["Student Name"].values:
            existing_student = students_data[students_data["Student Name"] == selected_name]
            update_count = existing_student["Update Count"].max() + 1
        else:
            update_count = 1

        # ✅ Add New Update
        new_data = {
            "Student Name": selected_name,
            "Phone Number": phone_number,
            "Date": update_date.strftime("%Y-%m-%d"),
            "Update": update_text,
            "Update Count": update_count,
        }
        students_data = pd.concat([students_data, pd.DataFrame([new_data])], ignore_index=True)
        save_data(sheet, students_data)
        st.success(f"✅ Update #{update_count} added for {selected_name}")
    else:
        st.error("❌ Please fill in all fields.")

# ✅ Display Student Updates
st.markdown("## 📜 Student Updates")
if not students_data.empty:
    st.dataframe(students_data, use_container_width=True)
else:
    st.info("ℹ️ No updates added yet.")

# ✅ Generate Inactivity Alerts (Highlight & Display in UI)
students_data = highlight_inactivity(students_data)  # Ensure 'Inactive' column is added

st.markdown("## ⚠️ Alerts for Inactivity")
if "Inactive" in students_data.columns:  # Ensure 'Inactive' column exists
    alerts = students_data[students_data["Inactive"] == True]
    if not alerts.empty:
        st.warning("🚨 The following students have no updates in over a week:")
        st.dataframe(alerts[["Student Name", "Days Since Last Update"]])
    else:
        st.success("✅ All students have recent updates.")
else:
    st.error("❌ Unable to generate inactivity alerts.")

# ✅ Footer
st.markdown("<hr><p style='text-align: center;'>© 2025 SPH Team</p>", unsafe_allow_html=True)
