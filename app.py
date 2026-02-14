import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import qrcode
from PIL import Image
from fpdf import FPDF
import scipy.stats as stats
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION & CSS ---
st.set_page_config(page_title="DataSuite Pro", layout="wide", page_icon="📊")

# Custom CSS for Mobile & Dark Mode
st.markdown("""
<style>
    /* Responsive Padding */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    /* Hide Streamlit Footer */
    footer {visibility: hidden;}
    /* Button Styling */
    div.stButton > button { width: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE INIT ---
if 'form_schema' not in st.session_state:
    # Default Starting Schema
    st.session_state['form_schema'] = [
        {"id": "q1", "type": "Text", "question": "Nama Penuh", "options": "", "logic": {}},
        {"id": "q2", "type": "Multiple Choice", "question": "Jantina", "options": "Lelaki,Perempuan", "logic": {}}
    ]

# --- 3. HELPER FUNCTIONS (DATA HANDLER) ---

def load_data():
    """Loads data. Tries Google Sheets first if secrets exist, else Local CSV."""
    try:
        # Check if Google Sheets secrets exist
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read()
            return df
        else:
            # Fallback to Local CSV
            try:
                return pd.read_csv("survey_data.csv")
            except FileNotFoundError:
                return pd.DataFrame(columns=["Timestamp"])
    except Exception as e:
        return pd.DataFrame(columns=["Timestamp"])

def save_data(new_data):
    """Saves data. Appends new row to Google Sheets or Local CSV."""
    df = load_data()
    
    # Add Timestamp
    new_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Convert single dict to DataFrame
    new_row = pd.DataFrame([new_data])
    
    # Combine (Sync Schema)
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Ensure Timestamp is FIRST column
    cols = ['Timestamp'] + [c for c in df.columns if c != 'Timestamp']
    df = df[cols]
    
    try:
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            conn = st.connection("gsheets", type=GSheetsConnection)
            conn.update(data=df)
            st.toast("Data saved to Google Sheets!", icon="☁️")
        else:
            df.to_csv("survey_data.csv", index=False)
            st.toast("Data saved locally (CSV)!", icon="💾")
    except Exception as e:
        st.error(f"Error saving data: {e}")

# --- 4. MODULES ---

def generate_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def respondent_view():
    st.title("📋 Soal Selidik / Survey")
    
    responses = {}
    schema = st.session_state['form_schema']
    
    # Render Questions with Logic
    skip_to = None
    
    with st.form("survey_form"):
        for i, item in enumerate(schema):
            # Skip logic
            if skip_to and item['id'] != skip_to:
                continue
            if skip_to and item['id'] == skip_to:
                skip_to = None # Reset skip
            
            st.markdown(f"**{i+1}. {item['question']}**")
            
            val = None
            if item['type'] == "Text":
                val = st.text_input(f"Answer for Q{i+1}", key=f"ans_{item['id']}", label_visibility="collapsed")
            elif item['type'] == "Multiple Choice":
                opts = [x.strip() for x in item['options'].split(',')]
                val = st.radio(f"Select for Q{i+1}", opts, key=f"ans_{item['id']}", label_visibility="collapsed", index=None)
            elif item['type'] == "Likert Scale (1-5)":
                val = st.slider(f"Scale for Q{i+1}", 1, 5, 3, key=f"ans_{item['id']}", label_visibility="collapsed")
            
            responses[item['question']] = val
            
            # Check Logic Immediate (Simulated)
            if item.get('logic') and val in item['logic']:
                action = item['logic'][val]
                if action == "Terminate":
                    st.warning("Terima kasih. Soal selidik tamat.")
                    st.form_submit_button("Hantar")
                    return
                elif action.startswith("Skip to"):
                    skip_to = action.split(": ")[1]

        submitted = st.form_submit_button("Hantar Jawapan / Submit", use_container_width=True)
        if submitted:
            save_data(responses)
            st.success("Terima kasih! Jawapan anda telah direkodkan.")
            st.balloons()

def module_form_builder():
    st.header("🛠️ Form Builder")
    
    # 1. Share & Collect Section
    with st.expander("🚀 Share & Collect Data (QR Code & Link)", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            base_url = st.text_input("App URL (Copy from browser)", value="http://localhost:8501")
            # Clean URL
            if not base_url.startswith("http"): base_url = "https://" + base_url
            final_link = f"{base_url.rstrip('/')}/?view=respondent"
            st.code(final_link, language="text")
            st.caption("Copy link ini untuk diberi kepada responden.")
        with col2:
            if base_url:
                img = generate_qr(final_link)
                # Convert to bytes for display
                buf = io.BytesIO()
                img.save(buf)
                st.image(buf, caption="Scan to Answer", width=150)

    st.divider()

    # 2. Question Editor
    st.subheader("Edit Soalan")
    
    new_schema = []
    for idx, item in enumerate(st.session_state['form_schema']):
        with st.container(border=True):
            c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
            c1.markdown(f"**#{idx+1}**")
            item['question'] = c2.text_input("Soalan", item['question'], key=f"q_txt_{idx}")
            item['type'] = c3.selectbox("Jenis", ["Text", "Multiple Choice", "Likert Scale (1-5)"], index=["Text", "Multiple Choice", "Likert Scale (1-5)"].index(item['type']), key=f"q_type_{idx}")
            
            if item['type'] == "Multiple Choice":
                item['options'] = st.text_input("Pilihan (Asingkan dengan koma)", item['options'], key=f"q_opt_{idx}")
            
            # Advanced Logic
            with st.expander("⚙️ Advanced Logic & Settings"):
                st.caption("Tetapkan logik jika responden pilih jawapan tertentu.")
                if item['type'] == "Multiple Choice":
                    opts = [x.strip() for x in item['options'].split(',') if x.strip()]
                    logic_dict = item.get('logic', {})
                    for opt in opts:
                        # Logic choices
                        targets = ["Next Question", "Terminate"] + [f"Skip to: {q['id']}" for q in st.session_state['form_schema']]
                        current_logic = logic_dict.get(opt, "Next Question")
                        chosen = st.selectbox(f"Jika jawab '{opt}', pergi ke:", targets, key=f"log_{item['id']}_{opt}")
                        if chosen != "Next Question":
                            logic_dict[opt] = chosen
                    item['logic'] = logic_dict

            # Action Buttons
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("⬆️ Naik", key=f"up_{idx}") and idx > 0:
                st.session_state['form_schema'][idx], st.session_state['form_schema'][idx-1] = st.session_state['form_schema'][idx-1], st.session_state['form_schema'][idx]
                st.rerun()
            if b2.button("⬇️ Turun", key=f"down_{idx}") and idx < len(st.session_state['form_schema'])-1:
                st.session_state['form_schema'][idx], st.session_state['form_schema'][idx+1] = st.session_state['form_schema'][idx+1], st.session_state['form_schema'][idx]
                st.rerun()
            if b3.button("📄 Duplicate", key=f"dup_{idx}"):
                new_q = item.copy()
                new_q['id'] = f"q_{datetime.now().timestamp()}" # New ID
                st.session_state['form_schema'].insert(idx+1, new_q)
                st.rerun()
            if b4.button("🗑️ Padam", key=f"del_{idx}"):
                st.session_state['form_schema'].pop(idx)
                st.rerun()
                
    if st.button("➕ Tambah Soalan Baru", use_container_width=True):
        st.session_state['form_schema'].append({"id": f"q_{datetime.now().timestamp()}", "type": "Text", "question": "Soalan Baru", "options": "", "logic": {}})
        st.rerun()

def module_dashboard():
    st.header("📊 Interactive Dashboard (Power BI Style)")
    df = load_data()
    
    if df.empty:
        st.info("Belum ada data. Sila jawab survey dahulu.")
        return

    # KPI Cards
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Respondan", len(df))
    k1.metric("Hari Ini", len(df[pd.to_datetime(df['Timestamp']).dt.date == datetime.now().date()]))
    
    # Filter
    st.subheader("Analisis Visual")
    cat_cols = [c for c in df.columns if c != "Timestamp"]
    selected_col = st.selectbox("Pilih Variabel untuk Analisis", cat_cols)
    
    # Chart
    c1, c2 = st.columns(2)
    with c1:
        # Bar Chart
        fig_bar = px.bar(df, x=selected_col, title=f"Taburan: {selected_col}", color=selected_col)
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)
    with c2:
        # Pie Chart
        fig_pie = px.pie(df, names=selected_col, title=f"Peratusan: {selected_col}")
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

def module_stats():
    st.header("📈 Statistical Analysis (SPSS Style)")
    df = load_data()
    if df.empty: return

    tab1, tab2 = st.tabs(["Descriptive", "Inferential"])
    
    with tab1:
        st.subheader("Descriptive Statistics")
        desc = df.describe(include='all').transpose()
        st.dataframe(desc, use_container_width=True)
        
        # Normality Test (Shapiro) for numeric
        st.subheader("Normality Test (Shapiro-Wilk)")
        num_cols = df.select_dtypes(include=['float64', 'int64']).columns
        if len(num_cols) > 0:
            for col in num_cols:
                stat, p = stats.shapiro(df[col].dropna())
                st.write(f"**{col}**: W={stat:.3f}, p={p:.3f} ({'Normal' if p>0.05 else 'Not Normal'})")

    with tab2:
        st.subheader("Correlation Matrix")
        if len(num_cols) > 1:
            corr = df[num_cols].corr()
            fig_corr = px.imshow(corr, text_auto=True, title="Correlation Heatmap")
            st.plotly_chart(fig_corr)
        else:
            st.info("Perlukan sekurang-kurangnya 2 lajur nombor untuk korelasi.")

def module_data_manager():
    st.header("🗂️ Data Manager")
    df = load_data()
    
    st.dataframe(df, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        # Download CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="data_survey.csv", mime="text/csv")
    
    with col2:
        # Download Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        st.download_button("📥 Download Excel", data=output.getvalue(), file_name="data_survey.xlsx", mime="application/vnd.ms-excel")

# --- 5. MAIN NAV ---

# Check URL Query Params (Respondent View)
if "view" in st.query_params and st.query_params["view"] == "respondent":
    respondent_view()
else:
    # Admin View
    st.sidebar.title("DataSuite Pro")
    menu = st.sidebar.radio("Menu", ["Form Builder", "Data Manager", "Dashboard", "Statistical Analysis"])
    
    if menu == "Form Builder":
        module_form_builder()
    elif menu == "Data Manager":
        module_data_manager()
    elif menu == "Dashboard":
        module_dashboard()
    elif menu == "Statistical Analysis":
        module_stats()