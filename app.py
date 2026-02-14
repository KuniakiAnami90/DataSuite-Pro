import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import qrcode
from streamlit_gsheets import GSheetsConnection
import scipy.stats as stats

# --- 1. INITIAL CONFIGURATION ---
st.set_page_config(page_title="DataSuite Pro", layout="wide", page_icon="📊")

# Simulasi INITIAL_SCHEMA daripada TypeScript
INITIAL_QUESTIONS = [
    {"id": "q1", "text": "Age", "type": "number"},
    {"id": "q2", "text": "Gender", "type": "select", "options": ["Male", "Female", "Other"]},
    {"id": "q3", "text": "Satisfaction Score", "type": "rating"},
    {"id": "q4", "text": "Likelihood to Recommend", "type": "rating"}
]

# --- 2. DATA & CLOUD CONNECTION (GOOGLE SHEETS) ---
def load_data_from_cloud():
    """Mengambil data dari Google Sheets (v1.2.0 Connected)"""
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Baiki format private key jika ada isu \n
            raw_key = st.secrets["connections"]["gsheets"]["private_key"]
            if "\\n" in raw_key:
                st.secrets["connections"]["gsheets"]["private_key"] = raw_key.replace("\\n", "\n")
            
            df = conn.read()
            return df.dropna(how='all'), True
        return pd.DataFrame(columns=["Timestamp"]), False
    except Exception as e:
        return pd.DataFrame(columns=["Timestamp"]), False

def handle_form_submit(new_row):
    """Menyimpan data baru ke awan (Optimistic UI Update)"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existing = conn.read().dropna(how='all')
        
        # Tambah timestamp (Metadata)
        new_row["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_updated = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)
        
        conn.update(data=df_updated)
        st.toast("Data synced to Google Sheets!", icon="☁️")
        return True
    except Exception as e:
        st.error(f"Sync failed: {e}")
        return False

# --- 3. UI MODULES (REPLICATING REACT COMPONENTS) ---

def module_dashboard(df):
    st.title("📈 Dashboard")
    if not df.empty and len(df.columns) > 1:
        col1, col2 = st.columns(2)
        target = st.selectbox("Select Metric", df.columns[1:])
        with col1:
            fig1 = px.histogram(df, x=target, title=f"Distribution of {target}", color_discrete_sequence=['#636EFA'])
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.pie(df, names=target, title=f"Percentage of {target}")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data available for visualization.")

def module_form_builder():
    st.title("🛠️ Form Builder")
    st.write("Configure your survey schema here.")
    with st.expander("🚀 Share Survey (QR Code)"):
        url = st.text_input("App URL", "https://your-app.streamlit.app")
        final_link = f"{url}?view=respondent"
        st.code(final_link)
        if st.button("Generate QR"):
            img = qrcode.make(final_link)
            buf = io.BytesIO()
            img.save(buf)
            st.image(buf, width=200)

def module_data_manager(df):
    st.title("📂 Data Manager")
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("📥 Export CSV", df.to_csv(index=False), "survey_results.csv", "text/csv")

def module_stats(df):
    st.title("🔬 Statistical Analysis")
    if not df.empty:
        st.subheader("Descriptive Statistics")
        st.write(df.describe())
    else:
        st.info("Insufficient data for analysis.")

# --- 4. RESPONDENT VIEW LOGIC ---
def respondent_view():
    st.title("📋 Customer Satisfaction Survey")
    st.write("Please help us improve our services by answering the following questions.")
    
    with st.form("survey_form"):
        responses = {}
        for q in INITIAL_QUESTIONS:
            if q["type"] == "number":
                responses[q["text"]] = st.number_input(q["text"], min_value=0)
            elif q["type"] == "select":
                responses[q["text"]] = st.selectbox(q["text"], q["options"])
            elif q["type"] == "rating":
                responses[q["text"]] = st.slider(q["text"], 1, 5, 3)
        
        if st.form_submit_button("Submit Response"):
            if handle_form_submit(responses):
                st.success("Thank you! Your response has been recorded.")
                st.balloons()

# --- 5. MAIN APP NAVIGATION ---

# Detect Respondent Mode from URL
query_params = st.query_params
if query_params.get("view") == "respondent":
    respondent_view()
else:
    # Sidebar (Admin Mode)
    st.sidebar.title("DataSuite Pro")
    df, is_online = load_data_from_cloud()
    
    # Status Indicators
    if not is_online:
        st.sidebar.error("⚠️ Offline Mode")
    else:
        st.sidebar.success("☁️ Google Sheets Connected")
    
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Form Builder", "Data Manager", "Statistical Analysis"])
    st.sidebar.caption("v1.2.0 (Stable)")

    if menu == "Dashboard":
        module_dashboard(df)
    elif menu == "Form Builder":
        module_form_builder()
    elif menu == "Data Manager":
        module_data_manager(df)
    elif menu == "Statistical Analysis":
        module_stats(df)
