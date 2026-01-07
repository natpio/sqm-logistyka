import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ==========================================
# 1. LOGOWANIE - HASŁO: Czaman2026
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "Czaman2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 SQM Logistics - Dostęp autoryzowany")
        st.text_input("Podaj hasło dostępowe:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 SQM Logistics - Dostęp autoryzowany")
        st.text_input("Podaj hasło dostępowe:", type="password", on_change=password_entered, key="password")
        st.error("❌ Hasło niepoprawne.")
        return False
    else:
        return True

if check_password():

    # ==========================================
    # 2. KONFIGURACJA UI I CSS
    # ==========================================
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        div[data-testid="stMetricValue"] > div { color: #1f77b4; }
        .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px 20px; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Konfiguracja kolumn
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options),
        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
        "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large")
    }

    # ==========================================
    # 3. POBIERANIE DANYCH
    # ==========================================
    try:
        df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        # ==========================================
        # 4. DASHBOARD
        # ==========================================
        st.title("🏗️ SQM Logistics Control Tower")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Wszystkie", len(df))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m4.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        tab_active, tab_out, tab_priority, tab_full = st.tabs([
            "📅 HARMONOGRAM MONTAŻY", 
            "🔄 DEMONTAŻE / ZAŁADUNKI",
            "🚨 TYLKO POD RAMPĄ", 
            "📚 PEŁNA BAZA"
        ])

        # --- TAB 1: MONTAŻE ---
        with tab_active:
            col_date, col_search, col_sort, col_ref = st.columns([1.5, 2, 1, 1])
            with col_date:
                selected_date = st.date_input("Dzień rozładunku:", value=datetime.now(), key="date_in")
                all_days_in = st.checkbox("Wszystkie dni", value=False, key="all_in")
            with col_search:
                st.write("##")
                search_in = st.text_input("🔍 Szukaj:", key="search_active")
            with col_sort:
                st.write("###")
                sort_in = st.button("📅 SORTUJ CZASOWO", key="sort_in", use_container_width=True)
            with col_ref:
                st.write("###")
                if st.button("🔄 Odśwież", key="ref_in", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            # Filtr: tylko to co NIE jest jeszcze rozładowane (lub w trakcie)
            mask_in = ~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|EMPTIES", na=False)
            df_in = df[mask_in].copy()

            if not all_days_in:
                df_in = df_in[df_in['Data'] == selected_date.strftime("%d.%m.%Y")]
            if sort_in:
                df_in['t_date'] = pd.to_datetime(df_in['Data'], dayfirst=True, errors='coerce')
                df_in = df_in.sort_values(by=['t_date', 'Godzina']).drop(columns=['t_date'])
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            updated_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg)

        # --- TAB 2: DEMONTAŻE (KONCEPCJA 1) ---
        with tab_out:
            st.subheader("Zarządzanie załadunkiem i wywozem (Load-out)")
            col_search_out, col_ref_out = st.columns([4, 1])
            with col_search_out:
                search_out = st.text_input("🔍 Szukaj transportu do wywozu:", key="search_out")
            with col_ref_out:
                st.write("##")
                if st.button("🔄 Odśwież", key="ref_out", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            # Filtr: tylko to co JUŻ zostało rozładowane LUB jest w trakcie demontażu
            mask_out = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|EMPTIES", na=False)
            df_out = df[mask_out].copy()

            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]

            updated_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg)

        # --- TAB 3: POD RAMPĄ ---
        with tab_priority:
            st.subheader("Auta pod rampą (Montaż/Demontaż)")
            ramp_df = df[df['STATUS'].str.contains("RAMP", na=False)].copy()
            st.dataframe(ramp_df, use_container_width=True, column_config=column_cfg)

        # --- TAB 4: PEŁNA BAZA ---
        with tab_full:
            search_f = st.text_input("🔍 Szukaj w całej bazie:", key="search_f")
            df_f = df.copy()
            if search_f:
                df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_f, case=False).any(), axis=1)]
            updated_f = st.data_editor(df_f, use_container_width=True, key="ed_f", column_config=column_cfg)

        # ==========================================
        # 5. ZAPIS
        # ==========================================
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            try:
                # Scalanie zmian ze wszystkich edytorów
                if not updated_in.equals(df_in): df.update(updated_in)
                if not updated_out.equals(df_out): df.update(updated_out)
                if not updated_f.equals(df_f): df.update(updated_f)
                
                conn.update(spreadsheet=URL, data=df)
                st.cache_data.clear()
                st.success("Dane SQM zsynchronizowane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    if st.sidebar.button("Wyloguj"):
        del st.session_state["password_correct"]
        st.rerun()
