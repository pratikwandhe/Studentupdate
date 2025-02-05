import streamlit as st
import gspread
import json
import smtplib
from email.message import EmailMessage
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd

# ✅ Load Branch Data
@st.cache_data
def load_branch_data():
    file_path = "/mnt/data/new_branch1.xlsx"
    return pd.read_excel(file_path)

branch_data = load_branch_data()

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
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["Student Name", "District", "Branch", "Update Count"])
    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=["Student Name", "District", "Branch", "Update Count"])

# ✅ Save data to Google Sheets
def save_data(sheet, data):
    try:
        data = data.fillna("").astype(str)  # Convert NaN to string
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data to Google Sheets: {e}")

# ✅ Identify Inactive Leads
def highlight_inactivity(data):
    today = datetime.today()
    update_date_columns = [col for col in data.columns if "Update" in col and "Date" in col]
    
    if update_date_columns:
        for col in update_date_columns:
            data[col] = pd.to_datetime(data[col], errors='coerce')
        data["Last Update Date"] = data[update_date_columns].max(axis=1)
        data["Days Since Last Update"] = (today - data["Last Update Date"]).dt.days
        data["Inactive"] = data["Days Since Last Update"] > 14
    else:
        data["Inactive"] = False

    return data

# ✅ Send Email Function
def send_email(recipient, subject, body):
    sender_email = "your_email@gmail.com"
    sender_password = "your_password"
    
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient
    msg.set_content(body)
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        st.success(f"✅ Email sent to {recipient}")
    except Exception as e:
        st.error(f"❌ Email sending failed: {e}")

# ✅ Main Streamlit App
st.title("📊 Chaitrali's Lead Tracker")
st.markdown("### 📌 Manage Leads by Branch & District")

# ✅ Load Google Sheets Data
SHEET_NAME = "Student_Updates"
sheet = get_worksheet(SHEET_NAME)
students_data = load_data(sheet)

if students_data.empty:
    students_data = pd.DataFrame(columns=["Student Name", "District", "Branch", "Update Count"])

# ✅ Name Auto-Suggestion
existing_names = students_data["Student Name"].unique().tolist()
selected_name = st.sidebar.text_input("👤 Enter Lead Name", "").strip()

if selected_name:
    matching_names = [name for name in existing_names if selected_name.lower() in name.lower()]
    if matching_names:
        selected_name = st.sidebar.selectbox("📝 Select or Confirm Name", matching_names + [selected_name], index=0)

# ✅ Sidebar: Add New Lead
st.sidebar.markdown("---")
st.sidebar.header("📌 Add Lead Update")

if selected_name in students_data["Student Name"].values:
    with st.sidebar.form("update_form"):
        update_text = st.text_area("📝 Enter Update")
        update_date = st.date_input("📅 Update Date", value=datetime.today())
        submit_button = st.form_submit_button("✅ Add Update")
    
    if submit_button and update_text:
        student_row = students_data[students_data["Student Name"] == selected_name]
        update_count = int(student_row["Update Count"].values[0]) + 1
        update_text_col = f"Update {update_count} Text"
        update_date_col = f"Update {update_count} Date"

        if update_text_col not in students_data.columns:
            students_data[update_text_col] = ""
            students_data[update_date_col] = ""

        students_data.loc[students_data["Student Name"] == selected_name, update_text_col] = update_text
        students_data.loc[students_data["Student Name"] == selected_name, update_date_col] = update_date.strftime('%Y-%m-%d')
        students_data.loc[students_data["Student Name"] == selected_name, "Update Count"] = update_count

        students_data = highlight_inactivity(students_data)
        save_data(sheet, students_data)
        st.success(f"✅ Update #{update_count} added for {selected_name}")
else:
    with st.sidebar.form("entry_form"):
        district = st.selectbox("🏢 Select District", branch_data["DISTRICT"].unique())
        phone_number = st.text_input("📞 Phone Number")
        update_text = st.text_area("📝 First Update")
        update_date = st.date_input("📅 Update Date", value=datetime.today())
        submit_button = st.form_submit_button("✅ Add Lead")
    
    if submit_button and selected_name and district and phone_number and update_text:
        branch = branch_data.loc[branch_data["DISTRICT"] == district, "Branch office"].values[0]
        new_data = {
            "Student Name": selected_name,
            "District": district,
            "Branch": branch,
            "Phone Number": phone_number,
            "Update Count": 1,
            "Update 1 Text": update_text,
            "Update 1 Date": update_date.strftime('%Y-%m-%d')
        }
        students_data = pd.concat([students_data, pd.DataFrame([new_data])], ignore_index=True)
        students_data = highlight_inactivity(students_data)
        save_data(sheet, students_data)
        st.success(f"✅ Lead {selected_name} added with first update")
