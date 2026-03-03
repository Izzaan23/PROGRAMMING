import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import contextily as cx

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Plotter", layout="wide")

# --- 2. SISTEM AKSES (ID & PASSWORD) ---
st.sidebar.header("🔒 Akses Sistem")
user_id = st.sidebar.text_input("ID Pengguna", placeholder="Masukkan ID anda")
password_input = st.sidebar.text_input("Kata Laluan", type="password", placeholder="Masukkan Password")

if user_id == "admin" and password_input == "admin123":
    st.sidebar.success(f"Log Masuk Berjaya: {user_id.upper()} ✅")
else:
    if user_id == "" and password_input == "":
        st.warning("⚠️ Sila masukkan ID dan Password.")
    else:
        st.error("❌ ID atau Password Salah!")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("❓ Lupa Kata Laluan?"):
        st.sidebar.info("Hubungi Admin Geomatik PUO.\n📧 admin.geomatik@puo.edu.my")
    st.stop() 

# --- 3. FUNGSI MATEMATIK ---
def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    return to_dms(bearing), jarak, bearing

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- 4. SIDEBAR TETAPAN ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Paparan")
pilihan_peta = st.sidebar.selectbox(
    "🗺️ Peta Latar:", 
    ["Tiada Peta", "OpenStreetMap", "Esri World Imagery", "Google Satellite", "Google Hybrid"]
)
on_off_satelit = pilihan_peta != "Tiada Peta"

st.sidebar.markdown("---")
st.sidebar.header("📏 Saiz Tulisan")
saiz_stn = st.sidebar.slider("Saiz No. Stesen", 5, 25, 11)
saiz_bearing = st.sidebar.slider("Saiz Teks Bearing", 5, 15, 9)
saiz_jarak = st.sidebar.slider("Saiz Teks Jarak", 5, 15, 8)
jarak_offset_stn = st.sidebar.slider("Jarak No. Stesen (m)", 0.5, 10.0, 4.0)

epsg_code = st.sidebar.text_input("Kod EPSG (Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin)", 10, 500, 100) # Minimum 10 untuk elak ralat data

# --- 5. HEADER UTAMA ---
st.title("POLITEKNIK UNGKU OMAR")
st.subheader("Jabatan Kejuruteraan Geomatik - Plotter Poligon")
st.divider()

uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    # Pelarasan Stesen 1 (Perak)
    target_n, target_e = 6757.654, 115594.785
    if 'STN' in df.columns and 1 in df['STN'].values:
        idx_1 = df[df['STN'] == 1].index[0]
        df['E'] += (target_e - df.at[idx_1, 'E'])
        df['N'] += (target_n - df.at[idx_1, 'N'])

    if 'E' in df.columns and 'N' in df.columns:
        luas_semasa = kira_luas(df['E'].values, df['N'].values)
        fig, ax = plt.subplots(figsize=(12, 12))
        
        is_dark = any(x in pilihan_peta for x in ["Satellite", "Imagery", "Hybrid"])
        warna_garisan = 'yellow' if is_dark else 'black'
        warna_brg = 'cyan' if is_dark else 'darkred'
        warna_dist = 'white' if is_dark else 'blue'
        warna_stn = 'yellow' if is_dark else 'black'

        points = df[['E', 'N']].values
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])

        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=warna_garisan, marker='o', markersize=3, linewidth=1.5, zorder=5)
            
            brg_str, dist_val, brg_deg = kira_bearing_jarak(p1, p2)
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            txt_rot = 90 - brg_deg
            if txt_rot < -90: txt_rot += 180
            if txt_rot > 90: txt_rot -= 180
            
            # Bearing (Atas) & Jarak (Bawah) - Seragam di tengah
            ax.text(mid_x, mid_y, brg_str, color=warna_brg, fontsize=saiz_bearing, 
                    rotation=txt_rot, ha='center', va='bottom', fontweight='bold', rotation_mode='anchor')
            ax.text(mid_x, mid_y, f"{dist_val:.3f}m", color=warna_dist, fontsize=saiz_jarak, 
                    rotation=txt_rot, ha='center', va='top', fontweight='bold', rotation_mode='anchor')

        # No Stesen di Luar
        for _, row in df.iterrows():
            dx, dy = row['E'] - cx_mean, row['N'] - cy_mean
            mag = np.sqrt(dx**2 + dy**2)
            ax.text(row['E'] + (dx/mag)*jarak_offset_stn, row['N'] + (dy/mag)*jarak_offset_stn, 
                    str(int(row['STN'])), color=warna_stn, fontsize=saiz_stn, fontweight='bold', ha='center', va='center')

        # --- LOGIK SATELIT STABIL ---
        if on_off_satelit:
            try:
                if "Google Satellite" in pilihan_peta:
                    url = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                elif "Google Hybrid" in pilihan_peta:
                    url = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                elif "Esri" in pilihan_peta:
                    url = cx.providers.Esri.WorldImagery
                else:
                    url = cx.providers.OpenStreetMap.Mapnik
                
                # Kunci Zoom=18 untuk elak ralat "Map data not available"
                cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=url, zoom=18, zorder=0)
            except:
                st.sidebar.warning("Cuba besarkan Margin Meter jika peta tidak keluar.")

        ax.set_aspect('equal')
        ax.set_xlim(df['E'].min() - margin_meter, df['E'].max() + margin_meter)
        ax.set_ylim(df['N'].min() - margin_meter, df['N'].max() + margin_meter)
        ax.axis('off') 
        
        st.pyplot(fig)
        st.success(f"📐 Luas Poligon: {luas_semasa:.3f} m²")
