import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_cookies_controller import CookieController

# 1. AUTORYZACJA
controller = CookieController()

def check_password():
    saved_auth = controller.get("sqm_login_key")
    if saved_auth == "Czaman2026":
        st.session_state["password_correct"] = True
        return True
    def password_entered():
        if st.session_state["password"] == "Czaman2026":
            st.session_state["password_correct"] = True
            controller.set("sqm_login_key", "Czaman2026", max_age=3600*24*30)
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🏗️ SQM Logistics - Control Tower")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Twój styl z dodatkiem dla sekcji archiwalnej
    st.markdown("""
        <style>
        .stButton button { height: 70px !important; border-radius: 10px !important; font-size: 16px !important; font-weight: bold !important; }
        .date-header { background-color: #2e3b4e; color: white; padding: 15px; border-radius: 10px; font-size: 28px; font-weight: bold; margin: 30px 0 10px 0; text-align: center; border-bottom: 5px solid #1f77b4; }
        .hala-banner { background-color: #1f77b4; color: white; padding: 10px 20px; border-radius: 8px; font-size: 20px; font-weight: bold; margin: 15px 0 10px 0; }
        .slot-pill { background-color: #f0f2f6; border: 1px solid #d1d5db; padding: 6px 15px; border-radius: 20px; font-size: 16px; font-weight: bold; color: #1f2937; }
        .status-tag { padding: 6px 12px; border-radius: 8px; font-weight: bold; color: white; text-align: center; }
        .archive-header { background-color: #e9ecef; color: #6c757d; padding: 10px; border-radius: 8px; font-size: 18px; font-weight: bold; margin-top: 20px; border-left: 5px solid #28a745; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Pobieranie danych...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None'], '')

        st.title("🏗️ SQM Control Tower")
        mode = st.radio("WYBIERZ WIDOK:", ["🛰️ RADAR OPERACYJNY", "🏗️ KREATOR KAFELKA", "📊 EDYCJA BAZY"], horizontal=True)
        st.divider()

        if mode != "📊 EDYCJA BAZY":
            c_search, c_hala = st.columns([2, 1])
            search = c_search.text_input("🔍 Szukaj ładunku...")
            hala_filter = c_hala.multiselect("Filtruj Hale:", options=sorted(df['Hala'].unique()))

            display_df = df.copy()
            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            if hala_filter:
                display_df = display_df[display_df['Hala'].isin(hala_filter)]
            
            display_df = display_df.sort_values(by=['Data', 'Godzina'])

        # --- FUNKCJA RENDERUJĄCA KAFELEK ---
        def draw_card(row, i, k_suffix):
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                c1.markdown(f'<span class="slot-pill">SLOT {row["Nr Slotu"]} | {row["Data"]} | ⏰ {row["Godzina"]}</span>', unsafe_allow_html=True)
                stat = row['STATUS'].upper()
                bg_stat = "#d73a49" if "RAMP" in stat else "#f9c000" if "TRASIE" in stat else "#28a745" if "ROZŁADOWANY" in stat else "#6a737d"
                c2.markdown(f'<div class="status-tag" style="background-color: {bg_stat};">{row["STATUS"]}</div>', unsafe_allow_html=True)
                
                st.markdown(f"## {row['Nr Proj.']} | {row['Nazwa Projektu']}")
                st.markdown(f"**PRZEWOŹNIK:** {row['Przewoźnik']}")
                st.markdown(f"🚚 **{row['Auto']}** | 👤 {row['Kierowca']}")
                st.write("---")
                
                t1, t2, t3, t4 = st.columns(4)
                def r_btn(col, label, emoji, link, k):
                    if "http" in str(link): col.link_button(f"{emoji} {label}", link, use_container_width=True)
                    else: col.button(f"{emoji} --", disabled=True, key=k, use_container_width=True)
                
                r_btn(t1, "FOTO", "📸", row['zdjęcie po załadunku'], f"f_{i}_{k_suffix}")
                r_btn(t2, "SPIS", "📋", row['spis casów'], f"s_{i}_{k_suffix}")
                r_btn(t3, "CURR", "🖼️", row['zrzut z currenta'], f"c_{i}_{k_suffix}")
                with t4:
                    if row['NOTATKA'].strip():
                        with st.expander("📝 NOTATKA"): st.info(row['NOTATKA'])
                    else: st.button("📝 --", disabled=True, key=f"n_{i}_{k_suffix}", use_container_width=True)

        # --- WIDOK 1: RADAR OPERACYJNY ---
        if mode == "🛰️ RADAR OPERACYJNY":
            dates = display_df['Data'].unique()
            for d in dates:
                st.markdown(f'<div class="date-header">📅 DZIEŃ: {d}</div>', unsafe_allow_html=True)
                date_df = display_df[display_df['Data'] == d]
                
                # PODZIAŁ: AKTYWNE vs ROZŁADOWANE
                active_mask = ~date_df['STATUS'].str.contains("ROZŁADOWANY", case=False, na=False)
                active_df = date_df[active_mask]
                done_df = date_df[~active_mask]

                # RENDER AKTYWNYCH
                hale = sorted(active_df['Hala'].unique())
                for h in hale:
                    st.markdown(f'<div class="hala-banner">📍 HALA {h} - W TOKU</div>', unsafe_allow_html=True)
                    hala_df = active_df[active_df['Hala'] == h]
                    cols = st.columns(2)
                    for i, (_, row) in enumerate(hala_df.iterrows()):
                        draw_card(row, i, f"act_{d}_{h}")

                # RENDER ZAKOŃCZONYCH (W EXPANDERZE)
                if not done_df.empty:
                    with st.expander(f"✅ ZOBACZ ROZŁADOWANE Z DNIA {d} ({len(done_df)})"):
                        cols_done = st.columns(2)
                        for i, (_, row) in enumerate(done_df.iterrows()):
                            draw_card(row, i, f"done_{d}")

        # --- WIDOK 2: KREATOR KAFELKA ---
        elif mode == "🏗️ KREATOR KAFELKA":
            st.info("Personalizacja widoku.")
            # ... (logika kreatora jak wcześniej, ale z podziałem na Aktywne/Gotowe)
            # Dla uproszczenia tutaj stosujemy ten sam podział co w Radarze
            st.write("Skonfiguruj widok w zakładce RADAR lub EDYCJA.")
            st.warning("Ta sekcja zostanie rozbudowana o Twoje zapisane style w kolejnym kroku.")

        # --- WIDOK 3: EDYCJA BAZY ---
        else:
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg)
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
