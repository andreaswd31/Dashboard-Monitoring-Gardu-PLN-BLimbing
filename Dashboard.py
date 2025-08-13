import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import plotly.express as px

# =================================================================================
# KONFIGURASI APLIKASI
# =================================================================================
SHEET_BEST_API_URL = "https://api.sheetbest.com/sheets/2d219b6c-99c3-4999-b433-c14aafa05d6b" 
HISTORY_SHEET_API_URL = "https://api.sheetbest.com/sheets/7e52bc4f-495e-4433-82fc-956e8d04f85d" 
WIB = pytz.timezone('Asia/Jakarta')

# Konfigurasi Halaman
st.set_page_config(
    page_title="Dashboard Gardu",
    page_icon="Logo_PLN.png",
    layout="centered"
)

# =================================================================================
# FUNGSI-FUNGSI
# =================================================================================

def local_css(file_name):
    """Membaca file CSS lokal."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"File CSS '{file_name}' tidak ditemukan.")

local_css("mobile.css")

@st.cache_data(ttl=300)
def load_data(url):
    """Mengambil data dari URL API."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

def process_main_data(df):
    """Membersihkan dataframe utama."""
    if df.empty: return df
    df.columns = df.columns.str.strip()
    numeric_cols = [
        'KAPASITAS', 'BEBAN (VA)', 'BEBAN %', 'R Utama', 'S Utama', 'T Utama', 'N Utama',
        'R Line A', 'S Line A', 'T Line A', 'N Line A', 'R Line B', 'S Line B', 'T Line B', 'N Line B',
        'R Line C', 'S Line C', 'T Line C', 'N Line C', 'R Line D', 'S Line D', 'T Line D', 'N Line D',
        'V R-N', 'V S-N', 'V T-N'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def log_update(log_entries):
    """Mengirim log ke sheet History."""
    if not log_entries: return
    try:
        requests.post(HISTORY_SHEET_API_URL, json=log_entries)
    except Exception:
        pass

def update_data_api(nama_gardu, old_data_dict, data_to_update):
    """Mengupdate data dan mencatat perubahan."""
    try:
        url = f"{SHEET_BEST_API_URL}/NAMA GARDU/{nama_gardu}"
        response = requests.patch(url, json=data_to_update)
        response.raise_for_status()
        log_entries, timestamp = [], datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')
        fields_to_ignore_in_log = ['TANGGAL UKUR', 'JAM UKUR']
        numeric_fields = ['KAPASITAS', 'BEBAN (VA)', 'BEBAN %', 'R Utama', 'S Utama', 'T Utama', 'N Utama', 'R Line A', 'S Line A', 'T Line A', 'N Line A', 'R Line B', 'S Line B', 'T Line B', 'N Line B', 'R Line C', 'S Line C', 'T Line C', 'N Line C', 'R Line D', 'S Line D', 'T Line D', 'N Line D', 'V R-N', 'V S-N', 'V T-N']
        for key, new_value in data_to_update.items():
            if key in fields_to_ignore_in_log: continue
            old_value = old_data_dict.get(key, None)
            is_changed = False
            if key in numeric_fields:
                try:
                    if float(old_value) != float(new_value): is_changed = True
                except (ValueError, TypeError):
                    if str(old_value) != str(new_value): is_changed = True
            else:
                if str(old_value) != str(new_value): is_changed = True
            if is_changed:
                log_entries.append({"Timestamp": timestamp, "Nama Gardu": nama_gardu, "Data yang Diubah": key, "Nilai Lama": str(old_value), "Nilai Baru": str(new_value)})
        if log_entries: log_update(log_entries)
        return True
    except Exception as e:
        st.error(f"Gagal memperbarui data: {e}")
        return False

def add_data_api(data_to_add):
    """Mengirim data baru ke API."""
    try:
        response = requests.post(SHEET_BEST_API_URL, json=data_to_add)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Gagal menambahkan data: {e}")
        st.error(f"Response dari server: {response.text}")
        return False

def create_side_by_side_display(data, title1, keys1, title2, keys2):
    """Membuat 2 kolom berdampingan di mobile."""
    html1 = f"<b>{title1}</b><br>" + "".join([f"{key.split(' ')[0]}: {data.get(key, 0):g}<br>" for key in keys1])
    html2 = f"<b>{title2}</b><br>" + "".join([f"{key.split(' ')[0].replace('-', ' - ')}: {data.get(key, 0):g}<br>" for key in keys2])
    final_html = f"""<div style="display: flex; justify-content: space-between; gap: 1.5rem;"><div>{html1}</div><div>{html2}</div></div>"""
    st.markdown(final_html, unsafe_allow_html=True)

# =================================================================================
# DEFINISI HALAMAN-HALAMAN APLIKASI
# =================================================================================

# ## PERUBAHAN: Halaman baru untuk ringkasan statistik
# =================================================================================
# HALAMAN BARU: HOME (RINGKASAN)
# =================================================================================
def page_home():
    """Halaman Utama yang menampilkan statistik dan ringkasan."""
    st.title("Selamat datang di Dashboard Data Gardu PLN Blimbing")
    df = process_main_data(load_data(SHEET_BEST_API_URL))

    if df.empty:
        st.info("Sedang memuat data atau tidak ada data yang ditemukan...")
        return

    total_gardu = len(df)
    status_counts = df['STATUS'].value_counts()
    gardu_overload = status_counts.get('OVERLOAD', 0)
    gardu_critical = status_counts.get('CRITICAL LOAD', 0)
    avg_beban_persen = df['BEBAN %'].mean()
    gardu_beban_tertinggi = df.loc[df['BEBAN %'].idxmax()]
    
    # ## PERBAIKAN: Kode HTML KPI dimasukkan kembali ke sini
    html_kpi = f"""
    <div class="kpi-container">
        <div class="kpi-row">
            <div class="kpi-item">
                <div class="kpi-label">Jumlah Gardu Total</div>
                <div class="kpi-value">{total_gardu:g}</div>
            </div>
            <div class="kpi-item">
                <div class="kpi-label">Gardu Overload (&gt;100%)</div>
                <div class="kpi-value">{gardu_overload}</div>
            </div>
        </div>
        <div class="kpi-row kpi-row-center">
            <div class="kpi-item">
                <div class="kpi-label">Gardu Critical (80-100%)</div>
                <div class="kpi-value">{gardu_critical}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html_kpi, unsafe_allow_html=True)
    st.write("") # Memberi sedikit spasi ke bawah

    col_grafik1, col_grafik2 = st.columns(2)
    with col_grafik1:
        st.subheader("Jumlah Gardu per Status")
        status_df = status_counts.reset_index()
        status_df.columns = ['STATUS', 'Jumlah']
        color_map_status = {'CRITICAL LOAD': '#FF4B4B', 'OVERLOAD': '#FFC300', 'NORMAL': '#1f77b4', 'UNDERLOAD': '#2ca02c', 'LIGHTLY LOAD': '#2ca02c'}
        fig_status = px.bar(status_df, x='STATUS', y='Jumlah', color='STATUS', color_discrete_map=color_map_status, text_auto=True)
        fig_status.update_layout(showlegend=False, yaxis_title="Jumlah")
        fig_status.update_traces(textposition='outside')
        st.plotly_chart(fig_status, use_container_width=True)

    with col_grafik2:
        st.subheader("Distribusi Beban Gardu")
        bins = [0, 40, 80, 100, 120, df['BEBAN %'].max() + 1]
        labels = ['0-40%', '41-80%', '81-100%', '101-120%', '>120%']
        df['Beban Group'] = pd.cut(df['BEBAN %'], bins=bins, labels=labels, right=False)
        beban_group_counts = df['Beban Group'].value_counts().sort_index()
        beban_df = beban_group_counts.reset_index()
        beban_df.columns = ['Grup Beban', 'Jumlah']
        color_map_beban = {'0-40%': '#2ca02c', '41-80%': '#1f77b4', '81-100%': '#ff7f0e', '101-120%': '#FF4B4B', '>120%': '#d62728'}
        fig_beban = px.bar(beban_df, x='Grup Beban', y='Jumlah', color='Grup Beban', color_discrete_map=color_map_beban, text_auto=True)
        fig_beban.update_layout(showlegend=False, yaxis_title="Jumlah")
        fig_beban.update_traces(textposition='outside')
        st.plotly_chart(fig_beban, use_container_width=True)

    st.info(f"📈 **Rata-rata Beban Jaringan**: {avg_beban_persen:.2f}% | ⚠️ **Beban Tertinggi**: {gardu_beban_tertinggi['BEBAN %']:.2f}% di Gardu **{gardu_beban_tertinggi['NAMA GARDU']}**")
    
# ## PERUBAHAN: Halaman monitoring sekarang hanya untuk detail dan edit
def page_monitoring_update():
    """Halaman untuk memilih, melihat detail, dan mengupdate data gardu."""
    st.title("⚙️ Monitoring & Update Gardu")
    df = process_main_data(load_data(SHEET_BEST_API_URL))

    if df.empty:
        st.info("Sedang memuat data atau tidak ada data yang ditemukan...")
        return

    df["PILIHAN"] = df['PENYULANG'] + " - " + df['NAMA GARDU']
    st.header("Pilih Gardu untuk Dilihat/Diedit")
    selected_gardu_pilihan = st.selectbox("Daftar Gardu:", options=df['PILIHAN'].unique(), index=None, placeholder="Ketik untuk mencari penyulang atau nama gardu...", key="selectbox_gardu_monitor")
    st.empty()
    st.empty()
    
    if selected_gardu_pilihan:
        selected_gardu_data = df[df['PILIHAN'] == selected_gardu_pilihan].iloc[0]
        st.divider()
        st.header(f"Detail Informasi: {selected_gardu_pilihan}")
        beban_persen_value = selected_gardu_data['BEBAN %']
        beban_persen_display = f"{float(beban_persen_value):.2f} %" if pd.notna(beban_persen_value) else "Data tidak tersedia"
        info_display = { "Penyulang": selected_gardu_data['PENYULANG'], "Nama Gardu": selected_gardu_data['NAMA GARDU'], "Kapasitas (kVA)": f"{selected_gardu_data['KAPASITAS']:g}", "Beban (VA)": f"{selected_gardu_data['BEBAN (VA)']:g}", "Beban (%)": beban_persen_display, "Status Beban": selected_gardu_data['STATUS'], "Tanggal Ukur Terakhir": selected_gardu_data['TANGGAL UKUR'], "Jam Ukur Terakhir": selected_gardu_data['JAM UKUR'], "Alamat": selected_gardu_data['ALAMAT'], "Konstruksi": selected_gardu_data['KONSTRUKSI'], }
        for label, value in info_display.items(): st.markdown(f"**{label}:** `{value}`")
        with st.expander("Lihat Detail Teknis Arus (Ampere) & Tegangan (Volt)"):
            tab_utama, tab_ac, tab_bd = st.tabs(["Utama & Tegangan", "Line A-C", "Line B-D"])
            with tab_utama: create_side_by_side_display(selected_gardu_data, "Arus Utama", ['R Utama', 'S Utama', 'T Utama', 'N Utama'], "Tegangan (V)", ['V R-N', 'V S-N', 'V T-N'])
            with tab_ac: create_side_by_side_display(selected_gardu_data, "Arus Line A", ['R Line A', 'S Line A', 'T Line A', 'N Line A'], "Arus Line C", ['R Line C', 'S Line C', 'T Line C', 'N Line C'])
            with tab_bd: create_side_by_side_display(selected_gardu_data, "Arus Line B", ['R Line B', 'S Line B', 'T Line B', 'N Line B'], "Arus Line D", ['R Line D', 'S Line D', 'T Line D', 'N Line D'])
        st.divider()
        with st.expander("✏️ Edit Data Gardu Ini", expanded=False):
            with st.form(key='edit_form'):
                st.subheader("Formulir Update Data")
                beban_va_baru = st.number_input("Update Beban (VA)", value=float(selected_gardu_data['BEBAN (VA)']), step=100.0)
                status_baru = st.selectbox("Update Status Beban", options=["NORMAL", "CRITICAL LOAD", "OVERLOAD", "LIGHTLY LOAD"], index=["NORMAL", "CRITICAL LOAD", "OVERLOAD", "LIGHTLY LOAD"].index(selected_gardu_data['STATUS']))
                def create_line_input(line_prefix, data):
                    st.write(f"**Update Arus {line_prefix} (Ampere)**"); cols = st.columns(4)
                    r = cols[0].number_input(f"R {line_prefix}", value=int(data[f'R {line_prefix}']), key=f'r_{line_prefix}')
                    s = cols[1].number_input(f"S {line_prefix}", value=int(data[f'S {line_prefix}']), key=f's_{line_prefix}')
                    t = cols[2].number_input(f"T {line_prefix}", value=int(data[f'T {line_prefix}']), key=f't_{line_prefix}')
                    n = cols[3].number_input(f"N {line_prefix}", value=int(data[f'N {line_prefix}']), key=f'n_{line_prefix}')
                    return r, s, t, n
                r_utama, s_utama, t_utama, n_utama = create_line_input("Utama", selected_gardu_data)
                r_a, s_a, t_a, n_a = create_line_input("Line A", selected_gardu_data)
                r_b, s_b, t_b, n_b = create_line_input("Line B", selected_gardu_data)
                r_c, s_c, t_c, n_c = create_line_input("Line C", selected_gardu_data)
                r_d, s_d, t_d, n_d = create_line_input("Line D", selected_gardu_data)
                if st.form_submit_button("Simpan Perubahan"):
                    waktu_sekarang = datetime.now(WIB)
                    kapasitas_va = float(selected_gardu_data['KAPASITAS']) * 1000
                    beban_persen_baru = (beban_va_baru / kapasitas_va) * 100 if kapasitas_va > 0 else 0
                    data_to_update = { 'BEBAN (VA)': str(beban_va_baru), 'BEBAN %': f"{beban_persen_baru:.1f}", 'STATUS': status_baru, 'TANGGAL UKUR': waktu_sekarang.strftime('%m/%d/%Y'), 'JAM UKUR': waktu_sekarang.strftime('%H:%M:%S'), 'R Utama': str(r_utama), 'S Utama': str(s_utama), 'T Utama': str(t_utama), 'N Utama': str(n_utama), 'R Line A': str(r_a), 'S Line A': str(s_a), 'T Line A': str(t_a), 'N Line A': str(n_a), 'R Line B': str(r_b), 'S Line B': str(s_b), 'T Line B': str(t_b), 'N Line B': str(n_b), 'R Line C': str(r_c), 'S Line C': str(s_c), 'T Line C': str(t_c), 'N Line C': str(n_c), 'R Line D': str(r_d), 'S Line D': str(s_d), 'T Line D': str(t_d), 'N Line D': str(n_d), }
                    with st.spinner('Menyimpan & Mencatat Perubahan...'):
                        if update_data_api(selected_gardu_data['NAMA GARDU'], selected_gardu_data.to_dict(), data_to_update):
                            st.success("Data berhasil diperbarui dan histori dicatat!")
                            st.cache_data.clear()
                            st.rerun()

def page_tambah_data():
    """Halaman untuk menambah data gardu baru."""
    st.title("➕ Formulir Tambah Data Gardu Baru")
    with st.form(key='add_new_form', clear_on_submit=True):
        st.subheader("Informasi Umum")
        penyulang, nama_gardu = st.text_input("PENYULANG"), st.text_input("NAMA GARDU (Harus Unik)")
        kapasitas, konstruksi = st.number_input("KAPASITAS (kVA)", min_value=0, step=25), st.text_input("KONSTRUKSI")
        alamat, peruntukan = st.text_area("ALAMAT"), st.selectbox("PERUNTUKAN", ["Umum", "Khusus"])
        st.divider()
        st.subheader("Informasi Pengukuran Awal")
        beban_va, status = st.number_input("BEBAN (VA)", min_value=0.0, step=100.0), st.selectbox("STATUS BEBAN", ["NORMAL", "CRITICAL LOAD", "OVERLOAD", "LIGHTLY LOAD"])
        def create_line_input_new(line_prefix):
            st.write(f"**Arus {line_prefix} (Ampere)**"); cols = st.columns(4)
            r = cols[0].number_input("R", key=f'r_{line_prefix}_new', min_value=0)
            s = cols[1].number_input("S", key=f's_{line_prefix}_new', min_value=0)
            t = cols[2].number_input("T", key=f't_{line_prefix}_new', min_value=0)
            n = cols[3].number_input("N", key=f'n_{line_prefix}_new', min_value=0)
            return r, s, t, n
        r_utama, s_utama, t_utama, n_utama = create_line_input_new("Utama")
        r_a, s_a, t_a, n_a = create_line_input_new("Line A")
        r_b, s_b, t_b, n_b = create_line_input_new("Line B")
        r_c, s_c, t_c, n_c = create_line_input_new("Line C")
        r_d, s_d, t_d, n_d = create_line_input_new("Line D")
        st.write("**Tegangan (V)**"); cols_v = st.columns(3)
        v_rn, v_sn, v_tn = cols_v[0].number_input("V R-N", key='v_rn_new', min_value=0), cols_v[1].number_input("V S-N", key='v_sn_new', min_value=0), cols_v[2].number_input("V T-N", key='v_tn_new', min_value=0)
        if st.form_submit_button("Simpan Data Baru"):
            if not penyulang or not nama_gardu:
                st.warning("Penyulang dan Nama Gardu wajib diisi!")
            else:
                waktu_sekarang = datetime.now(WIB)
                new_data = { 'PENYULANG': penyulang, 'NAMA GARDU': nama_gardu, 'KAPASITAS': str(kapasitas), 'KONSTRUKSI': konstruksi, 'ALAMAT': alamat, 'PERUNTUKAN': peruntukan, 'BEBAN (VA)': str(beban_va), 'STATUS': status, 'TANGGAL UKUR': waktu_sekarang.strftime('%m/%d/%Y'), 'JAM UKUR': waktu_sekarang.strftime('%H:%M:%S'), 'R Utama': str(r_utama), 'S Utama': str(s_utama), 'T Utama': str(t_utama), 'N Utama': str(n_utama), 'R Line A': str(r_a), 'S Line A': str(s_a), 'T Line A': str(t_a), 'N Line A': str(n_a), 'R Line B': str(r_b), 'S Line B': str(s_b), 'T Line B': str(t_b), 'N Line B': str(n_b), 'R Line C': str(r_c), 'S Line C': str(s_c), 'T Line C': str(t_c), 'N Line C': str(n_c), 'R Line D': str(r_d), 'S Line D': str(s_d), 'T Line D': str(t_d), 'N Line D': str(n_d), 'V R-N': str(v_rn), 'V S-N': str(v_sn), 'V T-N': str(v_tn) }
                with st.spinner("Menyimpan data baru..."):
                    if add_data_api(new_data):
                        st.success("Data gardu baru berhasil ditambahkan!")
                        st.cache_data.clear()

def page_history():
    """Halaman untuk menampilkan history perubahan."""
    st.title("📜 History Perubahan Data")
    st.info("Menampilkan 100 catatan perubahan terakhir.")
    history_df = load_data(HISTORY_SHEET_API_URL)
    if not history_df.empty:
        history_df['Timestamp'] = pd.to_datetime(history_df['Timestamp'])
        history_df = history_df.sort_values(by="Timestamp", ascending=False).head(100)
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Belum ada riwayat perubahan data yang tercatat.")

# =================================================================================
# NAVIGASI UTAMA (SIDEBAR) & STRUKTUR HALAMAN
# =================================================================================
with st.sidebar:
    try:
        st.image("Logo_PLN.png", width=100) 
    except Exception:
        st.warning("File Logo_PLN.png tidak ditemukan.")
    st.markdown("## PLN ULP BLIMBING")
    st.markdown("---")
    menu_pilihan = st.selectbox(
        "Pilih Menu:",
        ("Home", "Monitoring Gardu", "Tambah Data", "History"),
        key="main_menu"
    )
    st.markdown("---")
    st.write(f"**Tanggal:** {datetime.now(WIB).strftime('%d-%m-%Y')}")
    st.write(f"**Jam:** {datetime.now(WIB).strftime('%H:%M:%S')}")
    st.markdown("---")
    st.write("Create by University of Brawijaya 2025")
    st.write("@Andreas Wirawan Dananjaya")
    st.write("@Danish Gyan Pramana")

if menu_pilihan == "Home":
    page_home()
elif menu_pilihan == "Monitoring Gardu":
    page_monitoring_update()
elif menu_pilihan == "Tambah Data":
    page_tambah_data()
elif menu_pilihan == "History":
    page_history()