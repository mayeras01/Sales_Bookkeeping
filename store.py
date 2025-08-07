import streamlit as st
import pandas as pd
from datetime import date
from firebase_admin import credentials, firestore, initialize_app
import json

# --- CONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Python App | Bookkeeping",
    page_icon="🐍",
    layout="wide"
)

# --- INICIALISASI FIREBASE ---
# Mendapatkan konfigurasi Firebase dari lingkungan eksekusi
firebase_config_str = st.secrets["firebase_config"]
firebase_config = json.loads(firebase_config_str)

# Inisialisasi Firebase jika belum diinisialisasi
try:
    cred = credentials.Certificate(firebase_config)
    initialize_app(cred)
except ValueError:
    st.info("Firebase sudah diinisialisasi.")

db = firestore.client()

# --- INICIALISASI SESSION STATE ---
# Session state adalah cara Streamlit menyimpan data antar re-run
if 'penjualan' not in st.session_state:
    st.session_state['penjualan'] = []

# --- FUNGSI UNTUK MENAMBAH PENJUALAN KE DATABASE ---
def tambahkan_penjualan_ke_db(nama_barang, harga_satuan, jumlah_barang):
    """Menambahkan data penjualan baru ke Firestore."""
    total_harga = harga_satuan * jumlah_barang
    today = date.today().isoformat()
    
    penjualan_baru = {
        "nama_barang": nama_barang,
        "harga_satuan": harga_satuan,
        "jumlah_barang": jumlah_barang,
        "total_harga": total_harga,
        "tanggal": today,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    
    try:
        db.collection("penjualan").add(penjualan_baru)
        st.success(f"Penjualan '{nama_barang}' sebanyak {jumlah_barang} berhasil ditambahkan!")
    except Exception as e:
        st.error(f"Gagal menambahkan data ke database: {e}")

# --- TATA LETAK HALAMAN ---
st.title("💰 Sales Bookkeeping Application")

col1, col2 = st.columns(2)

with col1:
    st.header("Tambah Penjualan Baru")
    
    with st.form("form_penjualan"):
        nama_barang = st.text_input("Nama Barang", placeholder="Contoh: Kopi, Meja, dll.")
        harga_satuan = st.number_input("Harga Satuan (Rp)", min_value=0, step=1000)
        jumlah_barang = st.number_input("Jumlah Barang", min_value=1, step=1)
        
        submitted = st.form_submit_button("Tambahkan Penjualan")
        
        if submitted:
            if nama_barang and harga_satuan > 0 and jumlah_barang > 0:
                tambahkan_penjualan_ke_db(nama_barang, harga_satuan, jumlah_barang)
            else:
                st.error("Nama barang tidak boleh kosong, dan harga/jumlah harus lebih dari 0!")

with col2:
    st.header("Laporan Penjualan")
    st.markdown("---")
    
    # Ambil data dari database secara real-time
    penjualan_stream = db.collection("penjualan").stream()
    st.session_state['penjualan'] = [doc.to_dict() for doc in penjualan_stream]

    if st.session_state.penjualan:
        df_penjualan = pd.DataFrame(st.session_state.penjualan)
        df_penjualan.rename(columns={
            'nama_barang': 'Nama Barang',
            'harga_satuan': 'Harga Satuan',
            'jumlah_barang': 'Jumlah Barang',
            'total_harga': 'Total Harga',
            'tanggal': 'Tanggal'
        }, inplace=True)
        
        st.dataframe(df_penjualan, use_container_width=True)
        
        total_semua = df_penjualan["Total Harga"].sum()
        st.subheader(f"Total Keseluruhan Penjualan: Rp {total_semua:,.2f}")
    else:
        st.info("Belum ada data penjualan.")

st.write("---")

st.header("📊 Analisis Pemasukan")
if st.session_state.penjualan:
    df_all_sales = pd.DataFrame(st.session_state.penjualan)
    df_all_sales["tanggal"] = pd.to_datetime(df_all_sales["tanggal"])

    chart_type = st.selectbox(
        "Pilih Tipe Diagram",
        ("Diagram Garis", "Diagram Batang")
    )
    timeframe = st.selectbox(
        "Pilih Rentang Waktu",
        ("Harian", "Mingguan", "Bulanan")
    )

    if timeframe == "Harian":
        df_aggregated = df_all_sales.groupby(df_all_sales['tanggal'].dt.date)['total_harga'].sum().reset_index()
        df_aggregated.columns = ["Tanggal", "Pemasukan"]
    elif timeframe == "Mingguan":
        df_aggregated = df_all_sales.groupby(df_all_sales['tanggal'].dt.to_period('W'))['total_harga'].sum().reset_index()
        df_aggregated['Tanggal'] = df_aggregated['tanggal'].astype(str)
        df_aggregated.columns = ["Periode", "Pemasukan"]
    elif timeframe == "Bulanan":
        df_aggregated = df_all_sales.groupby(df_all_sales['tanggal'].dt.to_period('M'))['total_harga'].sum().reset_index()
        df_aggregated['Tanggal'] = df_aggregated['tanggal'].astype(str)
        df_aggregated.columns = ["Periode", "Pemasukan"]
    
    if chart_type == "Diagram Garis":
        st.line_chart(df_aggregated, x=df_aggregated.columns[0], y="Pemasukan")
    elif chart_type == "Diagram Batang":
        st.bar_chart(df_aggregated, x=df_aggregated.columns[0], y="Pemasukan")
else:
    st.info("Belum ada data pemasukan untuk ditampilkan dalam grafik.")

st.markdown("""
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f1f1f1;
        color: #333;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #ccc;
    }
    </style>
    <div class="footer">
        © 2025 by Mayer Amut Saleko | Powered by Streamlit
    </div>
""", unsafe_allow_html=True)