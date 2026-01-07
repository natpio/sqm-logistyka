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
        st.title("🔒 SQM Logistics Control Tower")
        st.text_input("Hasło dostępowe:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide")

    # Stylizacja pod tablet i czytelność
    st.markdown("""
        <style>
        .stButton button { width: 100%; height: 55px; font-size: 18px !important; font-weight: bold; }
        [data-testid="stDataFrame"] td { padding: 12px !important; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        div[data-testid="stMetric"] { background-color: #f8f9fb; border-radius: 10px; padding: 10px; border: 1px solid #e0e0e0; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Konfiguracja kolumn
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "WYBIERZ": st.column_config.CheckboxColumn("📂", default=False),
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options),
        "spis casów": st.column_config.TextColumn("📋 Link Spis"),
        "zdjęcie po załadunku": st.column_config.TextColumn("📸 Link Foto"),
        "SLOT": st.column_config.TextColumn("⏰ Link SLOT"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="medium")
    }

    try:
        # POBIERANIE I PRZYGOTOWANIE DANYCH
        raw_df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        # Dodajemy kolumnę WYBIERZ jeśli nie istnieje (techniczna dla iPada)
        if "WYBIERZ" not in df.columns:
            df.insert(0, "WYBIERZ", False)

        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        # DASHBOARD METRYKI
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # PRZYCISKI GŁÓWNE
        c_save, c_ref = st.columns(2)
        with c_save: btn_save = st.button("💾 ZAPISZ WSZYSTKIE ZMIANY")
        with c_ref: 
            if st.button("🔄 ODŚWIEŻ DANE"):
                st.cache_data.clear()
                st.rerun()

        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 PEŁNA BAZA"])

        # Funkcja do wyświetlania przycisków linków pod tabelą
        def show_ipad_links(edited_df):
            # Sprawdza czy w session_state są jakiekolwiek zmiany w checkboxach
            selected = edited_df[edited_df["WYBIERZ"] == True]
            if not selected.empty:
                row = selected.iloc[0]
                st.info(f"Dokumentacja dla: **{row['Nazwa Projektu']}**")
                l1, l2, l3 = st.columns(3)
                with l1:
                    if "http" in str(row['spis casów']): st.link_button("📋 SPIS CASE'ÓW", row['spis casów'])
                with l2:
                    if "http" in str(row['zdjęcie po załadunku']): st.link_button("📸 FOTO", row['zdjęcie po załadunku'])
                with l3:
                    if "http" in str(row['SLOT']): st.link_button("⏰ SLOT / AWIZACJA", row['SLOT'])

        # --- ZAKŁADKA 1: MONTAŻE ---
        with tab_in:
            c1, c2 = st.columns([1, 2])
            with c1:
                selected_date = st.date_input("Dzień rozładunku:", value=datetime.now(), key="d_in")
                all_days = st.checkbox("Pokaż wszystkie dni", value=False, key="a_in")
            with c2:
                search_in = st.text_input("🔍 Szukaj w montażach (auto, nr projektu, hala):", key="s_in")
            
            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()

            if not all_days:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == selected_date].drop(columns=['Data_dt'])
            
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]
            
            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg)
            show_ipad_links(ed_in)

        # --- ZAKŁADKA 2: DEMONTAŻE ---
        with tab_out:
            search_out = st.text_input("🔍 Szukaj w demontażach:", key="s_out")
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            
            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]
                
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg)
            show_ipad_links(ed_out)

        # --- ZAKŁADKA 3: BAZA ---
        with tab_full:
            search_f = st.text_input("🔍 Szukaj w całej bazie:", key="s_f")
            df_f = df.copy()
            if search_f:
                df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_f, case=False).any(), axis=1)]
            ed_full = st.data_editor(df_f, use_container_width=True, key="ed_full", column_config=column_cfg)

        # --- LOGIKA ZAPISU (Pancerne łączenie zmian) ---
        if btn_save:
            final_df = df.copy()
            # Iterujemy przez wszystkie edytory i nakładamy zmiany na bazę główną
            for key, source_df in [("ed_in", df_in), ("ed_out", df_out), ("ed_full", df_f)]:
                if key in st.session_state:
                    edytowane = st.session_state[key].get("edited_rows", {})
                    for row_idx_str, changes in edytowane.items():
                        real_idx = source_df.index[int(row_idx_str)]
                        for col, val in changes.items():
                            final_df.at[real_idx, col] = val
            
            # Czyścimy kolumnę techniczną WYBIERZ przed wysłaniem do GSheets
            if "WYBIERZ" in final_df.columns:
                final_df = final_df.drop(columns=["WYBIERZ"])
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("✅ ZMIANY ZAPISANE POMYŚLNIE!")
            st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    # Sidebar z wylogowaniem i informacją o firmie
    st.sidebar.title("SQM Logistics")
    st.sidebar.info("Pracujesz w SQM Multimedia Solutions. System Control Tower.")
    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
