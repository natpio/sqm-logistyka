def render_tile_view(data):
    """Widok pogrupowany po AUCIE i DACIE dla zachowania spójności transportu"""
    if data.empty:
        st.info("Brak transportów do wyświetlenia.")
        return

    # Grupowanie danych po Dacie i Aucie, aby utrzymać transporty razem
    # Sortujemy, aby najnowsze/najbliższe były na górze
    grouped = data.sort_values(['Data', 'Godzina']).groupby(['Data', 'Auto'])

    for (date_val, auto_nr), group in grouped:
        # Pobieramy dane wspólne dla transportu z pierwszego wiersza grupy
        przewoznik = group.iloc[0]['Przewoźnik']
        kierowca = group.iloc[0]['Kierowca']
        godzina = group.iloc[0]['Godzina']
        
        # Tworzymy duży kafelek transportu (Zestawu)
        with st.container(border=True):
            # Nagłówek Transportu
            h1, h2, h3 = st.columns([1.5, 2, 1])
            with h1:
                st.markdown(f"📅 **{date_val}**")
                st.markdown(f"<h2 style='margin:0; color:#1f77b4;'>🚚 {auto_nr}</h2>", unsafe_allow_html=True)
            with h2:
                st.markdown(f"**GODZINA:** ⏰ {godzina}")
                st.markdown(f"**FIRMA:** {przewoznik}")
                st.markdown(f"**KIEROWCA:** 👤 {kierowca}")
            with h3:
                # Wyświetlamy statusy projektów w pigułce
                distinct_stats = group['STATUS'].unique()
                for s in distinct_stats:
                    st_col = "#d73a49" if "RAMP" in s.upper() else "#f9c000" if "TRASIE" in s.upper() else "#28a745" if "ROZŁADOWANY" in s.upper() else "#6c757d"
                    st.markdown(f'<div style="background:{st_col}; color:white; padding:2px 10px; border-radius:10px; font-size:12px; margin-bottom:2px; text-align:center;">{s}</div>', unsafe_allow_html=True)

            st.markdown("---")
            
            # Lista projektów (ładunków) wewnątrz tego transportu
            st.markdown("**📦 ZAWARTOŚĆ TRANSPORTU:**")
            
            # Wyświetlamy projekty wewnątrz jednego transportu w kolumnach lub rzędach
            for _, row in group.iterrows():
                p_col1, p_col2 = st.columns([3, 1])
                with p_col1:
                    st.markdown(f"**{row['Nr Proj.']}** — {row['Nazwa Projektu']} (📍 Hala: {row['Hala']})")
                with p_col2:
                    # Szybkie linki do dokumentacji
                    l1, l2, l3 = st.columns(3)
                    if "http" in str(row['spis casów']): l1.link_button("📋", row['spis casów'], help="Spis casów")
                    if "http" in str(row['zdjęcie po załadunku']): l2.link_button("📸", row['zdjęcie po załadunku'], help="Foto załadunku")
                    if row['NOTATKA']:
                        with l3.expander("📝"): st.info(row['NOTATKA'])
                st.markdown("<div style='border-bottom: 1px dashed #eee; margin: 5px 0;'></div>", unsafe_allow_html=True)

# Podmiana w głównym kodzie w miejscu:
# else:
#     render_tile_view(current_df)
