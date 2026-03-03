import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from pyproj import Transformer
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Geomatik Izzaan", layout="wide")

# --- 2. SISTEM LOG MASUK & RESET ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "reset_mode" not in st.session_state:
    st.session_state.reset_mode = False

if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists("logo l.png"):
            st.image("logo l.png", width=120)
        
        if st.session_state.reset_mode:
            st.subheader("🔑 Set Semula Kata Laluan")
            new_p = st.text_input("Kata Laluan Baru", type="password")
            conf_p = st.text_input("Sahkan Kata Laluan", type="password")
            if st.button("Kemaskini Kata Laluan", use_container_width=True):
                if new_p == conf_p and new_p != "":
                    st.session_state.db_password = new_p
                    st.session_state.reset_mode = False
                    st.success("✅ Password berjaya diubah!")
                    st.rerun()
            if st.button("Batal"):
                st.session_state.reset_mode = False
                st.rerun()
        else:
            st.title("Sistem Plotter Geomatik PUO")
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            if st.button("🔓 Log Masuk", use_container_width=True):
                if u_id == "admin" and u_pass == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("❌ Salah!")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('reset_mode', True))
        
        st.markdown("<br><p style='text-align: center; color: gray;'>Dibangunkan oleh: <b>Izzaan</b></p>", unsafe_allow_html=True)
    st.stop()

# --- 3. FUNGSI PENUKARAN KOORDINAT (4390 -> WGS84) ---
# Folium memerlukan Lat/Long untuk paparan peta
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak

# --- 4. SIDEBAR ---
st.sidebar.header("📏 Laraskan Saiz Tulisan")
saiz_stn = st.sidebar.slider("Saiz No Stesen", 8, 20, 12)
saiz_data = st.sidebar.slider("Saiz Bearing/Jarak", 8, 20, 10)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 5. PLOTTER UTAMA ---
st.title("📍 Plotter Poligon Google Satellite (Cassini 4390)")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Penyelarasan Koordinat (Cassini Perak)
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        # Convert ke Lat/Long untuk Folium
        coords_wgs = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
        df['lon'] = [c[0] for c in coords_wgs]
        df['lat'] = [c[1] for c in coords_wgs]
        
        # Pusat Peta
        m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, control_scale=True)

        # TAMBAH GOOGLE SATELLITE
        google_sat = folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Satellite',
            overlay=False,
            control=True
        ).add_to(m)

        # Plot Poligon
        poly_points = [[row['lat'], row['lon']] for _, row in df.iterrows()]
        folium.Polygon(locations=poly_points, color="cyan", weight=3, fill=False).add_to(m)

        # Plot Bearing & Jarak (Center)
        for i in range(len(df)):
            p1 = df.iloc[i]
            p2 = df.iloc[(i+1)%len(df)]
            
            # Kira Bearing/Jarak guna koordinat asal (Meter)
            brg, dst = kira_bearing_jarak([p1['E'], p1['N']], [p2['E'], p2['N']])
            
            # Letak di tengah-tengah (Midpoint Lat/Long)
            mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
            
            folium.map.Marker(
                [mid_lat, mid_lon],
                icon=folium.DivIcon(html=f"""<div style="font-family: Arial; color: white; background: rgba(255,0,0,0.7); 
                padding: 2px; border-radius: 3px; font-size: {saiz_data}pt; font-weight: bold; text-align: center; width: 80px;">
                {brg}<br>{dst:.2f}m</div>""")
            ).add_to(m)

        # Plot Bucu (Clickable) & No Stesen (Luar)
        cx, cy = df['lon'].mean(), df['lat'].mean()
        for _, row in df.iterrows():
            # Info bila tekan bucu
            pop_info = f"<b>Stesen:</b> {int(row['STN'])}<br><b>E:</b> {row['E']:.3f}<br><b>N:</b> {row['N']:.3f}"
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=5, color="red", fill=True, fill_color="red",
                popup=folium.Popup(pop_info, max_width=200)
            ).add_to(m)

            # No Stesen (Offset sedikit dari bucu menjauhi pusat)
            off_lat = (row['lat'] - cy) * 0.2
            off_lon = (row['lon'] - cx) * 0.2
            folium.map.Marker(
                [row['lat'] + off_lat, row['lon'] + off_lon],
                icon=folium.DivIcon(html=f"""<div style="font-size: {saiz_stn}pt; color: yellow; font-weight: bold; text-shadow: 2px 2px black;">{int(row['STN'])}</div>""")
            ).add_to(m)

        # Paparkan Peta
        folium_static(m, width=1000, height=600)

        # INFO & EKSPORT
        st.divider()
        c1, c2 = st.columns([2, 1])
        with c1:
            st.dataframe(df[['STN', 'E', 'N']], use_container_width=True)
        with c2:
            st.success(f"**Surveyor:** Izzaan")
            st.info("💡 **Tips:** Klik pada titik merah di peta untuk melihat koordinat tepat setiap bucu.")
            
        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['lon', 'lat']].values.tolist()]}}
        st.sidebar.download_button("🚀 Eksport ke GIS (JSON)", data=json.dumps(geojson), file_name="survey_izzaan.json")
