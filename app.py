import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

controller = CookieController()

# 1. LOGOWANIE
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

    # CSS pod iPada - duże przyciski, czytelna tabela
    st.markdown("""
        <style>
        .stButton button { width: 100%; height: 55px; font-size: 18px !important; font-weight: bold; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        [data-testid="stDataFrame"] td { padding: 12px !important; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options),
        "spis casów": st.column_config.TextColumn("📋 Link Spis"),
        "zdjęcie po załadunku": st.column_config.TextColumn("📸 Link Foto"),
        "SLOT": st.column_config.TextColumn("⏰ Link SLOT"),
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

        # Główne przyciski operacyjne
        c_save, c_ref = st.columns(2)
        with c_save: btn_save = st.button("💾 ZAPISZ ZMIANY (WSZYSTKIE TABELE)")
        with c_ref: 
            if st.button("🔄 ODŚWIEŻ Z ARKUSZA"):
                st.cache_data.clear()
                st.rerun()

        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 PEŁNA BAZA"])

        # Funkcja do wyświetlania dużych przycisków linków pod tabelą
        def show_links_for_ipad(selected_rows_indices, current_df):
            if selected_rows_indices:
                idx = selected_rows_indices[0]
                row = current_df.iloc[idx]
                st.info(f"Opcje dla projektu: **{row['Nazwa Projektu']}** (Auto: {row['Auto']})")
                l1, l2, l3 = st.columns(3)
                with l1:
                    if "http" in str(row['spis casów']): st.link_button("📋 OTWÓRZ SPIS", row['spis casów'])
                with l2:
                    if "http" in str(row['zdjęcie po załadunku']): st.link_button("📸 OTWÓRZ FOTO", row['zdjęcie po załadunku'])
                with l3:
                    if "http" in str(row['SLOT']): st.link_button("⏰ OTWÓRZ SLOT", row['SLOT'])

        # --- MONTAŻE ---
        with tab_in:
            search_in = st.text_input("🔍 Szukaj w montażach:", key="s_in")
            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]
            
            # Edytor z obsługą wyboru wiersza pod iPada (naprawione: single-row)
            ed_in_state = st.data_editor(df_in, use_container_width=True, key="ed_in", 
                                         column_config=column_cfg, on_select="rerun", 
                                         selection_mode="single-row")
            show_links_for_ipad(ed_in_state.selection.rows, df_in)

        # --- DEMONTAŻE ---
        with tab_out:
            search_out = st.text_input("🔍 Szukaj w demontażach:", key="s_out")
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]
            
            ed_out_state = st.data_editor(df_out, use_container_width=True, key="ed_out", 
                                          column_config=column_cfg, on_select="rerun", 
                                          selection_mode="single-row")
            show_links_for_ipad(ed_out_state.selection.rows, df_out)

        # --- BAZA ---
        with tab_full:
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg)

        # --- ZAPIS ---
        if btn_save:
            final_df = df.copy()
            # Zbieramy zmiany ze wszystkich edytorów (wykorzystujemy ich klucze w session_state)
            for key, original_sub_df in [("ed_in", df_in), ("ed_out", df_out), ("ed_full", df)]:
                if key in st.session_state:
                    # edytor zwraca tylko zmiany, nakładamy je na pod-dfy, a te na final_df
                    edited_rows = st.session_state[key]["edited_rows"]
                    for idx_str, changes in edited_rows.items():
                        actual_idx = original_sub_df.index[int(idx_str)]
                        for col_name, val in changes.items():
                            final_df.at[actual_idx, col_name] = val

            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("DANE ZAPISANE!")
            st.rerun()

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
