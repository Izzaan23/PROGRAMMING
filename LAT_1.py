import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik - Izzaan", layout="wide")

# --- 2. SISTEM DATABASE KATA LALUAN ---
if "db_password" not in st.session_state:
    st.session_state.db_password = "admin123"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "reset_mode" not in st.session_state:
    st.session_state.reset_mode = False

# --- 3. ANTARAMUKA LOG MASUK & RESET PASSWORD ---
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
                    st.success("✅ Berjaya! Sila log masuk.")
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
                    st.balloons() # Sambutan kedatangan
                    st.rerun()
                else: st.error("ID atau Kata Laluan salah.")
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('reset_mode', True))
        
        st.markdown("<br><p style='text-align: center; color: gray;'>Dibangunkan oleh: <b>Izzaan</b></p>", unsafe_allow_html=True)
    st.stop()

# --- 4. MESEJ SAMBUTAN ---
st.success(f"👋 Selamat Datang kembali, **Izzaan**! Sistem Plotter Cassini Perak sedia digunakan.")

# --- 5. FUNGSI MATEMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak, bearing

# --- 6. SIDEBAR (KAWALAN VISUAL & EKSPORT) ---
st.sidebar.header("⚙️ Tetapan Paparan")
papar_satelit = st.sidebar.toggle("Papar Imej Satelit", value=True)
papar_data = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
papar_stn = st.sidebar.toggle("Papar Label Stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📏 Laraskan Tulisan")
saiz_font = st.sidebar.slider("Saiz Tulisan Data", 3, 15, 7)
jarak_label = st.sidebar.slider("Jarak Teks dari Garisan", 0.5, 10.0, 3.0)
stn_size = st.sidebar.slider("Saiz No Stesen", 5, 20, 10)

st.sidebar.markdown("---")
st.sidebar.header("📤 Eksport Data")
# Butang eksport akan diaktifkan jika fail dimuat naik

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 7. PEMPROSESAN FAIL & PLOT ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Pelarasan Cassini (EPSG:4390)
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        fig, ax = plt.subplots(figsize=(10, 8))
        cx_m, cy_m = df['E'].mean(), df['N'].mean()

        # Plot Garisan & Data (Bearing/Jarak)
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2, zorder=3)
            
            if papar_data:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                
                # Kira Vektor Normal untuk kedudukan tetap (Center & Offset)
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                mag = np.sqrt(dx**2 + dy**2)
                nx, ny = -dy/mag, dx/mag
                if np.dot([nx, ny], [mid_x - cx_m, mid_y - cy_m]) < 0: nx, ny = -nx, -ny

                txt_rot = 90 - brg_deg
                if txt_rot < -90: txt_rot += 180
                if txt_rot > 90: txt_rot -= 180
                
                # Paparan Bearing (Luar) & Jarak (Dalam)
                ax.text(mid_x + nx*jarak_label, mid_y + ny*jarak_label, brg_str, 
                        color='red', fontsize=saiz_font, fontweight='bold', ha='center', va='center', 
                        rotation=txt_rot, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
                ax.text(mid_x - nx*jarak_label, mid_y - ny*jarak_label, f"{dst_val:.2f}m", 
                        color='blue', fontsize=saiz_font, fontweight='bold', ha='center', va='center', 
                        rotation=txt_rot, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        # Label Stesen
        if papar_stn:
            for _, row in df.iterrows():
                ax.scatter(row['E'], row['N'], color='red', s=40, zorder=5)
                ax.text(row['E'], row['N'] + 1.5, str(int(row['STN'])), color='yellow', 
                        fontsize=stn_size, fontweight='bold', ha='center',
                        bbox=dict(facecolor='black', alpha=0.5, edgecolor='none'))

        # Satelit
        if papar_satelit:
            try: cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=19)
            except: pass

        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # --- JADUAL & EKSPORT ---
        st.divider()
        st.subheader("📋 Maklumat Poligon")
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.dataframe(df, use_container_width=True)
        with col_b:
            luas = kira_luas(df['E'].values, df['N'].values)
            st.metric("Luas (m²)", f"{luas:.2f}")
            st.write("Sistem oleh: **Izzaan**")

        # Butang Eksport GIS (Aktif di Sidebar)
        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist()]}}
        st.sidebar.download_button("🚀 Eksport ke GIS (JSON)", data=json.dumps(geojson), file_name="geomatik_izzaan.json", use_container_width=True)
