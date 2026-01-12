import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM CONTROL TOWER", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. AUTORYZACJA (HASŁO I CIASTECZKA) ---
controller = CookieController()

def check_password():
    """Obsługa logowania i zapamiętywania sesji."""
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
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Błędne hasło")
        return False
    return True

if check_password():
    # --- 3. STYLE CSS (METRYKI I KARTY) ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { 
            background-color: #f8f9fb; 
            border: 1px solid #e0e0e0; 
            padding: 15px; 
            border-radius: 10px; 
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f0f2f6;
            border-radius: 4px 4px 0px 0px;
            padding: 10px 20px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z ARKUSZEM I PRZYGOTOWANIE DANYCH ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        # Odczyt danych i wstępne czyszczenie
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        # Standaryzacja kolumn
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 
            'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
        ]
        
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT'], '')

        # KLUCZOWA POPRAWKA: Obsługa błędu ColumnDataKind.FLOAT dla PODGLĄD
        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        else:
            # Konwersja na typ logiczny, aby checkbox w edytorze działał poprawnie
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).map(lambda x: True if x == 1 or x is True else False)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ SQM Logistics")
            if st.button("🔄 Odśwież dane z arkusza"):
                st.cache_data.clear()
                st.rerun()
            st.divider()
            if st.button("🚪 Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Definicja konfiguracji edytora (st.data_editor)
        column_cfg = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=[
                "🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", 
                "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", 
                "ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"
            ], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
        }

        # --- 6. NAGŁÓWEK I STATYSTYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # --- 7. LOGIKA ZAKŁADEK ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        # Definicje masek (filtrów)
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"
        statusy_nowe_empties = "ODBIERA EMPTIES|ZAVOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        # Słownik do śledzenia zmian w edytorach w różnych zakładkach
        edit_trackers = {}

        # --- ZAKŁADKA 1: MONTAŻE ---
        with tabs[0]:
            col_d1, col_d2, col_s = st.columns([1.5, 1, 2])
            with col_d1:
                selected_date = st.date_input("Dzień montażu:", value=datetime.now(), key="date_in")
            with col_d2:
                st.write("###")
                show_all_days = st.checkbox("Wszystkie dni", value=False, key="all_days_in")
            with col_s:
                search_in = st.text_input("🔍 Szukaj projektu / auta:", key="search_in")

            # Maska: Ukrywamy rozładowane, puste oraz WSZYSTKIE wpisy "Empties" (projekt i statusy)
            mask_in = (
                (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & 
                (~df['STATUS'].str.contains("PUSTY", na=False, case=False)) & 
                (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)) &
                (~df['Nr Proj.'].str.contains("EMPTIES", na=False, case=False))
            )
            df_in = df[mask_in].copy()

            if not show_all_days:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == selected_date].drop(columns=['Data_dt'])
            
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            ed_in = st.data_editor(df_in, use_container_width=True, key="editor_in", column_config=column_cfg, hide_index=True)
            edit_trackers["editor_in"] = (df_in, ed_in)

        # --- ZAKŁADKA 2: ROZŁADOWANE ---
        with tabs[1]:
            mask_out = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
            df_out = df[mask_out].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="editor_out", column_config=column_cfg, hide_index=True)
            edit_trackers["editor_out"] = (df_out, ed_out)

        # --- ZAKŁADKA 3: PUSTE TRUCKI ---
        with tabs[2]:
            st.info("Pojazdy gotowe do planowania (Status: PUSTY / EMPTIES)")
            mask_empty = df['STATUS'].str.contains(statusy_puste, na=False, case=False)
            df_empty_raw = df[mask_empty].copy()
            
            if not df_empty_raw.empty:
                df_empty_grouped = df_empty_raw.groupby('Auto').agg({
                    'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'
                }).reset_index()
                
                ed_empty = st.data_editor(
                    df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], 
                    use_container_width=True, key="editor_empty",
                    column_config={"Auto": st.column_config.TextColumn("DANE AUTA")},
                    hide_index=True
                )
                edit_trackers["editor_empty"] = (df_empty_grouped, ed_empty)
            else:
                st.warning("Brak aut o statusie Pusty/Empties.")

        # --- ZAKŁADKA 4: SLOTY NA EMPTIES ---
        with tabs[3]:
            st.subheader("➕ Zaplanuj slot na Empties")
            # Pobieramy tylko te auta, które faktycznie są puste
            df_puste_dla_form = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
            lista_przewoznikow = sorted(df_puste_dla_form['Przewoźnik'].unique())

            with st.form("form_new_slot_empties"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    f_data = st.date_input("DATA", value=datetime.now())
                    f_slot = st.text_input("NUMER SLOTU")
                with c2:
                    f_godz = st.text_input("GODZINA")
                    f_hala = st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c3:
                    f_carr = st.selectbox("PRZEWOŹNIK", lista_przewoznikow if lista_przewoznikow else ["Brak"])
                    f_stat = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                
                if st.form_submit_button("DODAJ DO HARMONOGRAMU", use_container_width=True):
                    if lista_przewoznikow and f_carr != "Brak":
                        match = df_puste_dla_form[df_puste_dla_form['Przewoźnik'] == f_carr].iloc[0]
                        new_row = {
                            "Data": str(f_data), "Nr Slotu": f_slot, "Godzina": f_godz, "Hala": f_hala,
                            "Przewoźnik": f_carr, "Auto": match['Auto'], "Kierowca": match['Kierowca'],
                            "STATUS": f_stat, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "LOGISTYKA EMPTIES"
                        }
                        updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        if "PODGLĄD" in updated_df.columns: updated_df = updated_df.drop(columns=["PODGLĄD"])
                        conn.update(spreadsheet=URL, data=updated_df)
                        st.cache_data.clear()
                        st.success("Slot dodany!")
                        st.rerun()

            st.divider()
            st.subheader("📝 Aktywne operacje Empties")
            # Wyświetlamy tylko wiersze z danymi (eliminacja pustych)
            df_sl = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)].copy()
            df_sl = df_sl[df_sl['Data'] != ""] 
            
            if not df_sl.empty:
                ed_sl = st.data_editor(
                    df_sl[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA']], 
                    use_container_width=True, key="editor_sl", column_config=column_cfg, hide_index=True
                )
                edit_trackers["editor_sl"] = (df_sl, ed_sl)
            else:
                st.info("Brak aktywnych slotów na Empties.")

        # --- ZAKŁADKA 5: BAZA ---
        with tabs[4]:
            search_full = st.text_input("🔍 Przeszukaj całą bazę danych:", key="search_full")
            df_full = df.copy()
            if search_full:
                df_full = df_full[df_full.apply(lambda r: r.astype(str).str.contains(search_full, case=False).any(), axis=1)]
            
            ed_full = st.data_editor(df_full, use_container_width=True, key="editor_full", column_config=column_cfg, hide_index=True)
            edit_trackers["editor_full"] = (df_full, ed_full)

        # --- 8. ZAPISYWANIE ZMIAN ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY DO ARKUSZA", type="primary", use_container_width=True):
                final_df = df.copy()
                
                for key, (original_df_part, edited_df) in edit_trackers.items():
                    changes = st.session_state[key].get("edited_rows", {})
                    
                    if key == "editor_empty":
                        # Masowa aktualizacja statusu dla danego auta
                        for r_idx_str, col_changes in changes.items():
                            if "STATUS" in col_changes:
                                auto_id = original_df_part.iloc[int(r_idx_str)]['Auto']
                                final_df.loc[final_df['Auto'] == auto_id, 'STATUS'] = col_changes["STATUS"]
                    else:
                        # Standardowa aktualizacja pojedynczych komórek
                        for r_idx_str, col_changes in changes.items():
                            real_idx = original_df_part.index[int(r_idx_str)]
                            for col, val in col_changes.items():
                                final_df.at[real_idx, col] = val
                
                # Usuwamy techniczną kolumnę PODGLĄD przed wysyłką do Google Sheets
                save_df = final_df.copy()
                if "PODGLĄD" in save_df.columns:
                    save_df = save_df.drop(columns=["PODGLĄD"])
                
                conn.update(spreadsheet=URL, data=save_df)
                st.cache_data.clear()
                st.success("Synchronizacja zakończona pomyślnie!")
                st.rerun()

    except Exception as e:
        st.error(f"Wystąpił błąd krytyczny aplikacji: {e}")
        st.info("Spróbuj odświeżyć stronę lub sprawdź uprawnienia do arkusza Google.")
