import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. KONFIGURACJA I AUTORYZACJA
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

    # 2. STYLIZACJA CSS
    st.markdown("""
        <style>
        .truck-group-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-left: 8px solid #1f77b4;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .project-sub-row {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 10px;
            margin-top: 5px;
            border: 1px solid #eee;
            font-size: 14px;
        }
        .main-status-bar {
            padding: 8px 15px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            font-size: 16px;
            text-align: center;
            margin-bottom: 15px;
        }
        .filter-section {
            background-color: #f1f3f5;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)

    # 3. POŁĄCZENIE Z DANYMI
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    
    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Logistics Control Tower")

        # 4. MULTI-FILTR (Dynamiczny)
        with st.expander("🔍 PANEL FILTROWANIA I WYSZUKIWANIA", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            # Pobieranie unikalnych wartości dla filtrów (zabezpieczenie przed TypeError)
            def get_unique(col):
                return sorted([x for x in df[col].unique() if x.strip()])

            search_query = f_col1.text_input("Szukaj frazy:", placeholder="Rejestracja, projekt, kierowca...")
            sel_hala = f_col2.multiselect("📍 Hala:", options=get_unique('Hala'))
            sel_status = f_col3.multiselect("🚦 Status Auta:", options=status_options)
            sel_date = f_col4.multiselect("📅 Data:", options=get_unique('Data'))

        # Aplikowanie filtrów
        filtered_df = df.copy()
        if search_query:
            filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
        if sel_hala:
            filtered_df = filtered_df[filtered_df['Hala'].isin(sel_hala)]
        if sel_status:
            filtered_df = filtered_df[filtered_df['STATUS'].isin(sel_status)]
        if sel_date:
            filtered_df = filtered_df[filtered_df['Data'].isin(sel_date)]

        # Wybór widoku
        view_mode = st.radio("TRYB WYŚWIETLANIA:", ["📱 KAFELKI (AUTO-CENTRIC)", "📊 TABELA (EDYCJA DANYCH)"], horizontal=True)

        # 5. RENDEROWANIE
        if view_mode == "📊 TABELA (EDYCJA DANYCH)":
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS AUTA", options=status_options, width="medium"),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large")
            }
            ed_df = st.data_editor(filtered_df, use_container_width=True, column_config=column_cfg, key="main_editor")
            
            if st.button("💾 ZAPISZ ZMIANY W BAZIE", type="primary", use_container_width=True):
                # Mapowanie zmian z powrotem do głównego df
                edits = st.session_state["main_editor"].get("edited_rows", {})
                for r_idx_str, changes in edits.items():
                    real_idx = filtered_df.index[int(r_idx_str)]
                    for col, val in changes.items():
                        df.at[real_idx, col] = val
                
                conn.update(spreadsheet=URL, data=df)
                st.cache_data.clear()
                st.success("Zapisano pomyślnie!")
                st.rerun()

        else:
            # WIDOK KAFELKOWY (Grupowanie po AUCIE)
            if filtered_df.empty:
                st.warning("Brak transportów dla wybranych filtrów.")
            else:
                grouped = filtered_df.sort_values(['Data', 'Godzina']).groupby(['Data', 'Auto'])
                
                for (d_val, a_val), group in grouped:
                    # Status bierzemy z pierwszego wiersza (bo auto ma jeden status)
                    st_val = str(group.iloc[0]['STATUS']).upper()
                    st_bg = "#d73a49" if "RAMP" in st_val else "#f9c000" if "TRASIE" in st_val else "#28a745" if "ROZŁADOWANY" in st_val else "#6c757d"
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="truck-group-card">
                            <div class="main-status-bar" style="background:{st_bg};">{st_val}</div>
                            <div style="display: flex; justify-content: space-between;">
                                <div>
                                    <span style="background:#333; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">📅 {d_val}</span>
                                    <h2 style="margin:5px 0; color:#1f77b4; font-size:36px;">🚚 {a_val}</h2>
                                    <p style="margin:0;">Kierowca: <b>{group.iloc[0]['Kierowca']}</b> | Przewoźnik: {group.iloc[0]['Przewoźnik']}</p>
                                </div>
                                <div style="text-align:right;">
                                    <div style="font-size:28px; font-weight:bold;">⏰ {group.iloc[0]['Godzina']}</div>
                                    <div style="color:#666;">SLOT: {group.iloc[0]['Nr Slotu']}</div>
                                </div>
                            </div>
                            <div style="margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
                                <b>📦 ŁADUNEK (PROJEKTY):</b>
                        """, unsafe_allow_html=True)
                        
                        for _, row in group.iterrows():
                            c1, c2 = st.columns([4, 1])
                            with c1:
                                st.markdown(f"""<div class="project-sub-row">
                                    <b>{row['Nr Proj.']}</b> | {row['Nazwa Projektu']} | 📍 Hala: {row['Hala']}
                                </div>""", unsafe_allow_html=True)
                            with c2:
                                btns = st.columns(3)
                                if "http" in str(row['spis casów']): btns[0].link_button("📋", row['spis casów'])
                                if "http" in str(row['zdjęcie po załadunku']): btns[1].link_button("📸", row['zdjęcie po załadunku'])
                                if row['NOTATKA']:
                                    with btns[2].expander("📝"): st.caption(row['NOTATKA'])
                        
                        st.markdown("</div></div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
