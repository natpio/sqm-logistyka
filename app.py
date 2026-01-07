import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

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
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options),
        "spis casów": st.column_config.LinkColumn("📋 Spis"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large")
    }

    try:
        # POBIERANIE DANYCH
        raw_df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")
        
        # Kluczowe: Resetujemy indeks, aby Streamlit wiedział dokładnie, który to wiersz w Excelu
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        st.title("🏗️ SQM Logistics Control Tower")
        tab_in, tab_out, tab_priority, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "🚨 RAMPA", "📚 BAZA"])

        # --- MONTAŻE ---
        with tab_in:
            c1, c2, c3, c4 = st.columns([1.5, 2, 1, 1])
            with c1:
                selected_date = st.date_input("Dzień rozładunku:", value=datetime.now(), key="d_in")
                all_days = st.checkbox("Wszystkie dni", value=False, key="a_in")
            
            mask_in = ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_in = df[mask_in].copy()

            if not all_days:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == selected_date].drop(columns=['Data_dt'])
            
            # Edytor z zachowaniem oryginalnych indeksów
            updated_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg)

        # --- DEMONTAŻE ---
        with tab_out:
            mask_out = df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)
            df_out = df[mask_out].copy()
            updated_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg)

        # --- RAMPA & BAZA ---
        with tab_priority:
            st.dataframe(df[df['STATUS'].str.contains("RAMP", na=False)], use_container_width=True)
        with tab_full:
            updated_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg)

        # --- ZAPIS (POPRAWIONA LOGIKA) ---
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            # 1. Tworzymy kopię bazy głównej
            final_df = df.copy()
            
            # 2. Nakładamy zmiany z edytorów używając indeksów (to naprawia Twój problem)
            for updated_df in [updated_in, updated_out, updated_full]:
                for index, row in updated_df.iterrows():
                    final_df.loc[index] = row
            
            # 3. Wysyłamy do Google Sheets
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("Zsynchronizowano! Jeśli zmieniłeś status, ładunek przeskoczył do właściwej zakładki.")
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
