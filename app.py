import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. FUNKCJA LOGOWANIA (ZABEZPIECZENIE)
# ==========================================
def check_password():
    """Zwraca True, jeśli użytkownik podał poprawne hasło."""
    def password_entered():
        # HASŁO: SQM2026 (możesz je zmienić poniżej)
        if st.session_state["password"] == "SQM2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 SQM Logistics - Dostęp autoryzowany")
        st.text_input("Podaj hasło dostępowe:", type="password", on_change=password_entered, key="password")
        st.info("System wymaga autoryzacji do wglądu w harmonogram transportów.")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 SQM Logistics - Dostęp autoryzowany")
        st.text_input("Podaj hasło dostępowe:", type="password", on_change=password_entered, key="password")
        st.error("❌ Hasło niepoprawne. Spróbuj ponownie.")
        return False
    else:
        return True

# --- URUCHOMIENIE APLIKACJI TYLKO PO LOGOWANIU ---
if check_password():

    # ==========================================
    # 2. KONFIGURACJA STRONY I STYLE CSS
    # ==========================================
    st.set_page_config(
        page_title="SQM CONTROL TOWER", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
        <style>
        /* Kafelki Dashboardu */
        div[data-testid="stMetric"] {
            background-color: #f8f9fb;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        div[data-testid="stMetricValue"] > div {
            color: #1f77b4;
        }
        /* Stylizacja zakładek */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f0f2f6;
            border-radius: 5px 5px 0 0;
            padding: 10px 20px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1f77b4 !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # Połączenie z Google Sheets
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ==========================================
    # 3. POBIERANIE I NAPRAWA DANYCH
    # ==========================================
    try:
        df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")

        # Twoja pełna lista kolumn
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 
            'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 
            'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
        ]
        
        # Wymuszamy typ tekstowy dla wszystkich kolumn
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        # ==========================================
        # 4. NAGŁÓWEK I DASHBOARD (METRYKI)
        # ==========================================
        st.title("🏗️ SQM Logistics Control Tower")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Wszystkie transporty", len(df))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m4.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        st.write("##")

        # ==========================================
        # 5. ZAKŁADKI OPERACYJNE
        # ==========================================
        tab_active, tab_priority, tab_full = st.tabs([
            "📅 HARMONOGRAM OPERACJI", 
            "🚨 TYLKO POD RAMPĄ", 
            "📚 PEŁNA BAZA (ARCHIWUM)"
        ])

        # --- ZAKŁADKA 1: HARMONOGRAM (Transporty Aktywne) ---
        with tab_active:
            col_search, col_ref = st.columns([4, 1])
            with col_search:
                search = st.text_input("🔍 Szukaj (Nr rej / Projekt / Data):", key="search_active")
            with col_ref:
                st.write("##")
                if st.button("🔄 Odśwież dane", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            # Filtr: Tylko to, co NIE jest rozładowane
            active_mask = ~df['STATUS'].str.contains("ROZŁADOWANY", na=False)
            display_df = df[active_mask].copy()

            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

            updated_active = st.data_editor(
                display_df,
                use_container_width=True,
                num_rows="dynamic",
                key="active_editor",
                column_config={
                    "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]),
                    "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                    "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                    "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                    "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
                    "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large")
                }
            )

        # --- ZAKŁADKA 2: PRIORYTETY ---
        with tab_priority:
            st.subheader("Auta aktualnie obsługiwane (POD RAMPĄ)")
            ramp_only = df[df['STATUS'].str.contains("RAMP", na=False)]
            if not ramp_only.empty:
                st.dataframe(ramp_only[['Hala', 'Auto', 'Kierowca', 'Nazwa Projektu', 'Godzina']], use_container_width=True)
            else:
                st.info("Brak aut pod rampą.")

        # --- ZAKŁADKA 3: PEŁNA BAZA ---
        with tab_full:
            st.subheader("Pełna historia i edycja archiwum")
            full_editor = st.data_editor(df, use_container_width=True, key="full_editor")

        # ==========================================
        # 6. ZAPIS ZMIAN
        # ==========================================
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            with st.spinner("Synchronizacja z bazą danych SQM..."):
                try:
                    if not updated_active.equals(display_df):
                        df.update(updated_active)
                        conn.update(spreadsheet=URL, data=df)
                    else:
                        conn.update(spreadsheet=URL, data=full_editor)
                    
                    st.cache_data.clear()
                    st.success("Dane zostały poprawnie zapisane!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd krytyczny aplikacji: {e}")

    # Przycisk wylogowania
    if st.sidebar.button("Wyloguj"):
        del st.session_state["password_correct"]
        st.rerun()
