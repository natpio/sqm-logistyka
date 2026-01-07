import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. LOGOWANIE I PAMIĘĆ (COOKIES)
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
        st.title("🔒 SQM Logistics - Logowanie")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Wymuszenie widoczności paska przewijania i usunięcie ograniczeń szerokości
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        
        /* Ustawienie minimalnej szerokości dla kontenera tabeli */
        [data-testid="stDataFrame"] {
            min-width: 1200px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # KONFIGURACJA KOLUMN - NOTATKA NA 800 PIKSELI
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "Data": st.column_config.TextColumn("Data", width="small"),
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options, width="medium"),
        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz", width="small"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz", width="small"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz", width="small"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width=800) # Bardzo szeroka kolumna
    }

    try:
        raw_df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        st.title("🏗️ SQM Logistics Control Tower")
        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])

        with tab_in:
            search_in = st.text_input("🔍 Szukaj ładunku:", key="s_in")
            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()
            
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            # KLUCZOWA ZMIANA: use_container_width=False
            updated_in = st.data_editor(df_in, use_container_width=False, key="ed_in", column_config=column_cfg)

        with tab_out:
            search_out = st.text_input("🔍 Szukaj wywozu:", key="s_out")
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]
            
            updated_out = st.data_editor(df_out, use_container_width=False, key="ed_out", column_config=column_cfg)

        with tab_full:
            updated_full = st.data_editor(df, use_container_width=False, key="ed_full", column_config=column_cfg)

        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            final_df = df.copy()
            for key, source_df in [("ed_in", df_in), ("ed_out", df_out), ("ed_full", df)]:
                if key in st.session_state:
                    edytowane = st.session_state[key].get("edited_rows", {})
                    for row_idx_str, changes in edytowane.items():
                        real_idx = source_df.index[int(row_idx_str)]
                        for col, val in changes.items():
                            final_df.at[real_idx, col] = val
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("Zapisano!")
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

if st.sidebar.button("Wyloguj"):
    controller.remove("sqm_login_key")
    st.rerun()
