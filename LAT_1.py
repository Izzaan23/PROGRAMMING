import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik - Izzaan", layout="wide")

# --- 2. SISTEM LOG MASUK & RESET (Gaya Website) ---
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
        if os.path.exists("logo l.png"): st.image("logo l.png", width=120)
        
        if st.session_state.reset_mode:
            st.subheader("🔑 Set Semula Kata Laluan")
            new_p = st.text_input("Kata Laluan Baru", type="password")
            conf_p = st.text_input("Sahkan Kata Laluan", type="password")
            if st.button("Kemaskini Kata Laluan", use_container_width=True):
                if new_p == conf_p and new_p != "":
                    st.session_state.db_password = new_p
                    st.session_state.reset_mode = False
                    st.success("✅ Berjaya! Sila log masuk.")
                    st.rerun()
            st.button("Batal", on_click=lambda: st.session_state.__setitem__('reset_mode', False))
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

# --- 4. SIDEBAR ---
st.sidebar.header("🏷️ Tetapan Label")
p_stn = st.sidebar.checkbox("Papar Label Stesen (STN)", value=True)
s_stn = st.sidebar.slider("Saiz Tulisan Stesen", 3, 15, 6)
p_data = st.sidebar.checkbox("Papar Bearing & Jarak", value=True)
s_data = st.sidebar.slider("Saiz Tulisan Bearing/Jarak", 3, 15, 5)
p_luas = st.sidebar.checkbox("Papar Label Luas", value=True)
s_luas = st.sidebar.slider("Saiz Tulisan Luas", 5, 20, 7)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 5. PEMPROSESAN DATA ---
st.title("📍 Plotter Poligon Cassini (EPSG:4390)")
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Pelarasan Cassini Perak
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        fig, ax = plt.subplots(figsize=(10, 8))
        cx_m, cy_m = df['E'].mean(), df['N'].mean()

        # Plot Garisan Traverse
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2, zorder=3)
            
            if p_data:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                rot = (90 - brg_deg)
                if rot < -90: rot += 180
                if rot > 90: rot -= 180
                ax.text(mid_x, mid_y, f"{brg_str}\n{dst_val:.2f}m", color='red', fontsize=s_data, 
                        fontweight='bold', ha='center', va='center', rotation=rot, zorder=5,
                        bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=1))

        # Plot Bucu & No Stesen (Di Luar Poligon)
        ax.scatter(df['E'], df['N'], color='red', s=25, edgecolors='white', zorder=10)
        if p_stn:
            for _, row in df.iterrows():
                vx, vy = row['E'] - cx_m, row['N'] - cy_m
                dist = np.sqrt(vx**2 + vy**2)
                # Tolak label 3 meter ke luar dari pusat
                ax.text(row['E'] + (vx/dist)*3, row['N'] + (vy/dist)*3, str(row['STN']), 
                        color='yellow', fontsize=s_stn, fontweight='bold', ha='center', va='center',
                        bbox=dict(facecolor='black', alpha=0.7, edgecolor='none', pad=0.5))

        # Label Luas di Tengah (Gaya Gambar Anda)
        if p_luas:
            luas_val = kira_luas(df['E'].values, df['N'].values)
            ax.text(cx_m, cy_m, f"LUAS\n{luas_val:.2f} m²", color='green', fontsize=s_luas, 
                    fontweight='bold', ha='center', va='center', zorder=6,
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='green'))

        # TAMBAH GOOGLE SATELLITE & AUTO ZOOM
        try:
            google_url = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
            cx.add_basemap(ax, crs="EPSG:4390", source=google_url, zoom=19)
        except: pass

        # AUTO-ZOOM (Fit to Polygon dengan 10m padding)
        ax.set_xlim(df['E'].min() - 15, df['E'].max() + 15)
        ax.set_ylim(df['N'].min() - 15, df['N'].max() + 15)
        ax.axis('off')
        
        st.pyplot(fig)

        # --- INFO INTERAKTIF DI BAWAH ---
        st.divider()
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**🔍 Info Bucu Traverse:**")
            stn_sel = st.selectbox("Pilih Stesen untuk lihat Koordinat:", df['STN'].unique())
            r_data = df[df['STN'] == stn_sel].iloc[0]
            st.info(f"📍 **Stesen {int(r_data['STN'])}** | **East:** {r_data['E']:.3f} | **North:** {r_data['N']:.3f}")
        with col2:
            st.write(f"Surveyor: **Izzaan**")
            geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist()]}}
            st.download_button("🚀 Eksport GIS (JSON)", data=json.dumps(geojson), file_name="izzaan_plot.json")
