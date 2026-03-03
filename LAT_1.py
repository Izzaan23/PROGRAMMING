# --- SIDEBAR TETAPAN ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Peta")

# Pilihan jenis peta
pilihan_peta = st.sidebar.selectbox(
    "🗺️ Jenis Paparan Peta:",
    ["Tiada Peta", "OpenStreetMap (Jalan)", "Google Satellite", "Google Hybrid (Satelit + Jalan)"]
)

# --- TAMBAH KOD DI BAWAH INI ---
# Logik untuk on_off_satelit (Benar jika bukan "Tiada Peta")
on_off_satelit = pilihan_peta != "Tiada Peta"

# Tambah Checkbox untuk kawalan paparan
papar_stn = st.sidebar.checkbox("Papar No. Stesen", value=True)
papar_brg_dist = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
papar_luas_label = st.sidebar.checkbox("Papar Label Luas", value=False)
# ------------------------------

epsg_code = st.sidebar.text_input("Kod EPSG (Cth Cassini Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin Meter)", 0, 100, 5)
