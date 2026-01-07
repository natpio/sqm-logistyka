import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. LOGOWANIE I PAMIĘĆ
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
        st.title("🔒 SQM Logistics - Control Tower")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Stylizacja pod iPada
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        .notatka-box { 
            background-color: #fff3cd; 
            padding: 20px; 
            border-radius: 10px; 
            border-left: 10px solid #ffc107; 
            margin: 20px 0;
            font-size: 20px !important;
            color: #856404;
        }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # KONFIGURACJA KOLUMN
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small", default=False),
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options, width="medium"),
        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="medium")
    }

    try:
        raw_df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        # Dodajemy kolumnę techniczną do podglądu
        if "PODGLĄD" not in df.columns:
            df.insert(0, "PODGLĄD", False)

        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        st.title("🏗️ SQM Logistics Control Tower")
        
        # METRYKI
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])

        # Funkcja podglądu notatki bez on_select
        def render_notatka_viewer(edited_df):
            selected = edited_df[edited_df["PODGLĄD"] == True]
            if not selected.empty:
                row = selected.iloc[0]
                st.markdown(f"""
                <div class="notatka-box">
                    <strong>PEŁNA NOTATKA ({row['Nazwa Projektu']}):</strong><br>
                    {row['NOTATKA']}
                </div>
                """, unsafe_allow_html=True)

        # --- MONTAŻE ---
        with tab_in:
            c1, c2, c3 = st.columns([1.5, 2, 1])
            with c1:
                selected_date = st.date_input("Dzień rozładunku:", value=datetime.now(), key="d_in")
                all_days = st.checkbox("Wszystkie dni", value=False, key="a_in")
            with c2:
                st.write("##")
                search_in = st.text_input("🔍 Szukaj ładunku:", key="s_in")
            with c3:
                st.write("###")
                if st.button("🔄 Odśwież", key="ref_in"):
                    st.cache_data.clear()
                    st.rerun()

            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()
            if not all_days:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == selected_date].drop(columns=['Data_dt'])
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg)
            render_notatka_viewer(ed_in)

        # --- DEMONTAŻE ---
        with tab_out:
            search_out = st.text_input("🔍 Szukaj wywozu:", key="s_out")
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]
            
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg)
            render_notatka_viewer(ed_out)

        # --- BAZA ---
        with tab_full:
            search_f = st.text_input("🔍 Szukaj w całej bazie:", key="s_f")
            df_f = df.copy()
            if search_f:
                df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_f, case=False).any(), axis=1)]
            ed_f = st.data_editor(df_f, use_container_width=True, key="ed_f", column_config=column_cfg)
            render_notatka_viewer(ed_f)

        # --- ZAPIS ---
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            final_df = df.copy()
            for key, source_df in [("ed_in", df_in), ("ed_out", df_out), ("ed_f", df_f)]:
                if key in st.session_state:
                    edytowane = st.session_state[key].get("edited_rows", {})
                    for row_idx_str, changes in edytowane.items():
                        real_idx = source_df.index[int(row_idx_str)]
                        for col, val in changes.items():
                            final_df.at[real_idx, col] = val
            
            # Usuwamy kolumnę techniczną przed zapisem do GSheets
            if "PODGLĄD" in final_df.columns:
                final_df = final_df.drop(columns=["PODGLĄD"])
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("Zapisano!")
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
