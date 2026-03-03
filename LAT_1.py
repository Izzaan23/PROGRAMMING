# --- LOGIK PANGGIL GOOGLE SATELLITE (VERSI STABIL) ---
        if on_off_satelit:
            try:
                # Tentukan URL berdasarkan pilihan
                if pilihan_peta == "Google Satellite":
                    url_map = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
                elif pilihan_peta == "Google Hybrid":
                    url_map = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                elif pilihan_peta == "Esri World Imagery":
                    url_map = cx.providers.Esri.WorldImagery
                else:
                    url_map = cx.providers.OpenStreetMap.Mapnik

                # Guna zoom manual jika lot terlalu kecil (untuk elakkan "Map data not available")
                # Tahap 18 atau 19 selalunya yang paling rapat Google boleh pergi
                cx.add_basemap(ax, 
                               crs=f"EPSG:{epsg_code}", 
                               source=url_map, 
                               zoom=18,  # Kita kunci pada tahap 18 supaya gambar sentiasa ada
                               zorder=0)
            except Exception as e:
                # Jika tahap 18 gagal, kita biar sistem cuba 'auto'
                try:
                    cx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=url_map, zoom='auto', zorder=0)
                except:
                    st.sidebar.warning("Peta tidak dapat dimuat naik. Sila semak sambungan internet.")
