import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from pyproj import Transformer
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. SISTEM DATABASE KATA LALUAN ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- 3. ANTARAMUKA LOG MASUK & RESET PASSWORD ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=120)
        
        if st.session_state.page == "reset":
            st.subheader("🔑 Set Semula Kata Laluan")
            new_p = st.text_input("Kata Laluan Baru", type="password")
            conf_p = st.text_input("Sahkan Kata Laluan", type="password")
            if st.button("Kemaskini Kata Laluan", use_container_width=True):
                if new_p == conf_p and new_p != "":
                    st.session_state.db_password = new_p
                    st.session_state.page = "login"
                    st.success("✅ Berjaya! Sila log masuk semula.")
                    st.rerun()
                else:
                    st.error("❌ Kata laluan tidak padan.")
            st.button("Kembali", on_click=lambda: st.session_state.__setitem__('page', 'login'))
        else:
            st.title("Sistem Plotter Geomatik PUO")
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            if st.button("🔓 Log Masuk", use_container_width=True):
                if u_id == "admin" and u_pass == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('page', 'reset'))
        st.markdown("---")
        st.caption("Pembangun Sistem: Izzaan")
    st.stop()

# --- 4. FUNGSI GEOMATIK (EPSG:4390 ke WGS84) ---
# Folium memerlukan Lat/Long, jadi kita kena tukar koordinat Cassini
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak

# --- 5. SIDEBAR ---
st.success(f"👋 Selamat Datang, **Izzaan**!")
st.sidebar.header("⚙️ Kawalan Visual")
p_sat_label = st.sidebar.toggle("On/Off Label Google Maps", value=True)
p_brg_dist = st.sidebar.toggle("On/Off Bearing & Jarak", value=True)
p_stn_label = st.sidebar.toggle("On/Off No Stesen", value=True)
s_font = st.sidebar.slider("Saiz Tulisan", 8, 20, 10)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER ---
st.title("📍 Plotter Interaktif Cassini (EPSG:4390)")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # 1. Tukar koordinat ke Lat/Long untuk peta
        coords_wgs = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'] = [c[0] for c in coords_wgs]
        df['lat'] = [c[1] for c in coords_wgs]
        
        # 2. Inisialisasi Peta Folium
        m = folium.Map(control_scale=True)

        # 3. Masukkan Google Satellite (Boleh Zoom)
        # lyrs=s (Satelit bersih), lyrs=y (Satelit + Jalan)
        tile_type = 'y' if p_sat_label else 's'
        google_url = f'https://mt1.google.com/vt/lyrs={tile_type}&x={{x}}&y={{y}}&z={{z}}'
        folium.TileLayer(tiles=google_url, attr='Google Satellite', name='Google').add_to(m)

        # 4. Plot Poligon Traverse (Cyan)
        poly_points = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(locations=poly_points, color="cyan", weight=3, fill=False).add_to(m)

        # 5. Plot Bearing & Jarak (Gaya Gambar No. 2)
        if p_brg_dist:
            for i in range(len(df)):
                p1, p2 = df.iloc[i], df.iloc[(i+1)%len(df)]
                brg_str, dst_val = kira_bearing_jarak([p1['E'], p1['N']], [p2['E'], p2['N']])
                mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
                
                # Label gaya kotak putih teks merah
                folium.map.Marker(
                    [mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f"""<div style="font-family: Arial; color: red; background: white; 
                    padding: 2px 5px; border-radius: 3px; font-size: {s_font-2}pt; font-weight: bold; 
                    text-align: center; width: 80px; border: 1px solid gray;">{brg_str}<br>{dst_val:.2f}m</div>""")
                ).add_to(m)

        # 6. Plot No Stesen (Gaya Gambar No. 2)
        cx, cy = df['lon'].mean(), df['lat'].mean()
        for _, row in df.iterrows():
            # Marker Bucu Merah (Boleh klik untuk info)
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=4, color="red", fill=True, fill_color="red",
                popup=f"Stn: {int(row['STN'])}<br>E: {row['E']:.3f}<br>N: {row['N']:.3f}"
            ).add_to(m)

            # Label No Stesen Kuning (Tolak ke luar)
            if p_stn_label:
                off_lat, off_lon = (row['lat'] - cy) * 0.15, (row['lon'] - cx) * 0.15
                folium.map.Marker(
                    [row['lat'] + off_lat, row['lon'] + off_lon],
                    icon=folium.DivIcon(html=f"""<div style="font-size: {s_font}pt; color: yellow; font-weight: bold; 
                    text-shadow: 2px 2px 4px black; width: 30px;">{int(row['STN'])}</div>""")
                ).add_to(m)

        # 7. AUTO-ZOOM (Supaya tidak zoom out sangat)
        m.fit_bounds(poly_points)

        # 8. Paparkan Peta
        folium_static(m, width=1000, height=600)
        
        with st.expander("📊 Jadual Data Koordinat"):
            st.dataframe(df[['STN', 'E', 'N']], use_container_width=True)

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO")
