import streamlit as st
import gspread
import json
import pandas as pd
import smtplib
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# ✅ Page Configuration
st.set_page_config(
    page_title="Chaitrali's Lead Tracker",
    page_icon="📊",
    layout="wide"
)

# ✅ Custom CSS for UI Styling
st.markdown("""
    <style>
        body {
            background-color: #f8f9fa;
        }
        .block-container {
            padding-top: 1rem;
        }
        h1, h2, h3 {
            color: #2b6777;
        }
        .stButton>button {
            background-color: #52b69a !important;
            color: white !important;
            border-radius: 10px !important;
            padding: 8px 16px !important;
        }
        .stDataFrame {
            border: 1px solid #2b6777;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

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

# ✅ Load data from Google Sheets
def load_data(sheet):
    try:
        records = sheet.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame(columns=["Lead Name", "District", "Branch", "Update Count"])
    except Exception as e:
        st.error(f"❌ Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=["Lead Name", "District", "Branch", "Update Count"])

# ✅ Load Branch Data from Excel
@st.cache_data
def load_branch_data():
    try:
        branch_df = pd.read_excel("new_branch1.xlsx")
        return branch_df
    except Exception as e:
        st.error(f"❌ Error loading branch data: {e}")
        return pd.DataFrame(columns=["State", "Branch", "District", "Branch Head"])

# ✅ Save data to Google Sheets
def save_data(sheet, data):
    try:
        data = data.fillna("")  # Replace NaN with empty string
        data = data.astype(str)  # Convert everything to string before saving
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data to Google Sheets: {e}")

# ✅ Highlight inactive leads (No update in 14 days)
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

# ✅ Email Functionality
def send_email(email_to, subject, message):
    sender_email = "pratikwandhe9095@gmail.com"
    sender_password = "fixx dnwn jpin bwix"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            email_message = f"Subject: {subject}\n\n{message}"
            server.sendmail(sender_email, email_to, email_message)
        return True
    except Exception as e:
        st.error(f"❌ Error sending email: {e}")
        return False

# ✅ Load Data
SHEET_NAME = "Student_Updates"
sheet = get_worksheet(SHEET_NAME)
students_data = load_data(sheet)
branch_data = load_branch_data()

if students_data.empty:
    students_data = pd.DataFrame(columns=["Lead Name", "District", "Branch", "Update Count"])

# ✅ Sidebar: Add New Update Form
st.sidebar.header("📌 Add New Lead Update")

# ✅ Name Auto-Suggestion
existing_names = students_data["Lead Name"].unique().tolist()
selected_name = st.sidebar.text_input("👤 Start typing a Lead Name", "").strip()

if selected_name:
    matching_names = [name for name in existing_names if selected_name.lower() in name.lower()]
    if matching_names:
        selected_name = st.sidebar.selectbox("📝 Select or Confirm Name", matching_names + [selected_name], index=0)

# ✅ If the lead exists, only ask for an update
if selected_name in students_data["Lead Name"].values:
    with st.sidebar.form("update_form"):
        update_text = st.text_area("📝 Enter Update")
        update_date = st.date_input("📅 Update Date", value=datetime.today())
        submit_button = st.form_submit_button("✅ Add Update")

    if submit_button and update_text:
        student_row = students_data[students_data["Lead Name"] == selected_name]
        update_count = int(student_row["Update Count"].values[0]) + 1
        update_text_col = f"Update {update_count} Text"
        update_date_col = f"Update {update_count} Date"

        if update_text_col not in students_data.columns:
            students_data[update_text_col] = ""
            students_data[update_date_col] = ""

        students_data.loc[students_data["Lead Name"] == selected_name, update_text_col] = update_text
        students_data.loc[students_data["Lead Name"] == selected_name, update_date_col] = update_date.strftime('%Y-%m-%d')
        students_data.loc[students_data["Lead Name"] == selected_name, "Update Count"] = update_count

        save_data(sheet, students_data)
        st.success(f"✅ Update #{update_count} added for {selected_name}")

# ✅ Display Leads by Branch
st.markdown("## 🏢 Leads by Branch")
for branch, group in branch_data.groupby("Branch"):
    st.markdown(f"### 🏢 {branch}")
    branch_head = group.iloc[0]
    st.write(f"**Branch Head:** {branch_head['Branch Head']}")

    branch_leads = students_data[students_data["Branch"] == branch]
    if not branch_leads.empty:
        st.dataframe(branch_leads, use_container_width=True)

st.markdown("<hr><p style='text-align: center;'>© 2025 Chaitrali's Lead Manager</p>", unsafe_allow_html=True)
