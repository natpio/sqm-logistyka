import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. KONFIGURACJA I LOGOWANIE
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
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Stylizacja kafelków i notatek
    st.markdown("""
        <style>
        .stMetric { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .cargo-card {
            background-color: white;
            border: 1px solid #e0e0e0;
            border-left: 8px solid #1f77b4;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        .status-red { border-left-color: #ff4b4b !important; background-color: #fff5f5; }
        .status-yellow { border-left-color: #fca903 !important; background-color: #fffdf5; }
        .notatka-display { background-color: #fff3cd; padding: 20px; border-radius: 10px; border-left: 10px solid #ffc107; margin: 15px 0; font-size: 18px; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 2. POBIERANIE DANYCH
    try:
        with st.spinner('Ładowanie bazy SQM...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        # 3. INTERFEJS GÓRNY
        st.title("🏗️ SQM Logistics Control Tower")
        
        # Przełącznik widoku
        view_mode = st.radio("Wybierz widok:", ["📊 Tabela (Edycja)", "📦 Kafelki (Podgląd operacyjny)"], horizontal=True)

        # Metryki
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # 4. LOGIKA WIDOKÓW
        if view_mode == "📊 Tabela (Edycja)":
            tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])
            
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"], width="medium"),
                "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
                "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="medium")
            }

            def process_tab(data_subset, key):
                search = st.text_input("🔍 Szukaj:", key=f"search_{key}")
                if search:
                    data_subset = data_subset[data_subset.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
                
                edited = st.data_editor(data_subset, use_container_width=True, key=f"ed_{key}", column_config=column_cfg)
                
                # Podgląd notatki
                selected = edited[edited["PODGLĄD"] == True]
                if not selected.empty:
                    row = selected.iloc[-1]
                    st.markdown(f'<div class="notatka-display"><b>PROJEKT: {row["Nazwa Projektu"]}</b><br>{row["NOTATKA"]}</div>', unsafe_allow_html=True)
                return edited

            with tab_in:
                df_in = df[~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|EMPTIES", na=False)].copy()
                updated_in = process_tab(df_in, "in")

            with tab_out:
                df_out = df[df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|EMPTIES", na=False)].copy()
                updated_out = process_tab(df_out, "out")

            with tab_full:
                updated_full = process_tab(df.copy(), "full")

        else:
            # WIDOK KAFELKOWY
            st.write("### 🚛 Aktualne transporty (Kafelki)")
            search_tile = st.text_input("🔍 Filtruj kafelki (Hala, Auto, Projekt):")
            
            tile_df = df.copy()
            if search_tile:
                tile_df = tile_df[tile_df.apply(lambda r: r.astype(str).str.contains(search_tile, case=False).any(), axis=1)]

            for _, row in tile_df.iterrows():
                card_class = "cargo-card"
                if "RAMP" in row['STATUS']: card_class += " status-red"
                if "TRASIE" in row['STATUS']: card_class += " status-yellow"

                with st.container():
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="font-size: 20px; font-weight: bold;">{row['Hala']} | Slot: {row['Godzina']}</span>
                            <span style="font-size: 16px;">{row['STATUS']}</span>
                        </div>
                        <div style="margin-top: 10px;">
                            <b>Projekt:</b> {row['Nazwa Projektu']} ({row['Nr Proj.']})<br>
                            <b>Auto/Kierowca:</b> {row['Auto']} / {row['Kierowca']}<br>
                            <b>Przewoźnik:</b> {row['Przewoźnik']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Przyciski akcji pod kafelkiem
                    c1, c2, c3, c4 = st.columns(4)
                    if row['spis casów']: c1.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                    if row['zrzut z currenta']: c2.link_button("🖼️ Current", row['zrzut z currenta'], use_container_width=True)
                    if row['SLOT']: c3.link_button("⏰ SLOT", row['SLOT'], use_container_width=True)
                    if row['NOTATKA'] and row['NOTATKA'] != "":
                        with c4.expander("📝 Notatka"):
                            st.write(row['NOTATKA'])
                st.write("")

        # 5. ZAPIS (Tylko w trybie tabeli)
        if view_mode == "📊 Tabela (Edycja)":
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                # Logika zbierania zmian z edytorów
                for key, source_df in [("ed_in", df_in), ("ed_out", df_out), ("ed_full", df)]:
                    if f"ed_{key}" in st.session_state:
                        edits = st.session_state[f"ed_{key}"].get("edited_rows", {})
                        for r_idx_str, changes in edits.items():
                            real_idx = source_df.index[int(r_idx_str)]
                            for col, val in changes.items():
                                final_df.at[real_idx, col] = val
                
                if "PODGLĄD" in final_df.columns: final_df = final_df.drop(columns=["PODGLĄD"])
                conn.update(spreadsheet=URL, data=final_df)
                st.cache_data.clear()
                st.success("Zsynchronizowano z Google Sheets!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
