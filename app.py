import streamlit as st
import gspread
import json
import pandas as pd
import smtplib
from google.oauth2.service_account import Credentials
from datetime import datetime
from email.mime.text import MIMEText

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
        data = data.fillna("")
        data = data.astype(str)
        sheet.clear()
        sheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"❌ Error saving data to Google Sheets: {e}")

# ✅ Check for Inactivity
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

# ✅ Load Data
SHEET_NAME = "Student_Updates"
sheet = get_worksheet(SHEET_NAME)
students_data = load_data(sheet)
branch_data = load_branch_data()

if students_data.empty:
    students_data = pd.DataFrame(columns=["Lead Name", "District", "Branch", "Update Count"])

# ✅ Sidebar: Add New Lead or Update Form
st.sidebar.header("📌 Add or Update a Lead")

# ✅ Name Auto-Suggestion
existing_names = students_data["Lead Name"].unique().tolist()
selected_name = st.sidebar.text_input("👤 Start typing a Lead Name", "").strip()

# Dynamically show matching names
if selected_name:
    matching_names = [name for name in existing_names if selected_name.lower() in name.lower()]
    if matching_names:
        selected_name = st.sidebar.selectbox("📝 Select or Confirm Name", matching_names + [selected_name], index=0)

# ✅ If the lead exists, only ask for an update
if selected_name and selected_name in students_data["Lead Name"].values:
    st.sidebar.markdown(f"**Lead Found: {selected_name}** ✅")
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

else:
    with st.sidebar.form("entry_form"):
        district = st.selectbox("🏢 Select District", branch_data["District"].unique())
        branch = branch_data.loc[branch_data["District"] == district, "Branch"].unique()[0]
        phone_number = st.text_input("📞 Phone Number", value="")
        update_text = st.text_area("📝 First Update")
        update_date = st.date_input("📅 Update Date", value=datetime.today())
        submit_button = st.form_submit_button("✅ Add Lead")

    if submit_button and selected_name and phone_number and update_text:
        update_text_col = "Update 1 Text"
        update_date_col = "Update 1 Date"

        new_data = {
            "Lead Name": selected_name,
            "District": district,
            "Branch": branch,
            "Update Count": 1,
            update_text_col: update_text,
            update_date_col: update_date.strftime('%Y-%m-%d')
        }

        students_data = pd.concat([students_data, pd.DataFrame([new_data])], ignore_index=True)
        students_data = highlight_inactivity(students_data)
        save_data(sheet, students_data)
        st.success(f"✅ Lead {selected_name} added with first update")

# ✅ Display Leads by Branch
st.markdown("## 🏢 Leads by Branch")
for branch, group in branch_data.groupby("Branch"):
    st.markdown(f"### 🏢 {branch}")
    branch_head = group.iloc[0]
    st.write(f"**Branch Head:** {branch_head['Branch Head']}")

    branch_leads = students_data[students_data["Branch"] == branch]
    if not branch_leads.empty:
        st.dataframe(branch_leads, use_container_width=True)

        # ✅ Add a button to send email
        email_input = st.text_input(f"📧 Enter Email for {branch}")
        if st.button(f"📩 Send Leads to {branch} Branch Head"):
            if email_input:
                try:
                    msg = MIMEText(branch_leads.to_html(index=False), 'html')
                    msg['Subject'] = f"Leads Update for {branch}"
                    msg['From'] = "pratikwandhe9095@gmail.com"  # Replace with your email
                    msg['To'] = email_input

                    # Set up the SMTP server
                    with smtplib.SMTP('smtp.gmail.com', 587) as server:
                        server.starttls()
                        server.login("pratikwandhe9095@gmail.com", "fixx dnwn jpin bwix")  # Replace with your credentials
                        server.sendmail(msg['From'], msg['To'], msg.as_string())

                    st.success(f"✅ Leads sent to {email_input}")
                except Exception as e:
                    st.error(f"❌ Failed to send email: {e}")
            else:
                st.warning("⚠️ Please enter an email before sending.")

# ✅ Display Alerts for Inactive Leads
st.markdown("## ⚠️ Alerts for Inactive Leads")
students_data = highlight_inactivity(students_data)
if "Inactive" in students_data.columns:
    alerts = students_data[students_data["Inactive"] == True]
    if not alerts.empty:
        st.warning("🚨 The following leads have no updates in over 14 days:")
        st.dataframe(alerts[["Lead Name", "Days Since Last Update"]])
    else:
        st.success("✅ All leads have recent updates.")

st.markdown("<hr><p style='text-align: center;'>© 2025 Chaitrali's Lead Manager</p>", unsafe_allow_html=True)
