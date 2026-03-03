import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as cx
import json
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="PUO Geomatik System", layout="wide")

# --- 2. SISTEM DATABASE KATA LALUAN (Simulasi) ---
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
        
        # MODAL RESET PASSWORD
        if st.session_state.page == "reset":
            st.subheader("🔑 Set Semula Kata Laluan")
            st.info("Sila masukkan kata laluan baru anda di bawah.")
            new_p = st.text_input("Kata Laluan Baru", type="password")
            conf_p = st.text_input("Sahkan Kata Laluan", type="password")
            
            if st.button("Kemaskini Kata Laluan", use_container_width=True):
                if new_p == conf_p and new_p != "":
                    st.session_state.db_password = new_p
                    st.session_state.page = "login"
                    st.success("✅ Berjaya! Sila log masuk dengan kata laluan baru.")
                    st.rerun()
                else:
                    st.error("❌ Kata laluan tidak padan atau kosong.")
            
            if st.button("Kembali ke Log Masuk"):
                st.session_state.page = "login"
                st.rerun()

        # HALAMAN LOG MASUK ASAL
        else:
            st.title("Sistem Plotter Geomatik PUO")
            st.write("Sila masukkan kredential anda untuk mengakses sistem.")
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

# --- 4. MESEJ SAMBUTAN (WELCOME MESSAGE) ---
# Mesej ini muncul hanya selepas log masuk berjaya
st.balloons() # Efek keraian
st.success(f"👋 Selamat Datang ke Sistem Plotter Geomatik, **Izzaan**! Sistem sedia untuk digunakan.")

# --- 5. HALAMAN UTAMA ---
st.title("📍 Plotter Poligon Cassini (EPSG:4390)")
st.info("Sistem ini dilaraskan khas untuk unit meter (Perak).")

# --- 6. SIDEBAR ---
st.sidebar.header("⚙️ Kawalan Visual")
p_sat = st.sidebar.toggle("Papar Imej Satelit", value=True)
p_lbl = st.sidebar.toggle("Papar Bearing/Jarak", value=True)
p_stn = st.sidebar.toggle("Papar Label Stesen", value=True)

st.sidebar.markdown("---")
s_font = st.sidebar.slider("Saiz Tulisan", 4, 12, 7)

if st.sidebar.button("🚪 Log Keluar"):
    st.session_state.logged_in = False
    st.rerun()

# --- 7. PLOTTER ---
uploaded_file = st.file_uploader("📂 Muat naik fail CSV (STN, E, N)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.upper() for c in df.columns]

    if 'E' in df.columns and 'N' in df.columns:
        # Pelarasan Cassini (Simulasi ke PUO)
        t_n, t_e = 6757.654, 115594.785
        if 1 in df['STN'].values:
            idx = df[df['STN'] == 1].index[0]
            df['E'] += (t_e - df.at[idx, 'E'])
            df['N'] += (t_n - df.at[idx, 'N'])

        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plot Poligon & Label
        for i in range(len(df)):
            p1 = [df.iloc[i]['E'], df.iloc[i]['N']]
            p2 = [df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']]
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='cyan', linewidth=2, zorder=3)
            
            if p_lbl:
                # Kira bearing & jarak
                de, dn = p2[0]-p1[0], p2[1]-p1[1]
                dist = np.sqrt(de**2 + dn**2)
                mid = [(p1[0]+p2[0])/2, (p1[1]+p2[1])/2]
                ax.text(mid[0], mid[1], f"{dist:.2f}m", color='red', fontsize=s_font, 
                        fontweight='bold', ha='center', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

        ax.scatter(df['E'], df['N'], color='red', s=30, zorder=5)

        # Tambah Satelit (Esri)
        if p_sat:
            try:
                cx.add_basemap(ax, crs="EPSG:4390", source=cx.providers.Esri.WorldImagery, zoom=19)
            except: pass

        ax.set_aspect('equal')
        ax.axis('off')
        st.pyplot(fig)

        # JADUAL & LUAS
        st.divider()
        st.subheader("📊 Keputusan Analisis")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.dataframe(df, use_container_width=True)
        with c2:
            # Formula Shoelace Luas
            x, y = df['E'].values, df['N'].values
            luas = 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
            st.metric("Luas Keseluruhan", f"{luas:.2f} m²")
            st.write(f"Sistem dibangunkan oleh: **Izzaan**")
