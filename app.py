import streamlit as st
import pandas as pd
import plotly.express as px
import io
from fpdf import FPDF
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Analisis KIAS", layout="wide")

# --- CSS KHAS (TULISAN HITAM UNTUK REPORT) ---
st.markdown("""
<style>
    .report-view-text {
        color: black !important;
        font-family: 'Times New Roman', serif;
        background-color: white;
        padding: 20px;
        border: 1px solid #ddd;
    }
    .report-view-text h1, .report-view-text h2, .report-view-text h3, 
    .report-view-text p, .report-view-text td, .report-view-text th, 
    .report-view-text li, .report-view-text span, .report-view-text div {
        color: black !important;
    }
    /* Paksa table header jadi hitam */
    div[data-testid="stTable"] th {
        color: black !important; 
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZATION (CLEAN SLATE) ---
if 'df' not in st.session_state:
    st.session_state['df'] = None

if 'report_structure' not in st.session_state:
    # Mula dengan Bab 1 yang KOSONG
    st.session_state['report_structure'] = [
        {"title": "Bab 1: Demografi Responden", "items": []}
    ]

# --- FUNGSI LOAD DATA (HEURISTIC) ---
def detect_header_row(df_raw):
    # Imbas 10 baris pertama, cari baris paling banyak data (bukan NaN)
    max_non_na = 0
    header_idx = 0
    for i in range(min(10, len(df_raw))):
        row_count = df_raw.iloc[i].count()
        if row_count > max_non_na:
            max_non_na = row_count
            header_idx = i
    return header_idx

def clean_data(df):
    # Buang kolum tanpa nama (Unnamed)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    # Buang baris yang kosong sepenuhnya
    df.dropna(how='all', inplace=True)
    # Reset index
    df.reset_index(drop=True, inplace=True)
    return df

# --- FUNGSI ANALISIS TEKS (BAHASA MELAYU) ---
def generate_analysis_text(col_name, counts, percents):
    try:
        # Cari Max
        max_idx = counts.idxmax()
        max_val = counts[max_idx]
        max_pct = percents[max_idx]
        
        # Cari Min
        min_idx = counts.idxmin()
        min_val = counts[min_idx]
        min_pct = percents[min_idx]
        
        text = (
            f"Berdasarkan analisis deskriptif bagi pemboleh ubah **{col_name}**, dapatan kajian menunjukkan bahawa "
            f"majoriti responden memilih kategori **{max_idx}** dengan kekerapan seramai **{max_val}** orang ({max_pct:.1f}%). "
            f"Manakala, kategori **{min_idx}** mencatatkan jumlah terendah iaitu seramai **{min_val}** orang ({min_pct:.1f}%)."
        )
        return text
    except:
        return "Data tidak mencukupi untuk menjana analisis automatik."

# --- KELAS PDF GENERATOR ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Laporan Analisis Data KIAS', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, title, 0, 1, 'L', 1)
        self.ln(4)

    def add_table(self, df, title):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 6, title, 0, 1)
        self.set_font('Arial', '', 10)
        
        # Header
        cols = df.columns
        col_width = 190 / len(cols)
        for col in cols:
            self.cell(col_width, 7, str(col), 1)
        self.ln()
        
        # Rows
        for _, row in df.iterrows():
            for col in cols:
                self.cell(col_width, 7, str(row[col]), 1)
            self.ln()
        self.ln(5)

    def add_analysis_text(self, text):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, text.replace('**', '')) # Remove markdown bold for PDF
        self.ln(5)

# --- FUNGSI EXPORT WORD ---
def generate_word_doc(structure, df):
    doc = Document()
    doc.add_heading('Laporan Analisis Data KIAS', 0)
    
    for chapter in structure:
        doc.add_heading(chapter['title'], level=1)
        
        for item in chapter['items']:
            if item['type'] == 'single':
                col = item['var']
                if col in df.columns:
                    # Data Processing
                    counts = df[col].value_counts()
                    percents = df[col].value_counts(normalize=True) * 100
                    
                    # Table A (Counts)
                    df_A = pd.DataFrame({'Kategori': counts.index, 'Bilangan': counts.values})
                    total_count = df_A['Bilangan'].sum()
                    df_A.loc[len(df_A)] = ['JUMLAH BESAR', total_count]
                    
                    # Table B (Percents)
                    df_B = pd.DataFrame({'Kategori': percents.index, 'Peratus (%)': percents.values.round(1)})
                    total_pct = df_B['Peratus (%)'].sum()
                    df_B.loc[len(df_B)] = ['JUMLAH BESAR', round(total_pct, 1)] # Should be near 100
                    
                    text = generate_analysis_text(col, counts, percents)
                    
                    # Write to Word
                    doc.add_heading(f"Analisis: {col}", level=2)
                    
                    # Table A
                    doc.add_paragraph("Jadual (a): Taburan Kekerapan", style='Caption')
                    t1 = doc.add_table(df_A.shape[0]+1, df_A.shape[1])
                    t1.style = 'Table Grid'
                    # Header
                    for j, col_name in enumerate(df_A.columns):
                        t1.cell(0, j).text = col_name
                    # Rows
                    for i, row in enumerate(df_A.itertuples(index=False)):
                        for j, val in enumerate(row):
                            t1.cell(i+1, j).text = str(val)
                    doc.add_paragraph() # Spacing

                    # Table B
                    doc.add_paragraph("Jadual (b): Taburan Peratusan", style='Caption')
                    t2 = doc.add_table(df_B.shape[0]+1, df_B.shape[1])
                    t2.style = 'Table Grid'
                    # Header
                    for j, col_name in enumerate(df_B.columns):
                        t2.cell(0, j).text = col_name
                    # Rows
                    for i, row in enumerate(df_B.itertuples(index=False)):
                        for j, val in enumerate(row):
                            t2.cell(i+1, j).text = str(val)
                    doc.add_paragraph()
                    
                    # Analysis Text
                    p = doc.add_paragraph(text.replace('**', ''))
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    
    return doc

# --- SIDEBAR & NAVIGATION ---
st.sidebar.title("Menu Sistem")
menu = st.sidebar.radio("Pilih Modul:", 
    ["1. Upload / Paste Data", "2. Dashboard Ringkas", "3. Report Generator", "4. Advanced Report Builder"])

# --- MODUL 1: UPLOAD DATA ---
if menu == "1. Upload / Paste Data":
    st.title("📂 Pengurusan Data")
    
    tab1, tab2 = st.tabs(["Upload Fail (Excel/CSV)", "Paste Data (Grid Mode)"])
    
    with tab1:
        uploaded_file = st.file_uploader("Muat Naik Fail", type=['csv', 'xlsx'])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    # Baca header dahulu
                    df_temp = pd.read_csv(uploaded_file, header=None)
                    header_row = detect_header_row(df_temp)
                    # Baca semula dengan header yang betul
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, header=header_row)
                else:
                    df = pd.read_excel(uploaded_file)
                
                df = clean_data(df)
                st.session_state['df'] = df
                st.success(f"✅ Data berjaya dimuat naik! Jumlah Responden: {len(df)}")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Ralat membaca fail: {e}")

    with tab2:
        st.write("### Manual Entry (Grid Style)")
        st.info("💡 Klik pada sel pertama (Var1), kemudian tekan **Ctrl+V** untuk paste data dari Excel.")
        
        # Sediakan Grid Kosong Besar
        if 'grid_df' not in st.session_state:
            cols = [f"Var{i+1}" for i in range(50)]
            st.session_state['grid_df'] = pd.DataFrame(columns=cols, index=range(100)).fillna("")
            
        edited_df = st.data_editor(st.session_state['grid_df'], num_rows="dynamic", use_container_width=True)
        
        if st.button("✅ Proses Data Paste"):
            # Cari baris pertama yang berisi sebagai header
            try:
                # Bersihkan row/col kosong dulu
                clean_edit = edited_df.replace("", pd.NA).dropna(how='all', axis=0).dropna(how='all', axis=1)
                
                # Angkat row pertama jadi header
                new_header = clean_edit.iloc[0]
                df_final = clean_edit[1:]
                df_final.columns = new_header
                df_final.reset_index(drop=True, inplace=True)
                
                st.session_state['df'] = df_final
                st.success(f"✅ Data Paste Berjaya! Jumlah: {len(df_final)}")
                st.rerun()
            except Exception as e:
                st.error(f"Ralat memproses data: {e}")

# --- MODUL 2: DASHBOARD ---
elif menu == "2. Dashboard Ringkas":
    st.title("📊 Dashboard Analisis")
    df = st.session_state['df']
    
    if df is None:
        st.warning("⚠️ Sila upload data dahulu di menu 1.")
    else:
        col_list = df.columns.tolist()
        selected_col = st.selectbox("Pilih Pemboleh Ubah untuk Dianalisis:", col_list)
        
        if selected_col:
            counts = df[selected_col].value_counts()
            fig = px.bar(counts, x=counts.index, y=counts.values, 
                         labels={'x': selected_col, 'y': 'Kekerapan'},
                         title=f"Taburan: {selected_col}",
                         text_auto=True, color_discrete_sequence=['#3366cc'])
            st.plotly_chart(fig, use_container_width=True)
            
            # Cross Analysis Mini
            st.subheader("Analisis Silang (Cross-Tab)")
            c1, c2 = st.columns(2)
            with c1: x_var = st.selectbox("Paksi X", col_list, index=0)
            with c2: y_var = st.selectbox("Paksi Y", col_list, index=min(1, len(col_list)-1))
            
            if x_var and y_var:
                ct = pd.crosstab(df[x_var], df[y_var])
                fig2 = px.imshow(ct, text_auto=True, aspect="auto", color_continuous_scale="Blues")
                st.plotly_chart(fig2, use_container_width=True)

# --- MODUL 3: REPORT GENERATOR (BASIC) ---
elif menu == "3. Report Generator":
    st.title("📑 Report Generator (Auto)")
    df = st.session_state['df']
    
    if df is None:
        st.warning("⚠️ Tiada data.")
    else:
        st.info("Modul ini akan menjana laporan untuk SEMUA pemboleh ubah secara automatik.")
        cols_to_analyze = [c for c in df.columns if c.lower() not in ['timestamp', 'email address', 'id']]
        
        st.markdown('<div class="report-view-text">', unsafe_allow_html=True)
        st.header("LAPORAN ANALISIS PENUH")
        
        for col in cols_to_analyze:
            st.subheader(f"Analisis: {col}")
            
            counts = df[col].value_counts()
            percents = df[col].value_counts(normalize=True) * 100
            
            # Table A
            df_A = pd.DataFrame({'Kategori': counts.index, 'Bilangan': counts.values})
            df_A.loc[len(df_A)] = ['JUMLAH BESAR', df_A['Bilangan'].sum()]
            
            # Table B
            df_B = pd.DataFrame({'Kategori': percents.index, 'Peratus (%)': percents.values.round(1)})
            df_B.loc[len(df_B)] = ['JUMLAH BESAR', df_B['Peratus (%)'].sum().round(1)]

            c1, c2 = st.columns(2)
            with c1: 
                st.write("**Jadual (a): Kekerapan**")
                st.table(df_A)
            with c2: 
                st.write("**Jadual (b): Peratusan**")
                st.table(df_B)
            
            text = generate_analysis_text(col, counts, percents)
            st.markdown(f"<p style='text-align: justify;'>{text}</p>", unsafe_allow_html=True)
            st.markdown("---")
            
        st.markdown('</div>', unsafe_allow_html=True)

# --- MODUL 4: ADVANCED REPORT BUILDER ---
elif menu == "4. Advanced Report Builder":
    st.title("📝 Advanced Report Builder")
    df = st.session_state['df']
    
    if df is None:
        st.warning("⚠️ Sila upload data dahulu.")
    else:
        # --- SIDEBAR CONFIG ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔧 Konfigurasi Laporan")
        
        if st.sidebar.button("➕ Tambah Bab Baru"):
            new_chap_num = len(st.session_state['report_structure']) + 1
            st.session_state['report_structure'].append(
                {"title": f"Bab {new_chap_num}: (Klik untuk Edit Tajuk)", "items": []}
            )
            st.rerun()

        if st.sidebar.button("🗑️ Reset Laporan (Kosongkan)"):
             st.session_state['report_structure'] = [{"title": "Bab 1: Pendahuluan", "items": []}]
             st.rerun()

        # --- MAIN BUILDER UI ---
        for i, chapter in enumerate(st.session_state['report_structure']):
            with st.expander(f"{chapter['title']}", expanded=True):
                # Edit Title
                new_title = st.text_input(f"Tajuk Bab {i+1}", value=chapter['title'], key=f"title_{i}")
                st.session_state['report_structure'][i]['title'] = new_title
                
                # Show Items
                if chapter['items']:
                    st.write("##### Senarai Analisis dalam Bab ini:")
                    for j, item in enumerate(chapter['items']):
                        if item['type'] == 'single':
                            st.text(f"{j+1}. Single Variable: {item['var']}")
                        else:
                            st.text(f"{j+1}. Cross Analysis: {item['var_x']} VS {item['var_y']}")
                else:
                    st.info("Belum ada item. Sila tambah di bawah.")

                st.markdown("---")
                # Add Item Form
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    type_choice = st.selectbox("Jenis Analisis", ["Single Variable", "Cross Analysis"], key=f"type_{i}")
                with c2:
                    col_opts = df.columns.tolist()
                    if type_choice == "Single Variable":
                        var_sel = st.selectbox("Pilih Variable", col_opts, key=f"v1_{i}")
                    else:
                        var_x = st.selectbox("Paksi X", col_opts, key=f"vx_{i}")
                        var_y = st.selectbox("Paksi Y", col_opts, key=f"vy_{i}")
                with c3:
                    st.write("") # Spacer
                    st.write("")
                    if st.button("➕ Tambah Item", key=f"add_{i}"):
                        if type_choice == "Single Variable":
                            chapter['items'].append({"type": "single", "var": var_sel})
                        else:
                            chapter['items'].append({"type": "cross", "var_x": var_x, "var_y": var_y})
                        st.rerun()

        # --- PREVIEW & EXPORT ---
        st.markdown("## Pratsonton & Muat Turun")
        
        if st.button("🔄 Generate Full Report Preview"):
            st.markdown('<div class="report-view-text">', unsafe_allow_html=True)
            st.header("DRAF LAPORAN AKHIR")
            
            for chapter in st.session_state['report_structure']:
                st.markdown(f"## {chapter['title']}")
                
                for item in chapter['items']:
                    if item['type'] == 'single':
                        col = item['var']
                        if col in df.columns:
                            st.markdown(f"### Analisis: {col}")
                            counts = df[col].value_counts()
                            percents = df[col].value_counts(normalize=True) * 100
                            
                            df_A = pd.DataFrame({'Kategori': counts.index, 'Bilangan': counts.values})
                            df_A.loc[len(df_A)] = ['JUMLAH BESAR', df_A['Bilangan'].sum()]
                            
                            df_B = pd.DataFrame({'Kategori': percents.index, 'Peratus (%)': percents.values.round(1)})
                            df_B.loc[len(df_B)] = ['JUMLAH BESAR', df_B['Peratus (%)'].sum().round(1)]
                            
                            c1, c2 = st.columns(2)
                            with c1: st.table(df_A)
                            with c2: st.table(df_B)
                            
                            text = generate_analysis_text(col, counts, percents)
                            st.markdown(f"*{text}*")
                            
                    elif item['type'] == 'cross':
                        # Logic ringkas untuk Cross Analysis preview
                        st.markdown(f"### Analisis Silang: {item['var_x']} vs {item['var_y']}")
                        ct = pd.crosstab(df[item['var_x']], df[item['var_y']])
                        st.table(ct)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Export Buttons
            # Word
            doc = generate_word_doc(st.session_state['report_structure'], df)
            bio = io.BytesIO()
            doc.save(bio)
            
            st.download_button(
                label="📝 Muat Turun Laporan (Word .docx)",
                data=bio.getvalue(),
                file_name="Laporan_Analisis_KIAS.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
