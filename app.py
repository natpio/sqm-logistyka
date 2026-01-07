import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# Inicjalizacja kontrolera ciasteczek
controller = CookieController()

# ==========================================
# 1. LOGOWANIE Z PAMIĘCIĄ
# ==========================================
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
        st.title("🔒 SQM Logistics - Logowanie")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 SQM Logistics - Logowanie")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
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
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Opcje statusów (muszą zawierać te słowa kluczowe)
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options),
        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
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

        # Definicja statusów "końcowych" dla montażu
        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        st.title("🏗️ SQM Logistics Control Tower")
        
        tab_in, tab_out, tab_priority, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "🚨 RAMPA", "📚 BAZA"])

        # --- TAB 1: MONTAŻE (Inbound) ---
        with tab_in:
            c1, c2, c3, c4 = st.columns([1.5, 2, 1, 1])
            with c1:
                selected_date = st.date_input("Dzień rozładunku:", value=datetime.now(), key="date_in")
                all_days_in = st.checkbox("Wszystkie dni", value=False, key="all_in")
            with c2:
                st.write("##")
                search_in = st.text_input("🔍 Szukaj:", key="search_active")
            with c3:
                st.write("###")
                sort_in = st.button("📅 SORTUJ", key="sort_in", use_container_width=True)
            with c4:
                st.write("###")
                if st.button("🔄 Odśwież", key="ref_in", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            # Maska: Pokaż tylko jeśli status NIE zawiera słów wyjazdowych
            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()

            if not all_days_in:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == selected_date].drop(columns=['Data_dt'])

            if sort_in:
                df_in['t_date'] = pd.to_datetime(df_in['Data'], dayfirst=True, errors='coerce')
                df_in = df_in.sort_values(by=['t_date', 'Godzina']).drop(columns=['t_date'])
            
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            updated_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg)

        # --- TAB 2: DEMONTAŻE (Outbound) ---
        with tab_out:
            st.subheader("Demontaże (Load-out)")
            search_out = st.text_input("🔍 Szukaj wywozu:", key="search_out")
            
            # Maska: Pokaż TYLKO jeśli status zawiera słowa wyjazdowe
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            
            if search_out:
                df_out = df_out[df_out.apply(lambda r: r.astype(str).str.contains(search_out, case=False).any(), axis=1)]
            
            updated_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg)

        # --- TAB 3: RAMPA ---
        with tab_priority:
            st.subheader("Auta pod rampą")
            ramp_df = df[df['STATUS'].str.contains("RAMP", na=False)].copy()
            st.dataframe(ramp_df, use_container_width=True, column_config=column_cfg)

        # --- TAB 4: PEŁNA BAZA ---
        with tab_full:
            updated_f = st.data_editor(df, use_container_width=True, key="ed_f", column_config=column_cfg)

        # ==========================================
        # 5. ZAPIS SYNCHRONIZOWANY
        # ==========================================
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            try:
                # Pobieramy najświeższe dane z edytorów i nadpisujemy główny DF
                if not updated_in.equals(df_in): 
                    df.update(updated_in)
                if not updated_out.equals(df_out): 
                    df.update(updated_out)
                if not updated_f.equals(df): 
                    df.update(updated_f)
                
                # Wysyłka do Google Sheets
                conn.update(spreadsheet=URL, data=df)
                st.cache_data.clear()
                st.success("Zapisano pomyślnie! Ładunki zostały przeliczone i posegregowane.")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        del st.session_state["password_correct"]
        st.rerun()
