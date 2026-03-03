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

# --- 4. SIDEBAR TETAPAN (LABEL ON/OFF DIKEMBALIKAN) ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Paparan")

# Label On/Off yang anda minta
papar_satelit = st.sidebar.checkbox("Boleh on off satelit imej", value=True)
papar_brg_dist = st.sidebar.checkbox("Boleh on off bering dan jarak", value=True)
papar_stn_label = st.sidebar.checkbox("Boleh on off label stesen", value=True)

pilihan_peta = "Google Satellite" # Default jika satelit ON
if papar_satelit:
    pilihan_peta = st.sidebar.selectbox("Pilih Jenis Satelit:", ["Google Satellite", "Google Hybrid", "Esri World Imagery"])
else:
    pilihan_peta = st.sidebar.selectbox("Pilih Peta Jalan:", ["Tiada Peta", "OpenStreetMap"])

st.sidebar.markdown("---")
st.sidebar.header("📏 Saiz Tulisan")
saiz_stn = st.sidebar.slider("Saiz No. Stesen", 5, 25, 12)
saiz_bearing = st.sidebar.slider("Saiz Teks Bearing", 5, 15, 9)
saiz_jarak = st.sidebar.slider("Saiz Teks Jarak", 5, 15, 8)
jarak_offset_stn = st.sidebar.slider("Jarak No. Stesen (m)", 0.5, 15.0, 5.0)

epsg_code = st.sidebar.text_input("Kod EPSG (Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin)", 10, 1000, 150)

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
        
        # Plotting
        fig, ax = plt.subplots(figsize=(12, 12))
        is_dark = papar_satelit
        warna_garisan = 'yellow' if is_dark else 'black'
        warna_brg = 'cyan' if is_dark else 'darkred'
        warna_dist = 'white' if is_dark else 'blue'
        warna_stn = 'yellow' if is_dark else 'black'

        points = df[['E', 'N']].values
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])
        total_perimeter = 0

        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=warna_garisan, marker='o', markersize=4, linewidth=2, zorder=5)
            
            brg_str, dist_val, brg_deg = kira_bearing_jarak(p1, p2)
            total_perimeter += dist_val
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            if papar_brg_dist:
                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                ax.text(mid_x, mid_y, brg_str, color=warna_brg, fontsize=saiz_bearing, rotation=txt_rot, ha='center', va='bottom', fontweight='bold', rotation_mode='anchor')
                ax.text(mid_x, mid_y, f"{dist_val:.3f}m", color=warna_dist, fontsize=saiz_jarak, rotation=txt_rot, ha='center', va='top', fontweight='bold', rotation_mode='anchor')

        if papar_stn_label:
            for _, row in df.iterrows():
                dx, dy = row['E'] - cx_mean, row['N'] - cy_mean
                mag = np.sqrt(dx**2 + dy**2)
                ax.text(row['E'] + (dx/mag)*jarak_offset_stn, row['N'] + (dy/mag)*jarak_offset_stn, str(int(row['STN'])), color=warna_stn, fontsize=saiz_stn, fontweight='bold', ha='center', va='center')

        # Logik Satelit
        if papar_satelit or pilihan_peta != "Tiada Peta":
            try:
                if "Google Satellite" in pilihan_peta:
                    url = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                elif "Google Hybrid" in pilihan_peta:
                    url = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                elif "Esri" in pilihan_peta:
                    url = cx.providers.Esri.WorldImagery
                else:
                    url = cx.providers.OpenStreetMap.Mapnik
                cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=url, zoom=19, zorder=0)
            except:
                st.sidebar.warning("Sila besarkan Margin Meter untuk memuatkan imej satelit.")

        ax.set_aspect('equal')
        ax.set_xlim(df['E'].min() - margin_meter, df['E'].max() + margin_meter)
        ax.set_ylim(df['N'].min() - margin_meter, df['N'].max() + margin_meter)
        ax.axis('off')
        st.pyplot(fig)

        # --- 6. BAHAGIAN INFO STESEN & POLIGON (BARU) ---
        st.divider()
        st.subheader("📊 Maklumat Analisis Geomatik")
        
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.info("🏠 **Info Poligon**")
            st.write(f"- **Luas Keseluruhan:** {luas_semasa:.3f} m²")
            st.write(f"- **Luas (Ekar):** {luas_semasa * 0.000247105:.4f} ekar")
            st.write(f"- **Perimeter:** {total_perimeter:.3f} meter")
            st.write(f"- **Kod EPSG Gunapakai:** {epsg_code}")

        with col_info2:
            st.info("📍 **Info Stesen (Koordinat Terlaras)**")
            st.dataframe(df[['STN', 'E', 'N']].set_index('STN'), use_container_width=True)

        st.success("Nota: Stesen 1 telah dilaraskan secara automatik ke koordinat Cassini Perak.")
