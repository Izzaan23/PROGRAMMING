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

# --- 3. LOG MASUK & RESET ---
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
                else:
                    st.error("❌ Salah!")
            
            st.button("❓ Lupa Kata Laluan?", on_click=lambda: st.session_state.__setitem__('reset_mode', True))
        
        st.markdown("<br><p style='text-align: center; color: gray;'>Dibangunkan oleh: <b>Izzaan</b></p>", unsafe_allow_html=True)
    st.stop()

# --- 4. FUNGSI GEOMATIK ---
def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def kira_bearing_jarak(p1, p2):
    de, dn = p2[0] - p1[0], p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    d = int(bearing); m = int((bearing-d)*60); s = round((((bearing-d)*60)-m)*60,0)
    return f"{d}°{m:02d}'{s:02.0f}\"", jarak, bearing

# --- 5. SIDEBAR ---
st.sidebar.header("⚙️ Kawalan Visual")
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)
p_data = st.sidebar.toggle("Papar Bearing & Jarak", value=True)
p_stn = st.sidebar.toggle("Papar Label Stesen", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📏 Laraskan Tulisan")
saiz_font = st.sidebar.slider("Saiz Tulisan Data", 3, 15, 6)
jarak_label = st.sidebar.slider("Jarak Teks (Offset)", 0.5, 10.0, 3.0)
stn_push = st.sidebar.slider("Tolak No Stesen Ke Luar", 1.0, 15.0, 5.0)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. PLOTTER ---
st.title("📍 Plotter Poligon Cassini Perak (4390)")
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

        # Plot Garisan & Label Center
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2, zorder=3)
            
            if p_data:
                brg_str, dst_val, brg_deg = kira_bearing_jarak(p1, p2)
                mid_x, mid_y = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                mag = np.sqrt(dx**2 + dy**2)
                nx, ny = -dy/mag, dx/mag
                if np.dot([nx, ny], [mid_x - cx_m, mid_y - cy_m]) < 0: nx, ny = -nx, -ny

                rot = (90 - brg_deg)
                if rot < -90: rot += 180
                if rot > 90: rot -= 180
                
                ax.text(mid_x + nx*jarak_label, mid_y + ny*jarak_label, brg_str, color='red', 
                        fontsize=saiz_font, fontweight='bold', ha='center', va='center', rotation=rot,
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
                ax.text(mid_x - nx*jarak_label, mid_y - ny*jarak_label, f"{dst_val:.2f}m", color='blue', 
                        fontsize=saiz_font, fontweight='bold', ha='center', va='center', rotation=rot,
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        # --- LOGIK TOLAK NO STESEN KE LUAR ---
        if p_stn:
            ax.scatter(df['E'], df['N'], color='red', s=40, zorder=5)
            for _, row in df.iterrows():
                # Kira arah dari pusat poligon ke titik bucu
                vec_x = row['E'] - cx_m
                vec_y = row['N'] - cy_m
                dist_from_center = np.sqrt(vec_x**2 + vec_y**2)
                
                # Tolak teks mengikut arah vektor tersebut
                off_x = (vec_x / dist_from_center) * stn_push
                off_y = (vec_y / dist_from_center) * stn_push
                
                ax.text(row['E'] + off_x, row['N'] + off_y, str(int(row['STN'])), 
                        color='yellow', fontweight='bold', ha='center', va='center',
                        fontsize=saiz_font+2,
                        bbox=dict(facecolor='black', alpha=0.6, edgecolor='none', pad=1))

        if p_sat:
            try: cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=19)
            except: pass

        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # INFO & EKSPORT
        st.divider()
        c_left, c_right = st.columns([2, 1])
        with c_left:
            stn_sel = st.selectbox("Pilih Stesen untuk Info Koordinat:", df['STN'].unique())
            r = df[df['STN'] == stn_sel].iloc[0]
            st.info(f"📍 Stesen {int(r['STN'])} | E: {r['E']:.3f} | N: {r['N']:.3f}")
        with c_right:
            luas = kira_luas(df['E'].values, df['N'].values)
            st.metric("Luas Poligon", f"{luas:.2f} m²")
            st.write("Surveyor: **Izzaan**")

        geojson = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [df[['E', 'N']].values.tolist()]}}
        st.sidebar.download_button("🚀 Eksport GIS (JSON)", data=json.dumps(geojson), file_name="geomatik_izzaan.json", use_container_width=True)
