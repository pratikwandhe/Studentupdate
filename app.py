import streamlit as st
import gspread
import json
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ✅ Page Configuration
st.set_page_config(page_title="Chaitrali's Lead Tracker", page_icon="📊", layout="wide")

# ✅ Load Branch Data
@st.cache_resource
def load_branch_data():
    return pd.read_excel("new_branch1.xlsx")

branch_data = load_branch_data()

# ✅ Google Sheets Setup
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

# ✅ Load Data from Google Sheets
def load_data(sheet):
    try:
        records = sheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["Student Name", "Phone Number", "District", "Update Count"])
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame(columns=["Student Name", "Phone Number", "District", "Update Count"])

# ✅ Save Data to Google Sheets
def save_data(sheet, data):
    try:
        data = data.fillna("").astype(str)
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")

# ✅ Highlight Inactivity (No Update in 14 Days)
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

# ✅ Function to Send Email
def send_email(recipient, subject, body):
    sender_email = "pratikwandhe9095.com"
    sender_password = "fixx dnwn jpin bwix"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
        return False

# ✅ Main Streamlit App
st.title("📊 Chaitrali's Lead Tracker")

# Google Sheet
SHEET_NAME = "Lead_Tracker"
sheet = get_worksheet(SHEET_NAME)
students_data = load_data(sheet)

# Initialize Data
if students_data.empty:
    students_data = pd.DataFrame(columns=["Student Name", "Phone Number", "District", "Update Count"])

# ✅ Sidebar: Add New Lead
st.sidebar.header("➕ Add New Lead")
selected_name = st.sidebar.text_input("👤 Lead Name", "").strip()

# ✅ Auto-suggestion for existing names
existing_names = students_data["Student Name"].unique().tolist()
matching_names = [name for name in existing_names if selected_name.lower() in name.lower()]
if matching_names:
    selected_name = st.sidebar.selectbox("📝 Select or Confirm Name", matching_names + [selected_name], index=0)

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

# ✅ Display Leads by Branch
for branch, group in branch_data.groupby("Branch"):
    st.markdown(f"### 🏢 {branch}")
    branch_head = group.iloc[0]
    st.write(f"**Branch Head:** {branch_head['Branch Head']} | 📧 {branch_head['Email']} | 📞 {branch_head['Phone']}")

    branch_leads = students_data[students_data["District"].isin(group["District"])]
    st.dataframe(branch_leads)

    if st.button(f"📧 Send Updates to {branch_head['Branch Head']}", key=branch):
        email_body = branch_leads.to_string()
        if send_email(branch_head["Email"], f"Leads for {branch}", email_body):
            st.success(f"✅ Email sent to {branch_head['Branch Head']}")

st.markdown("<hr><p style='text-align: center;'>© 2025 Chaitrali's Lead Manager</p>", unsafe_allow_html=True)
