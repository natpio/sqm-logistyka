import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. FUNKCJA LOGOWANIA
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "SQM2026":
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
    # 2. KONFIGURACJA UI
    # ==========================================
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        div[data-testid="stMetricValue"] > div { color: #1f77b4; }
        .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px 20px; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ==========================================
    # 3. POBIERANIE I PRZYGOTOWANIE DANYCH
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

        tab_active, tab_priority, tab_full = st.tabs(["📅 HARMONOGRAM OPERACJI", "🚨 TYLKO POD RAMPĄ", "📚 PEŁNA BAZA (ARCHIWUM)"])

        with tab_active:
            col_search, col_sort, col_ref = st.columns([3, 1, 1])
            
            with col_search:
                search = st.text_input("🔍 Filtruj widok:", key="search_active")
            
            # --- NOWY PRZYCISK SORTOWANIA ---
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

            # Logika sortowania
            if sort_clicked:
                # Konwersja tymczasowa na format daty, aby sortowanie było poprawne (nie alfabetyczne)
                display_df['temp_date'] = pd.to_datetime(display_df['Data'], dayfirst=True, errors='coerce')
                display_df = display_df.sort_values(by=['temp_date', 'Godzina'], ascending=[True, True]).drop(columns=['temp_date'])

            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

            updated_active = st.data_editor(
                display_df, use_container_width=True, num_rows="dynamic", key="active_editor",
                column_config={
                    "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]),
                    "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                    "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                    "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                    "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz")
                }
            )

        with tab_priority:
            st.subheader("Aktualnie obsługiwane auta")
            ramp_only = df[df['STATUS'].str.contains("RAMP", na=False)]
            st.dataframe(ramp_only[['Hala', 'Auto', 'Kierowca', 'Nazwa Projektu', 'Godzina']], use_container_width=True)

        with tab_full:
            full_editor = st.data_editor(df, use_container_width=True, key="full_editor")

        # ==========================================
        # 5. ZAPIS
        # ==========================================
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            try:
                # Ważne: Jeśli dane były sortowane, musimy je scalić z oryginalnym DF po indeksach
                if not updated_active.equals(display_df):
                    df.update(updated_active)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=full_editor)
                st.cache_data.clear()
                st.success("Zapisano i zsynchronizowano!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    if st.sidebar.button("Wyloguj"):
        del st.session_state["password_correct"]
        st.rerun()
