import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
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
        st.title("🏗️ SQM Control Tower")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - High Visibility dla iPada
    st.markdown("""
        <style>
        .stButton button { height: 75px !important; border-radius: 12px !important; font-weight: bold !important; font-size: 18px !important; }
        .op-card-border { border: 2px solid #e1e4e8; border-radius: 15px; padding: 20px; margin-bottom: 20px; background-color: white; }
        .status-box { padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; color: white; min-width: 120px; }
        .blink { color: #d73a49; animation: blink 2s infinite; font-weight: bold; }
        @keyframes blink { 50% { opacity: 0.3; } }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Synchronizacja danych SQM...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        # Uzupełnienie kolumn
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Logistics Control Tower")
        
        # GŁÓWNY PRZEŁĄCZNIK WIDOKU
        view_mode = st.radio("WYBIERZ TRYB PRACY:", ["🚀 WIDOK OPERACYJNY (Karty)", "📊 EDYCJA BAZY (Tabela)"], horizontal=True)
        st.divider()

        if view_mode == "🚀 WIDOK OPERACYJNY (Karty)":
            # Filtry szybkiego dostępu
            c_f1, c_f2 = st.columns([2, 1])
            search = c_f1.text_input("🔍 Szukaj projektu/auta:", placeholder="Wpisz nazwę...")
            active_hala = c_f2.selectbox("Filtruj halę:", ["Wszystkie"] + sorted([h for h in df['Hala'].unique() if h]))

            display_df = df.copy()
            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            if active_hala != "Wszystkie":
                display_df = display_df[display_df['Hala'] == active_hala]
            
            display_df = display_df.sort_values(by="Godzina")

            for idx, row in display_df.iterrows():
                # Kolor statusu
                stat = row['STATUS'].upper()
                s_color = "#d73a49" if "RAMP" in stat else "#f9c000" if "TRASIE" in stat else "#28a745" if "ROZŁADOWANY" in stat else "#6a737d"
                
                with st.container():
                    st.markdown(f"""
                    <div class="op-card-border">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <span style="font-size: 14px; color: #6a737d;">SLOT: {row['Godzina']} | HALA: {row['Hala']}</span>
                                <h1 style="margin: 0; padding: 0; font-size: 28px;">{row['Nazwa Projektu']}</h1>
                                <span style="font-size: 16px;">PROJEKT: {row['Nr Proj.']} | AUTO: <b>{row['Auto']}</b></span>
                            </div>
                            <div class="status-box" style="background-color: {s_color};">
                                {row['STATUS']}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # DUŻE PRZYCISKI AKCJI
                    b1, b2, b3, b4 = st.columns(4)
                    
                    def link_btn(col, label, emoji, link, key_id):
                        if "http" in str(link):
                            col.link_button(f"{emoji} {label}", link, use_container_width=True)
                        else:
                            col.button(f"❌ {label}", disabled=True, key=key_id, use_container_width=True)

                    link_btn(b1, "FOTO ZAŁADUNEK", "📸", row['zdjęcie po załadunku'], f"bt_f_{idx}")
                    link_btn(b2, "SPIS TOWARU", "📋", row['spis casów'], f"bt_s_{idx}")
                    link_btn(b3, "CURRENT", "🖼️", row['zrzut z currenta'], f"bt_c_{idx}")
                    
                    with b4:
                        if row['NOTATKA'].strip():
                            with st.expander("📝 NOTATKA"):
                                st.info(row['NOTATKA'])
                        else:
                            st.button("BRAK NOTATKI", disabled=True, key=f"bt_n_{idx}", use_container_width=True)
                    st.write("##") # Odstęp

        else:
            # PRZYWRÓCONY WIDOK TABELI (EDYCJA)
            st.info("Zmień dane w tabeli i kliknij ZAPISZ na dole strony.")
            
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current"),
                "SLOT": st.column_config.LinkColumn("⏰ SLOT"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
            }
            
            # Podział na zakładki wewnątrz edycji
            tab1, tab2 = st.tabs(["🚛 Aktywne Transporty", "📚 Pełna Baza"])
            
            with tab1:
                df_active = df[~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|EMPTIES", na=False)].copy()
                ed_active = st.data_editor(df_active, use_container_width=True, column_config=column_cfg, key="editor_active")
            
            with tab2:
                ed_full = st.data_editor(df, use_container_width=True, column_config=column_cfg, key="editor_full")

            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                # Scalanie zmian z edytorów
                final_df = df.copy()
                for ed_key, source_df in [("editor_active", df_active), ("editor_full", df)]:
                    if ed_key in st.session_state:
                        edits = st.session_state[ed_key].get("edited_rows", {})
                        for r_idx_str, changes in edits.items():
                            real_idx = source_df.index[int(r_idx_str)]
                            for col, val in changes.items():
                                final_df.at[real_idx, col] = val
                
                conn.update(spreadsheet=URL, data=final_df)
                st.cache_data.clear()
                st.success("Dane zapisane w Google Sheets!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
