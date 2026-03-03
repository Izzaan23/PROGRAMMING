import streamlit as st
import pandas as pd
import numpy as np
import json

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. SISTEM LOG MASUK (DI TENGAH) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Menggunakan columns untuk meletakkan kotak login di tengah
    _, col_mid, _ = st.columns([1, 2, 1])
    
    with col_mid:
        st.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=100)
        st.title("Sistem Plotter Geomatik PUO")
        st.subheader("Sila Log Masuk")
        
        user_id = st.text_input("ID Pengguna (admin)")
        password_input = st.text_input("Kata Laluan (admin123)", type="password")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔓 Log Masuk", use_container_width=True):
                if user_id == "admin" and password_input == "admin123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan Salah!")
        
        with col_btn2:
            if st.button("❓ Lupa Password", use_container_width=True):
                st.info("Sila hubungi Penyelaras Unit Geomatik atau Admin IT Jabatan untuk menetap semula kata laluan anda. \n\n📧 admin.geomatik@puo.edu.my")
    st.stop()

# --- 3. FUNGSI GEOMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak, bearing

# --- 4. SIDEBAR TETAPAN (ON/OFF) ---
st.sidebar.header("⚙️ Kawalan Visual")
papar_satelit = st.sidebar.toggle("Boleh on off satelit imej", value=True)
papar_brg_dist = st.sidebar.toggle("Boleh on off bering dan jarak", value=True)
papar_stn = st.sidebar.toggle("Boleh on off label stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📏 Saiz & Jarak")
saiz_font = st.sidebar.slider("Saiz Tulisan", 5, 20, 9)
dist_offset = st.sidebar.slider("Jarak Label dari Garisan", 1.0, 10.0, 3.0)
stn_offset = st.sidebar.slider("Jarak No Stesen", 1.0, 15.0, 5.0)

# --- 5. PEMPROSESAN PLOT (MATPLOTLIB UNTUK STABILITI) ---
st.title("📍 Plotter Poligon Interaktif")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    # Pelarasan Cassini ke Koordinat Tempatan
    if 'E' in df.columns and 'N' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 10))
        cx_mean, cy_mean = df['E'].mean(), df['N'].mean()
        luas = kira_luas(df['E'].values, df['N'].values)
        perimeter = 0

        # Plot Garisan
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='yellow' if papar_satelit else 'black', linewidth=2, zorder=5)
            
            brg, dst, ang = kira_bearing_jarak(p1, p2)
            perimeter += dst
            
            if papar_brg_dist:
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                ax.text(mid_x, mid_y, f"{brg}\n{dst:.3f}m", color='cyan' if papar_satelit else 'blue', 
                        fontsize=saiz_font, fontweight='bold', ha='center')

        # No Stesen di Luar
        if papar_stn:
            for _, row in df.iterrows():
                dx, dy = row['E']-cx_mean, row['N']-cy_mean
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E']+(dx/mag)*stn_offset, row['N']+(dy/mag)*stn_offset, 
                        str(int(row['STN'])), color='yellow' if papar_satelit else 'red', 
                        fontweight='bold', ha='center', fontsize=saiz_font+2)

        # Butang Eksport GIS
        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist()]}}
        st.sidebar.download_button("🚀 Eksport ke GIS (.json)", data=json.dumps(geojson), file_name="data_gis.json")

        # Paparan Peta
        if papar_satelit:
            import contextily as cx
            try:
                cx.add_basemap(ax, crs="EPSG:4390", source="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", zoom=18)
            except: pass
        
        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # --- 6. INFO INTERAKTIF (TABLE & CLICK INFO) ---
        st.divider()
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("📋 Jadual Stesen")
            st.table(df)
        with col_t2:
            st.subheader("ℹ️ Maklumat Poligon")
            st.success(f"**Luas:** {luas:.3f} m²")
            st.info(f"**Perimeter:** {perimeter:.3f} m")
            st.warning(f"**Klik Info:** Gunakan jadual untuk melihat koordinat tepat setiap stesen.")
