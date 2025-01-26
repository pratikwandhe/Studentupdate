import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Initialize session state for storing data
if "students_data" not in st.session_state:
    st.session_state["students_data"] = pd.DataFrame(
        columns=["Student Name", "Phone Number", "Date", "Update"]
    )

# Function to check for inactivity and alert
def check_inactivity(data):
    today = datetime.today()
    alerts = []
    if not data.empty:
        # Group data by student and find the most recent update for each
        grouped_data = data.groupby("Student Name")["Date"].max().reset_index()
        grouped_data["Date"] = pd.to_datetime(grouped_data["Date"])
        grouped_data["Days Since Last Update"] = (today - grouped_data["Date"]).dt.days

        # Find students with no updates in over a week
        inactive_students = grouped_data[grouped_data["Days Since Last Update"] > 7]
        if not inactive_students.empty:
            alerts = inactive_students[["Student Name", "Days Since Last Update"]].to_dict(
                "records"
            )
    return alerts

# Streamlit app
st.title("Real-Time Student Data Entry and Alert System")

# Section for adding new entries
st.sidebar.header("Add Student Update")
with st.sidebar.form("entry_form"):
    student_name = st.text_input("Student Name")
    phone_number = st.text_input("Phone Number")
    update_date = st.date_input("Update Date", value=datetime.today())
    update_text = st.text_area("Update")
    submit_button = st.form_submit_button("Add Update")

# Add data to session state
if submit_button:
    if student_name and phone_number and update_text:
        new_data = {
            "Student Name": student_name,
            "Phone Number": phone_number,
            "Date": update_date,
            "Update": update_text,
        }
        st.session_state["students_data"] = pd.concat(
            [st.session_state["students_data"], pd.DataFrame([new_data])],
            ignore_index=True,
        )
        st.success(f"Update added for {student_name}")
    else:
        st.error("Please fill in all fields.")

# Display the data
st.markdown("## Student Updates")
if not st.session_state["students_data"].empty:
    # Convert date column to datetime
    st.session_state["students_data"]["Date"] = pd.to_datetime(
        st.session_state["students_data"]["Date"]
    )
    st.dataframe(st.session_state["students_data"], use_container_width=True)
else:
    st.info("No updates added yet.")

# Check for inactive students
alerts = check_inactivity(st.session_state["students_data"])

# Display alerts
st.markdown("## Alerts for Inactivity")
if alerts:
    st.warning("The following students have no updates in over a week:")
    for alert in alerts:
        st.write(
            f"**{alert['Student Name']}** - Last update was {alert['Days Since Last Update']} days ago"
        )
else:
    st.success("All students have recent updates.")

# Footer
st.markdown("<hr><p style='text-align: center;'>© 2025 SPH Team</p>", unsafe_allow_html=True)
