import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. SISTEM LOG MASUK (TENGAH) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Pastikan fail logo l.png ada dalam folder yang sama
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=150)
        st.title("Sistem Plotter Geomatik PUO")
        user_id = st.text_input("ID Pengguna")
        password_input = st.text_input("Kata Laluan", type="password")
        if st.button("🔓 Log Masuk", use_container_width=True):
            if user_id == "admin" and password_input == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("ID atau Kata Laluan Salah!")
    st.stop()

# --- 3. FUNGSI MATEMATIK ---
def kira_luas(x, y):
    # Pengiraan luas menggunakan formula shoelace
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak, bearing

# --- 4. SIDEBAR TETAPAN ---
st.sidebar.header("⚙️ Tetapan Visual")
papar_satelit = st.sidebar.checkbox("Papar Imej Satelit", value=True)
papar_brg_dist = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
papar_stn = st.sidebar.checkbox("Papar Label Stesen (STN)", value=True)

st.sidebar.markdown("---")
saiz_font = st.sidebar.slider("Saiz Tulisan", 3, 15, 7)
stn_offset = st.sidebar.slider("Jarak No Stesen", 1.0, 10.0, 4.0)
st.sidebar.info("Sistem Koordinat: EPSG:4390 (Perak)")

# --- 5. PEMPROSESAN DATA ---
st.title("📍 Plotter Poligon Cassini Perak (4390)")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Penyelarasan Stesen 1 (Pelarasan Automatik ke Koordinat Sasaran)
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        fig, ax = plt.subplots(figsize=(10, 8))
        cx_m, cy_m = df['E'].mean(), df['N'].mean()
        
        # Plot Garisan Poligon (Cyan)
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2.5, zorder=3)
            
            if papar_brg_dist:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                
                # Rotasi teks selari dengan garisan
                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                
                ax.text(mid_x, mid_y, f"{brg_str}\n{dst_val:.2f}m", 
                        color='red', fontsize=saiz_font, fontweight='bold', 
                        ha='center', va='center', rotation=txt_rot, zorder=5,
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

        # Plot Titik Bucu Merah
        ax.scatter(df['E'], df['N'], color='red', s=50, edgecolors='white', zorder=10)

        # Label Stesen (Kuning)
        if papar_stn:
            for _, row in df.iterrows():
                dx, dy = row['E']-cx_m, row['N']-cy_m
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E']+(dx/mag)*stn_offset, row['N']+(dy/mag)*stn_offset, 
                        f"{row['STN']}", color='yellow', fontweight='bold', 
                        ha='center', fontsize=saiz_font+2,
                        bbox=dict(facecolor='black', alpha=0.6, edgecolor='none', pad=0.5))

        # Tambah Peta Satelit (EPSG:4390)
        if papar_satelit:
            try:
                # Menggunakan Esri World Imagery (Lebih stabil untuk 4390)
                cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=19)
            except:
                st.sidebar.error("Ralat memuat peta satelit.")

        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # --- INFO INTERAKTIF & EKSPORT ---
        st.divider()
        st.subheader("📊 Maklumat Analisis Geomatik")
        
        # Simulasi Klik: Pilih stesen untuk info
        stn_pilihan = st.selectbox("Klik/Pilih Stesen untuk Info Koordinat:", df['STN'].unique())
        row_stn = df[df['STN'] == stn_pilihan].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.info(f"📍 **Stesen:** {int(row_stn['STN'])}")
        col2.success(f"🌏 **East (E):** {row_stn['E']:.3f}")
        col3.success(f"🌏 **North (N):** {row_stn['N']:.3f}")

        # Ringkasan Luas (Gaya Gambar Anda)
        luas_m2 = kira_luas(df['E'].values, df['N'].values)
        st.markdown(f"""
            <div style="background-color:#white; padding:20px; border-radius:10px; border: 2px solid #28a745; text-align:center;">
                <h4 style="color:#28a745; margin:0;">LUAS KESELURUHAN</h4>
                <h1 style="color:black; margin:0;">{luas_m2:.2f} m²</h1>
            </div>
        """, unsafe_allow_html=True)

        # Butang Eksport GIS
        st.sidebar.markdown("---")
        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist()]}}
        st.sidebar.download_button("🚀 Eksport GIS (JSON)", data=json.dumps(geojson), file_name="perak_4390.json")
