import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import qrcode
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DataSuite Pro", layout="wide", page_icon="📊")

# --- 2. DATA HANDLER (GOOGLE SHEETS) ---
def load_data():
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Fix PEM private key format
            raw_key = st.secrets["connections"]["gsheets"]["private_key"]
            if "\\n" in raw_key:
                st.secrets["connections"]["gsheets"]["private_key"] = raw_key.replace("\\n", "\n")
            df = conn.read()
            return df.dropna(how='all')
        return pd.DataFrame(columns=["Timestamp"])
    except:
        return pd.DataFrame(columns=["Timestamp"])

def save_data(new_data):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_existing = conn.read().dropna(how='all')
        new_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_updated = pd.concat([df_existing, pd.DataFrame([new_data])], ignore_index=True)
        conn.update(data=df_updated)
        st.toast("Data berjaya disimpan!", icon="☁️")
    except Exception as e:
        st.error(f"Error: {e}")

# --- 3. UI MODULES ---
def module_form_builder():
    st.title("🛠️ Form Builder")
    with st.expander("🚀 Share & Collect Data (QR & Link)", expanded=True):
        st.info("Salin link app anda dari browser dan letak di bawah untuk jana QR Code.")
        url = st.text_input("App URL", "https://datasuite-pro-zu2afssf...streamlit.app")
        final_url = f"{url}?view=respondent"
        st.code(final_url)
        if st.button("Generate QR"):
            qr_img = qrcode.make(final_url)
            buf = io.BytesIO()
            qr_img.save(buf)
            st.image(buf, width=200, caption="Scan untuk jawab")

def module_dashboard():
    st.title("📊 Interactive Dashboard")
    df = load_data()
    if not df.empty and len(df.columns) > 1:
        col1, col2 = st.columns(2)
        cat_col = st.selectbox("Pilih Analisis Data", df.columns[1:])
        with col1:
            st.plotly_chart(px.bar(df, x=cat_col, title=f"Jumlah: {cat_col}", color=cat_col), use_container_width=True)
        with col2:
            st.plotly_chart(px.pie(df, names=cat_col, title=f"Peratus: {cat_col}"), use_container_width=True)
    else:
        st.warning("Belum ada data untuk dipaparkan di Dashboard.")

def module_data_manager():
    st.title("📂 Data Manager")
    df = load_data()
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download CSV", df.to_csv(index=False), "data.csv", "text/csv")
        with col2:
            st.download_button("📥 Download Excel", df.to_excel(index=False) if hasattr(df, 'to_excel') else "", "data.xlsx")

# --- 4. MAIN NAVIGATION ---
if "view" in st.query_params and st.query_params["view"] == "respondent":
    st.title("📋 Soal Selidik")
    with st.form("main_form"):
        name = st.text_input("Nama Penuh")
        gender = st.radio("Jantina", ["Lelaki", "Perempuan"])
        if st.form_submit_button("Hantar"):
            save_data({"Nama Penuh": name, "Jantina": gender})
else:
    st.sidebar.title("DataSuite Pro")
    menu = st.sidebar.radio("Menu Utama", ["Form Builder", "Data Manager", "Dashboard"])
    
    if menu == "Form Builder": module_form_builder()
    elif menu == "Data Manager": module_data_manager()
    elif menu == "Dashboard": module_dashboard()
