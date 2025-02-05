import streamlit as st
import gspread
import json
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ✅ Page Config for Custom Look
st.set_page_config(
    page_title="Chaitrali's Lead Tracker",
    page_icon="📊",
    layout="wide"
)

# ✅ Custom CSS for Styling
st.markdown("""
    <style>
        body { background-color: #f8f9fa; }
        .block-container { padding-top: 1rem; }
        h1, h2, h3 { color: #2b6777; }
        .stButton>button {
            background-color: #52b69a !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 8px 16px !important;
        }
        .stDataFrame { border: 1px solid #2b6777; border-radius: 10px; }
        .stTextInput>div>div>input {
            border-radius: 5px !important;
            border: 1px solid #2b6777 !important;
        }
    </style>
""", unsafe_allow_html=True)

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
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["Student Name", "Phone Number", "District", "Branch", "Update Count"])
    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=["Student Name", "Phone Number", "District", "Branch", "Update Count"])

# ✅ Save data to Google Sheets
def save_data(sheet, data):
    try:
        data = data.fillna("")  
        data = data.astype(str)  
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data to Google Sheets: {e}")

# ✅ Highlight inactive students (No update in 14 days)
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

# ✅ Load Branch Mapping Data
branch_data = pd.read_excel("new branch.xlsx")  
branch_dict = branch_data.set_index("District").to_dict("index")  

# ✅ Main Streamlit App
st.title("📊 Chaitrali's Lead Tracker")
st.markdown("### 📌 Manage Your Leads & Stay Updated")

# Google Sheet name
SHEET_NAME = "Student_Updates"
sheet = get_worksheet(SHEET_NAME)

# ✅ Load existing data
students_data = load_data(sheet)

# ✅ Initialize DataFrame if Empty
if students_data.empty:
    students_data = pd.DataFrame(columns=["Student Name", "Phone Number", "District", "Branch", "Update Count"])

# ✅ Name Auto-Suggestion
existing_names = students_data["Student Name"].unique().tolist()

# 🔍 Name Autocomplete Feature
selected_name = st.sidebar.text_input("👤 Start typing a Lead Name", "").strip()

if selected_name:
    matching_names = [name for name in existing_names if selected_name.lower() in name.lower()]
    if matching_names:
        selected_name = st.sidebar.selectbox("📝 Select or Confirm Name", matching_names + [selected_name], index=0)

# ✅ Sidebar: Add New Update (Only Ask for Update if Name Exists)
st.sidebar.markdown("---")
st.sidebar.header("📌 Add New Lead Update")

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
st.markdown("## 📜 Leads by Branch")
branches = students_data["Branch"].unique()

for branch in branches:
    branch_leads = students_data[students_data["Branch"] == branch]
    branch_head = branch_dict.get(branch, {}).get("Branch Head", "Unknown")
    branch_email = branch_dict.get(branch, {}).get("Email", "N/A")
    branch_phone = branch_dict.get(branch, {}).get("Phone", "N/A")

    st.subheader(f"🏢 {branch} Branch")
    st.markdown(f"**Branch Head:** {branch_head} | 📧 {branch_email} | 📞 {branch_phone}")

    st.dataframe(branch_leads, use_container_width=True)

    email_input = st.text_input(f"📩 Enter Email to Send Leads for {branch}")
    if st.button(f"📤 Send to {branch_head}"):
        send_email(email_input, branch_leads)
        st.success(f"✅ Email sent to {email_input}")

# ✅ Function to Send Emails
def send_email(recipient_email, lead_data):
    sender_email = "your-email@gmail.com"
    sender_password = "your-app-password"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = "Lead Updates for Your Branch"
    
    body = lead_data.to_html(index=False)
    message.attach(MIMEText(body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

st.markdown("<hr><p style='text-align: center;'>© 2025 Chaitrali's Lead Manager</p>", unsafe_allow_html=True)
