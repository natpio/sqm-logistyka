import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

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

    # Konfiguracja kolumn (wspólna dla edytorów)
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
        m1.metric("Suma", len(df))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m4.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        tab_active, tab_priority, tab_full = st.tabs(["📅 HARMONOGRAM OPERACJI", "🚨 TYLKO POD RAMPĄ", "📚 PEŁNA BAZA (ARCHIWUM)"])

        # --- TAB 1: HARMONOGRAM ---
        with tab_active:
            col_search, col_sort, col_ref = st.columns([3, 1, 1])
            with col_search: search = st.text_input("🔍 Szukaj:", key="search_active")
            with col_sort:
                st.write("##")
                sort_clicked = st.button("📅 SORTUJ WG CZASU", use_container_width=True)
            with col_ref:
                st.write("##")
                if st.button("🔄 Odśwież", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            active_mask = ~df['STATUS'].str.contains("ROZŁADOWANY", na=False)
            display_df = df[active_mask].copy()

            if sort_clicked:
                display_df['temp_date'] = pd.to_datetime(display_df['Data'], dayfirst=True, errors='coerce')
                display_df = display_df.sort_values(by=['temp_date', 'Godzina'], ascending=[True, True]).drop(columns=['temp_date'])

            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

            updated_active = st.data_editor(display_df, use_container_width=True, key="active_editor", column_config=column_cfg)

        # --- TAB 2: POD RAMPĄ (Teraz z kompletem kolumn i linków) ---
        with tab_priority:
            st.subheader("Auta aktualnie obsługiwane")
            ramp_df = df[df['STATUS'].str.contains("RAMP", na=False)].copy()
            if not ramp_df.empty:
                # Tu używamy st.dataframe zamiast st.table, aby linki były klikalne
                st.dataframe(ramp_df, use_container_width=True, column_config=column_cfg)
            else:
                st.info("Brak aut pod rampą.")

        # --- TAB 3: PEŁNA BAZA (Z możliwością zmiany statusu) ---
        with tab_full:
            st.subheader("Archiwum i Pełna Edycja")
            search_full = st.text_input("🔍 Szukaj w całej bazie:", key="search_full")
            
            full_display = df.copy()
            if search_full:
                full_display = full_display[full_display.apply(lambda r: r.astype(str).str.contains(search_full, case=False).any(), axis=1)]
                
            updated_full = st.data_editor(full_display, use_container_width=True, key="full_editor", column_config=column_cfg)

        # ==========================================
        # 5. ZAPIS
        # ==========================================
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            with st.spinner("Zapisywanie..."):
                try:
                    # Decyzja, który edytor nadpisuje bazę
                    if not updated_active.equals(display_df):
                        df.update(updated_active)
                    elif not updated_full.equals(full_display):
                        # To pozwala na zmianę statusu w archiwum
                        df.update(updated_full)
                    
                    conn.update(spreadsheet=URL, data=df)
                    st.cache_data.clear()
                    st.success("Zapisano!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        del st.session_state["password_correct"]
        st.rerun()
