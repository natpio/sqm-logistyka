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
            text-transform: uppercase;
        }
        </style>
        """, unsafe_allow_html=True)

    # 3. POŁĄCZENIE Z DANYMI
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    
    try:
        # Pobieranie i czyszczenie danych
        df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None'], '').str.strip()

        st.title("🏗️ SQM Logistics Control Tower")

        # 4. PANEL FILTROWANIA (Działa na oba widoki)
        with st.container(border=True):
            st.subheader("🔍 Filtry operacyjne")
            f1, f2, f3, f4 = st.columns(4)
            
            search_query = f1.text_input("Szukaj:", placeholder="Rejestracja, projekt...")
            
            # Bezpieczne pobieranie unikalnych wartości
            hale_list = sorted([h for h in df['Hala'].unique() if h])
            sel_hala = f2.multiselect("📍 Hala:", options=hale_list)
            
            sel_status = f3.multiselect("🚦 Status:", options=status_options)
            
            daty_list = sorted([d for d in df['Data'].unique() if d])
            sel_date = f4.multiselect("📅 Data:", options=daty_list)

        # --- APLIKOWANIE FILTRÓW (Tworzymy view_df) ---
        view_df = df.copy()
        
        if search_query:
            view_df = view_df[view_df.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
        if sel_hala:
            view_df = view_df[view_df['Hala'].isin(sel_hala)]
        if sel_status:
            view_df = view_df[view_df['STATUS'].isin(sel_status)]
        if sel_date:
            view_df = view_df[view_df['Data'].isin(sel_date)]

        # Tryb wyświetlania
        view_mode = st.radio("WIDOK:", ["📱 KAFELKI", "📊 TABELA"], horizontal=True)

        # 5. RENDEROWANIE
        if view_mode == "📊 TABELA":
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS AUTA", options=status_options, width="medium"),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large")
            }
            # Edytujemy tylko przefiltrowany widok
            ed_df = st.data_editor(view_df, use_container_width=True, column_config=column_cfg, key="main_editor")
            
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                edits = st.session_state["main_editor"].get("edited_rows", {})
                for r_idx_str, changes in edits.items():
                    # Mapowanie indeksu z edytora na oryginalny DataFrame
                    real_idx = view_df.index[int(r_idx_str)]
                    for col, val in changes.items():
                        df.at[real_idx, col] = val
                
                conn.update(spreadsheet=URL, data=df)
                st.cache_data.clear()
                st.success("Zapisano pomyślnie!")
                st.rerun()

        else:
            # WIDOK KAFELKOWY (Używa tego samego view_df)
            if view_df.empty:
                st.info("Brak wyników dla wybranych filtrów.")
            else:
                # Grupujemy przefiltrowane dane
                grouped = view_df.sort_values(['Data', 'Godzina']).groupby(['Data', 'Auto'])
                
                for (d_val, a_val), group in grouped:
                    st_val = str(group.iloc[0]['STATUS']).upper()
                    st_bg = "#d73a49" if "RAMP" in st_val else "#f9c000" if "TRASIE" in st_val else "#28a745" if "ROZŁADOWANY" in st_val else "#6c757d"
                    
                    st.markdown(f"""
                    <div class="truck-group-card">
                        <div class="main-status-bar" style="background:{st_bg};">{st_val}</div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="color:#666; font-size:14px;">📅 {d_val} | ⏰ {group.iloc[0]['Godzina']}</span>
                                <h2 style="margin:0; color:#1f77b4; font-size:32px;">🚚 {a_val}</h2>
                                <p style="margin:0;">Kierowca: <b>{group.iloc[0]['Kierowca']}</b> | Przewoźnik: {group.iloc[0]['Przewoźnik']}</p>
                            </div>
                            <div style="text-align:right; background:#f0f2f6; padding:10px; border-radius:10px;">
                                <span style="font-size:12px; color:#555;">SLOT</span><br>
                                <span style="font-size:24px; font-weight:bold;">{group.iloc[0]['Nr Slotu']}</span>
                            </div>
                        </div>
                        <div style="margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
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
        st.error(f"Wystąpił błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
