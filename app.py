import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")

# --- 2. AUTORYZACJA ---
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
    # --- 3. STYLE CSS ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .truck-separator {
            background-color: #2c3e50;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            margin: 30px 0 15px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="10s").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        # Wymuszenie typu dla checkboxa podglądu
        df["PODGLĄD"] = False

        # --- 5. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        
        # Obliczenia statusów
        count_trasie = len(df[df['STATUS'].str.contains("TRASIE", na=False)])
        count_rampa = len(df[df['STATUS'].str.contains("RAMP", na=False)])
        count_zakonczone = len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)])
        # Nowa metryka: unikalne auta ze statusem PUSTY/EMPTIES
        puste_df = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        count_puste = puste_df['Auto'].nunique()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", count_trasie)
        m2.metric("POD RAMPĄ 🔴", count_rampa)
        m3.metric("ZAKOŃCZONE 🟢", count_zakonczone)
        m4.metric("PUSTE TRUCKI ⚪", count_puste)

        # --- 6. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📚 BAZA"])
        edit_trackers = {}

        for i, (tab, key) in enumerate(zip(tabs, ["in", "out", "empty", "full"])):
            with tab:
                # Maskowanie danych dla odpowiednich zakładek
                if key == "in":
                    mask = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False, case=False))
                elif key == "out":
                    mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty":
                    mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                else: mask = None

                df_view = df[mask].copy() if mask is not None else df.copy()

                # --- SPECYFIKA ZAKŁADKI PUSTE TRUCKI ---
                if key == "empty":
                    if not df_view.empty:
                        # Grupowanie unikalnych aut
                        df_empty_grouped = df_view.groupby('Auto').agg({
                            'Przewoźnik': 'first',
                            'Kierowca': 'first',
                            'STATUS': 'first'
                        }).reset_index()
                        
                        # Wybór i kolejność kolumn
                        df_empty_grouped = df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']]
                        df_empty_grouped.insert(0, "LP", range(1, len(df_empty_grouped) + 1))
                        
                        cfg_empty = {
                            "LP": st.column_config.NumberColumn("LP", width="small", disabled=True),
                            "STATUS": st.column_config.SelectboxColumn("Zmień status auta", 
                                options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"], width="large")
                        }
                        
                        ed_empty = st.data_editor(df_empty_grouped, use_container_width=True, hide_index=True, 
                                                 key="ed_empty", column_config=cfg_empty)
                        edit_trackers["ed_empty"] = (df_empty_grouped, ed_empty)
                    else:
                        st.info("Brak pojazdów o statusie Pusty/Empties.")

                # --- POZOSTAŁE ZAKŁADKI (MONTAŻE, ROZŁADOWANE, BAZA) ---
                else:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                        all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")

                    if not all_d: df_view = df_view[df_view['Data'] == str(d_val)]
                    if search:
                        df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                    # Dodanie LP i Checkboxa Usuń
                    df_view.insert(0, "LP", range(1, len(df_view) + 1))
                    df_view.insert(1, "USUŃ", False)

                    column_cfg = {
                        "LP": st.column_config.NumberColumn("LP", width="small", disabled=True),
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                        "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]),
                        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                        "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
                        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz")
                    }
                    
                    ed = st.data_editor(df_view, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=column_cfg)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)
                    
                    # Logika podglądu notatki
                    if not ed[ed["PODGLĄD"] == True].empty:
                        row = ed[ed["PODGLĄD"] == True].iloc[-1]
                        st.info(f"**[{row['Nr Proj.']}] {row['Nazwa Projektu']}**\n\n{row['NOTATKA']}")

        # --- 7. GLOBALNY ZAPIS ZMIAN ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            final_df = df.copy()
            rows_to_delete = []

            for k, (orig_df_part, ed_df) in edit_trackers.items():
                changes = st.session_state[k].get("edited_rows", {})
                
                for r_idx_str, col_ch in changes.items():
                    r_idx_int = int(r_idx_str)
                    
                    if k == "ed_empty":
                        # Masowa zmiana statusu dla wszystkich wierszy danego Auta
                        truck_id = orig_df_part.iloc[r_idx_int]['Auto']
                        if "STATUS" in col_ch:
                            final_df.loc[final_df['Auto'] == truck_id, 'STATUS'] = col_ch["STATUS"]
                    else:
                        # Standardowa zmiana lub usuwanie po indeksie
                        real_idx = orig_df_part.index[r_idx_int]
                        if col_ch.get("USUŃ") == True:
                            rows_to_delete.append(real_idx)
                        else:
                            for col, val in col_ch.items():
                                if col not in ["LP", "USUŃ", "PODGLĄD"]:
                                    final_df.at[real_idx, col] = val
            
            # Realizacja usuwania
            if rows_to_delete:
                final_df = final_df.drop(rows_to_delete)
            
            # Czyszczenie kolumn technicznych
            for c_drop in ["LP", "USUŃ", "PODGLĄD"]:
                if c_drop in final_df.columns:
                    final_df = final_df.drop(columns=[c_drop])
            
            # Wysyłka do Google Sheets
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success(f"Zapisano pomyślnie! (Usunięto: {len(rows_to_delete)})")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Krytyczny błąd aplikacji: {e}")
