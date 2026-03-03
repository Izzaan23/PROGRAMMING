import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from pyproj import Transformer
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

# --- 3. ANTARAMUKA LOG MASUK & RESET ---
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
            st.button("Kembali", on_click=lambda: st.session_state.__setitem__('page', 'login'))
        else:
            st.title("Sistem Plotter Geomatik PUO")
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            if st.button("🔓 Log Masuk", use_container_width=True):
                if u_id == "admin" and u_pass == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('page', 'reset'))
        st.caption("Pembangun Sistem: Izzaan")
    st.stop()

# --- 4. FUNGSI GEOMATIK (Cassini EPSG:4390 -> WGS84) ---
# Kita perlukan penukaran koordinat supaya boleh duduk atas Google Maps
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_brg_dst(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn))
    if brg < 0: brg += 360
    d = int(brg); m = int((brg-d)*60); s = round((((brg-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", dist

# --- 5. SIDEBAR & KAWALAN ---
st.success(f"👋 Selamat Datang, **Izzaan**!")
st.sidebar.header("⚙️ Kawalan Visual")
p_label = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
p_stn = st.sidebar.toggle("Papar No Stesen", value=True)
s_font = st.sidebar.slider("Saiz Tulisan", 8, 18, 11)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER INTERAKTIF ---
st.title("📍 Plotter Interaktif Google Satellite")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper().strip() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Tukar koordinat Cassini ke Lat/Lon
        coords_wgs = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'] = [c[0] for c in coords_wgs]
        df['lat'] = [c[1] for c in coords_wgs]
        
        # Cipta peta Folium
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], control_scale=True)
        
        # Tambah Google Satellite yang boleh zoom
        google_sat = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}' # y = hybrid (ada jalan)
        folium.TileLayer(tiles=google_sat, attr='Google Satellite', name='Google').add_to(m)

        # Lukis Garisan (Cyan)
        poly_pts = [[r['lat'], r['lon']] for _, r in df.iterrows()]
        folium.Polygon(locations=poly_pts, color="cyan", weight=3, fill=False).add_to(m)

        # Tambah Label Bearing/Jarak & No Stesen
        for i in range(len(df)):
            p1_row = df.iloc[i]
            p2_row = df.iloc[(i+1)%len(df)]
            
            # 1. Label No Stesen (Kuning)
            if p_stn:
                folium.map.Marker(
                    [p1_row['lat'], p1_row['lon']],
                    icon=folium.DivIcon(html=f"""<div style="font-size: {s_font}pt; color: yellow; 
                    font-weight: bold; text-shadow: 2px 2px 2px black;">{int(p1_row['STN'])}</div>""")
                ).add_to(m)
                folium.CircleMarker([p1_row['lat'], p1_row['lon']], radius=3, color='red', fill=True).add_to(m)

            # 2. Label Bearing/Jarak (Kotak Putih)
            if p_label:
                brg_txt, dst_val = kira_brg_dst([p1_row['E'], p1_row['N']], [p2_row['E'], p2_row['N']])
                mid_lat = (p1_row['lat'] + p2_row['lat']) / 2
                mid_lon = (p1_row['lon'] + p2_row['lon']) / 2
                
                folium.map.Marker(
                    [mid_lat, mid_lon],
                    icon=folium.DivIcon(html=f"""<div style="background: white; border: 1px solid red; 
                    padding: 2px; border-radius: 3px; font-size: {s_font-2}pt; color: red; font-weight: bold; 
                    text-align: center; width: 80px;">{brg_txt}<br>{dst_val:.2f}m</div>""")
                ).add_to(m)

        # Auto-Zoom ke arah Traverse
        m.fit_bounds(poly_pts)

        # Paparkan Peta
        folium_static(m, width=1000, height=600)

        with st.expander("📊 Lihat Jadual Data"):
            st.dataframe(df[['STN', 'E', 'N']])

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO")
