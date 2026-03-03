import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
import contextily as cx
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik Plotter", layout="wide")

# --- 2. SISTEM PASSWORD ---
st.sidebar.header("🔒 Akses Sistem")
password_input = st.sidebar.text_input("Masukkan Password", type="password")

if password_input != "admin":
    if password_input == "":
        st.warning("⚠️ Halaman dikunci. Sila masukkan password di sidebar.")
    else:
        st.error("❌ Password Salah!")
    st.stop() 

st.sidebar.success("Akses Dibenarkan ✅")

# --- FUNGSI-FUNGSI MATEMATIK ---
def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de = p2[0] - p1[0]
    dn = p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    return to_dms(bearing), jarak, bearing

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- FUNGSI EKSPORT KE QGIS ---
def convert_to_geojson(df, luas, epsg):
    features = []
    coords = []
    for _, row in df.iterrows():
        coords.append([round(float(row['E']), 3), round(float(row['N']), 3)])
    coords.append([round(float(df.iloc[0]['E']), 3), round(float(df.iloc[0]['N']), 3)]) 
    
    poly_feature = {
        "type": "Feature",
        "properties": {"Layer": "Lot_Poligon", "Luas_m2": round(luas, 3)},
        "geometry": {"type": "Polygon", "coordinates": [coords]}
    }
    features.append(poly_feature)

    for i, row in df.iterrows():
        p1 = [row['E'], row['N']]; p2 = [df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N']]
        brg, dist, _ = kira_bearing_jarak(p1, p2)
        point_feature = {
            "type": "Feature",
            "properties": {"STN": int(row['STN']), "Bearing": brg, "Jarak_m": round(dist, 3)},
            "geometry": {"type": "Point", "coordinates": [round(float(row['E']), 3), round(float(row['N']), 3)]}
        }
        features.append(point_feature)

    geojson_data = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{epsg}"}
        },
        "features": features
    }
    return json.dumps(geojson_data, indent=4)

# --- SIDEBAR TETAPAN ---
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan Peta")

pilihan_peta = st.sidebar.selectbox(
    "🗺️ Jenis Paparan Peta:",
    ["Tiada Peta", "OpenStreetMap (Jalan)", "Google Satellite", "Google Hybrid"]
)

# Definisi pembolehubah kawalan paparan
on_off_satelit = pilihan_peta != "Tiada Peta"
papar_stn = st.sidebar.checkbox("Papar No. Stesen", value=True)
papar_brg_dist = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
papar_luas_label = st.sidebar.checkbox("Papar Label Luas", value=False)

epsg_code = st.sidebar.text_input("Kod EPSG (Cth Cassini Perak: 4390):", "4390")
margin_meter = st.sidebar.slider("🔍 Zum Keluar (Margin Meter)", 0, 100, 5)

# --- HEADER UTAMA ---
st.title("POLITEKNIK UNGKU OMAR")
st.subheader("Jabatan Kejuruteraan Geomatik - Plotter Poligon")
st.divider()

# --- MUAT NAIK FAIL ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Pastikan ada kolum STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    target_n, target_e = 6757.654, 115594.785

    if 'STN' in df.columns and 1 in df['STN'].values:
        idx_1 = df[df['STN'] == 1].index[0]
        shift_e = target_e - df.at[idx_1, 'E']
        shift_n = target_n - df.at[idx_1, 'N']
        df['E'] += shift_e
        df['N'] += shift_n
        st.success(f"📍 Stesen 1 dilaraskan ke: U={target_n}, B={target_e}")

    st.dataframe(df.set_index('STN'), use_container_width=True)

    if 'E' in df.columns and 'N' in df.columns:
        if 'tampilkan_luas' not in st.session_state:
            st.session_state.tampilkan_luas = False

        luas_semasa = kira_luas(df['E'].values, df['N'].values)
        
        # Eksport Sidebar
        st.sidebar.markdown("---")
        geojson_output = convert_to_geojson(df, luas_semasa, epsg_code)
        st.sidebar.download_button(label="🌍 MUAT TURUN FAIL QGIS", data=geojson_output, file_name="plot_puo.geojson", mime="application/json")

        # --- PLOTTING ---
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Warna ikut mod peta
        warna_garisan = 'yellow' if on_off_satelit else 'black'
        warna_teks_brg = 'cyan' if on_off_satelit else 'red'
        warna_teks_dist = 'white' if on_off_satelit else 'blue'

        points = df[['E', 'N']].values
        n_points = len(points)
        cx_mean, cy_mean = np.mean(df['E']), np.mean(df['N'])

        for i in range(n_points):
            p1, p2 = points[i], points[(i + 1) % n_points]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=warna_garisan, marker='o', linewidth=2, zorder=4)
            
            brg_str, dist, brg_val = kira_bearing_jarak(p1, p2)
            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
            
            if papar_brg_dist:
                rot = 90 - brg_val
                if rot < -90: rot += 180
                if rot > 90: rot -= 180
                ax.text(mid_x, mid_y, f"{brg_str}\n{dist:.3f}m", color=warna_teks_brg, fontsize=8, rotation=rot, ha='center', fontweight='bold')

        if papar_stn:
            for _, row in df.iterrows():
                ax.text(row['E'], row['N'], f" {int(row['STN'])}", color='black', fontweight='bold', bbox=dict(facecolor='yellow', alpha=0.7))

        if st.session_state.tampilkan_luas or papar_luas_label:
            ax.fill(df['E'], df['N'], alpha=0.3, color='green')
            ax.text(cx_mean, cy_mean, f"LUAS: {luas_semasa:.2f}m²", ha='center', bbox=dict(facecolor='white', alpha=0.8))

        if on_off_satelit:
            try:
                source = cx.providers.Esri.WorldImagery if "Satellite" in pilihan_peta else cx.providers.OpenStreetMap.Mapnik
                cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=source, zorder=0)
            except:
                st.error("Gagal muat peta latar. Sila semak Kod EPSG.")

        ax.set_aspect('equal')
        st.pyplot(fig)

        if st.button('📐 Kira & Papar Luas'):
            st.session_state.tampilkan_luas = True
            st.rerun()
