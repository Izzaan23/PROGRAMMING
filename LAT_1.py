import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from folium.plugins import Fullscreen  
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

# --- 3. ANTARAMUKA LOG MASUK ---
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
            if st.button("Kembali"):
                st.session_state.page = "login"
                st.rerun()
        else:
            st.title("Sistem Plotter Geomatik PUO")
            u_id = st.text_input("ID Pengguna")
            u_pass = st.text_input("Kata Laluan", type="password")
            if st.button("🔓 Log Masuk", use_container_width=True):
                # ID Pengguna ditukar kepada "11"
                if u_id == "11" and u_pass == st.session_state.db_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('page', 'reset'))
        st.markdown("---")
        st.caption("Pembangun Sistem: Izzaan")
    st.stop()

# --- 4. FUNGSI GEOMATIK ---
transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)

def kira_brg_dst(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    dist = np.sqrt(de**2 + dn**2)
    brg = np.degrees(np.arctan2(de, dn))
    if brg < 0: brg += 360
    d = int(brg); m = int((brg-d)*60); s = round((((brg-d)*60)-m)*60,0)
    
    flipped = False
    angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
    if angle > 90: 
        angle -= 180
        flipped = True
    elif angle < -90: 
        angle += 180
        flipped = True
    
    return f"{d}°{m:02d}'{s:02.0f}\"", dist, angle, flipped

def kira_luas(df):
    x = df['E'].values
    y = df['N'].values
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- 5. SIDEBAR & MENU ---
st.sidebar.title("📁 Menu Utama")
pilihan_menu = st.sidebar.selectbox("Pilih Halaman:", ["🏠 Dashboard", "📍 Plotter Interaktif"])

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Tetapan (Global)")

# Tetapan dikumpulkan dalam sidebar tapi hanya aktif mengikut logik
if "p_sat" not in st.session_state: st.session_state.p_sat = True
if "p_lbl" not in st.session_state: st.session_state.p_lbl = True
if "p_stn" not in st.session_state: st.session_state.p_stn = True
if "s_font" not in st.session_state: st.session_state.s_font = 11

if pilihan_menu == "🏠 Dashboard":
    st.title("🏠 Dashboard Tetapan")
    st.markdown("Sila tetapkan visualisasi peta dan label di sini sebelum memulakan plotting.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🗺️ Tetapan Peta")
        st.session_state.p_sat = st.toggle("Papar Imej Satelit (Google)", value=st.session_state.p_sat)
        st.session_state.p_stn = st.toggle("Papar Label No. Stesen", value=st.session_state.p_stn)
        
    with col2:
        st.subheader("🏷️ Tetapan Label")
        st.session_state.p_lbl = st.toggle("Papar Bearing & Jarak", value=st.session_state.p_lbl)
        st.session_state.s_font = st.slider("Saiz Tulisan Label", 8, 20, st.session_state.s_font)

    st.info("💡 Semua tetapan di atas akan diaplikasikan secara automatik di halaman Plotter.")

else:
    # --- 6. PLOTTER INTERAKTIF ---
    st.title("📍 Plotter Interaktif Izzaan")
    
    # Ambil nilai dari session state (Dashboard)
    p_sat = st.session_state.p_sat
    p_lbl = st.session_state.p_lbl
    p_stn = st.session_state.p_stn
    s_font = st.session_state.s_font

    uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.upper().strip() for c in df.columns]

        if 'E' in df.columns and 'N' in df.columns:
            coords = [transformer.transform(e, n) for e, n in zip(df['E'], df['N'])]
            df['lon'], df['lat'] = [c[0] for c in coords], [c[1] for c in coords]
            
            m = folium.Map(
                location=[df['lat'].mean(), df['lon'].mean()], 
                zoom_start=19, max_zoom=22, control_scale=True
            )
            
            Fullscreen(position="topleft", title="Skrin Penuh", title_cancel="Keluar").add_to(m)

            if p_sat:
                google_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
                folium.TileLayer(tiles=google_url, attr='Google', name='Google Satellite', max_zoom=22, max_native_zoom=20).add_to(m)

            luas = kira_luas(df)
            info_lot = f"""<div style='width:150px'><b>Info Lot:</b><br>Luas: {luas:.2f} m²<br>Luas: {(luas/4046.86):.3f} Ekar</div>"""
            
            poly_pts = [[r['lat'], r['lon']] for _, r in df.iterrows()]
            folium.Polygon(
                locations=poly_pts, color="cyan", weight=3, fill=True, fill_opacity=0.2,
                popup=folium.Popup(info_lot, max_width=200)
            ).add_to(m)

            for i in range(len(df)):
                p1 = df.iloc[i]
                p2 = df.iloc[(i+1)%len(df)]
                
                if p_stn:
                    folium.map.Marker(
                        [p1['lat'], p1['lon']],
                        icon=folium.DivIcon(html=f"<div style='font-family: Arial; color: yellow; font-weight: bold; font-size: {s_font}pt; text-shadow: 2px 2px 3px black; width: 40px;'>{int(p1['STN'])}</div>")
                    ).add_to(m)
                    folium.CircleMarker([p1['lat'], p1['lon']], radius=5, color='red', fill=True, fill_color='red').add_to(m)

                if p_lbl:
                    brg_txt, dst_val, angle, flipped = kira_brg_dst([p1['E'], p1['N']], [p2['E'], p2['N']])
                    mid_lat, mid_lon = (p1['lat'] + p2['lat'])/2, (p1['lon'] + p2['lon'])/2
                    flex_direction = "column-reverse" if flipped else "column"
                    
                    folium.map.Marker(
                        [mid_lat, mid_lon],
                        icon=folium.DivIcon(html=f"""
                            <div style="transform: rotate({-angle}deg); display: flex; flex-direction: {flex_direction}; align-items: center; justify-content: center; width: 120px; margin-left: -60px; pointer-events: none;">
                                <div style="font-size: {s_font-2}pt; color: white; font-weight: bold; text-shadow: 1px 1px 2px black; padding-bottom: 2px;">{brg_txt}</div>
                                <div style="font-size: {s_font-3}pt; color: #00FF00; font-weight: bold; text-shadow: 1px 1px 2px black; padding-top: 2px;">{dst_val:.2f}m</div>
                            </div>""")
                    ).add_to(m)

            m.fit_bounds(poly_pts)
            folium_static(m, width=1100, height=600)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

st.markdown("---")
st.caption("Pembangun Sistem: Izzaan | Geomatics PUO | Menu Navigation Mode")
