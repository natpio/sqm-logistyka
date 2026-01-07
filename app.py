import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

controller = CookieController()

# 1. LOGOWANIE (bez zmian)
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
        st.title("🔒 SQM Logistics")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM TABLET MODE", layout="wide")

    # CSS OPTYMALIZOWANY POD TABLET (Większe odstępy, duże przyciski)
    st.markdown("""
        <style>
        .stButton button { width: 100%; height: 60px; font-size: 20px !important; margin-bottom: 10px; }
        div[data-testid="stMetric"] { padding: 10px; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; font-weight: bold; }
        /* Większe wiersze w tabeli dla palca */
        [data-testid="stDataFrame"] td { padding: 15px !important; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Konfiguracja kolumn - zmieniamy LinkColumn na TextColumn w edytorze, 
    # a linki obsłużymy przyciskami pod spodem.
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options),
        "spis casów": st.column_config.TextColumn("📋 Spis (Link)"),
        "zdjęcie po załadunku": st.column_config.TextColumn("📸 Foto (Link)"),
        "SLOT": st.column_config.TextColumn("⏰ SLOT (Link)"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="medium")
    }

    try:
        raw_df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        # --- PANEL AKCJI NA GÓRZE (PRZYCISKI DLA iPada) ---
        col_save, col_ref = st.columns(2)
        with col_save:
            btn_save = st.button("💾 ZAPISZ ZMIANY")
        with col_ref:
            if st.button("🔄 ODŚWIEŻ DANE"):
                st.cache_data.clear()
                st.rerun()

        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 PEŁNA BAZA"])

        # --- FUNKCJA DO OBSŁUGI LINKÓW ---
        def link_preview_section(selected_rows, source_df):
            if len(selected_rows) > 0:
                idx = selected_rows[0]
                row_data = source_df.iloc[idx]
                st.markdown("---")
                st.subheader(f"📂 Dokumentacja: {row_data['Nazwa Projektu']}")
                c1, c2, c3 = st.columns(3)
                
                # Duże przyciski, które iPad otwiera bez problemu
                with c1:
                    if row_data['spis casów'] and "http" in row_data['spis casów']:
                        st.link_button("📋 OTWÓRZ SPIS CASE'ÓW", row_data['spis casów'])
                with c2:
                    if row_data['zdjęcie po załadunku'] and "http" in row_data['zdjęcie po załadunku']:
                        st.link_button("📸 OTWÓRZ ZDJĘCIA", row_data['zdjęcie po załadunku'])
                with c3:
                    if row_data['SLOT'] and "http" in row_data['SLOT']:
                        st.link_button("⏰ OTWÓRZ SLOT", row_data['SLOT'])

        # --- MONTAŻE ---
        with tab_in:
            search_in = st.text_input("🔍 Szukaj ładunku:", key="s_in")
            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]
            
            # Dodajemy parametr on_change lub selection_mode
            event_in = st.dataframe(df_in, use_container_width=True, column_config=column_cfg, on_select="rerun", selection_mode="single_row")
            link_preview_section(event_in.selection.rows, df_in)
            updated_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg)

        # --- DEMONTAŻE ---
        with tab_out:
            search_out = st.text_input("🔍 Szukaj wywozu:", key="s_out")
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]
            
            event_out = st.dataframe(df_out, use_container_width=True, column_config=column_cfg, on_select="rerun", selection_mode="single_row")
            link_preview_section(event_out.selection.rows, df_out)
            updated_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg)

        # --- TAB 4: PEŁNA BAZA ---
        with tab_full:
            updated_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg)

        # --- ZAPIS (Pancerny) ---
        if btn_save:
            final_df = df.copy()
            # Łączymy zmiany z edytorów (jeśli były edytowane)
            # Uwaga: data_editor zwraca tylko zmiany, więc łączymy ostrożnie
            for upd, original in [(updated_in, df_in), (updated_out, df_out), (updated_full, df)]:
                for index, row in upd.iterrows():
                    final_df.loc[index] = row
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("ZAPISANO!")
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
