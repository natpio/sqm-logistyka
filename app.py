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
            background-color: #2c3e50; color: white; padding: 10px 20px;
            border-radius: 8px; margin: 30px 0 10px 0; display: flex;
            justify-content: space-between; align-items: center; font-weight: bold;
        }
        .transport-card {
            background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px;
            padding: 15px; margin-bottom: 10px; border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
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

        df["PODGLĄD"] = False

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            f_hala, f_status = [], []
            if view_mode == "Kafelkowy":
                st.divider()
                st.subheader("🔍 Filtry")
                f_hala = st.multiselect("Hala:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Status:", options=sorted(df['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # --- 6. METRYKI ---
        st.title("🏗️ SQM Control Tower")
        puste_auta_df = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        m4.metric("PUSTE TRUCKI ⚪", puste_auta_df['Auto'].nunique())

        # CIĄG DALSZY W KOLEJNEJ WIADOMOŚCI...
        # --- 7. FUNKCJA WIDOKU KAFELKOWEGO ---
        def render_tiles(dataframe):
            dff = dataframe.copy()
            if f_hala: dff = dff[dff['Hala'].isin(f_hala)]
            if f_status: dff = dff[dff['STATUS'].isin(f_status)]
            
            if dff.empty:
                st.info("Brak danych dla wybranych filtrów.")
                return

            for truck in dff['Auto'].unique():
                truck_data = dff[dff['Auto'] == truck]
                st.markdown(f'<div class="truck-separator">🚛 AUTO: {truck} | {truck_data.iloc[0]["Przewoźnik"]}</div>', unsafe_allow_html=True)
                t_cols = st.columns(3)
                for idx, (_, r) in enumerate(truck_data.iterrows()):
                    with t_cols[idx % 3]:
                        s = str(r['STATUS']).upper()
                        s_cls = ""
                        if "TRASIE" in s: s_cls = "status-trasie"
                        elif "RAMP" in s: s_cls = "status-rampa"
                        elif "ROZŁADOWANY" in s: s_cls = "status-rozladowany"
                        elif "ZAŁADOWANY" in s: s_cls = "status-zaladowany"
                        
                        st.markdown(f'''
                            <div class="transport-card {s_cls}">
                                <b>[{r["Nr Proj."]}] {r["Nazwa Projektu"]}</b><br>
                                📍 Hala: {r["Hala"]} | Godz: {r["Godzina"]}<br>
                                👤 {r["Kierowca"]}<br>
                                <small>Status: {r["STATUS"]}</small>
                            </div>
                        ''', unsafe_allow_html=True)

        # --- 8. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📚 BAZA"])
        edit_trackers = {}

        for tab, key in zip(tabs, ["in", "out", "empty", "full"]):
            with tab:
                # Logika filtrów (Maski)
                if key == "in":
                    mask = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False, case=False))
                elif key == "out":
                    mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty":
                    mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                else: mask = None

                df_view = df[mask].copy() if mask is not None else df.copy()

                # Specyfika zakładki PUSTE TRUCKI (brak powtórzeń)
                if key == "empty":
                    if not df_view.empty:
                        df_view = df_view.groupby('Auto').agg({
                            'Przewoźnik': 'first',
                            'Kierowca': 'first',
                            'STATUS': 'first'
                        }).reset_index()
                        df_view = df_view[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']]
                else:
                    # Filtrowanie daty i wyszukiwarka dla pozostałych
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                        if not all_d:
                            d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                            df_view = df_view[df_view['Data'] == str(d_val)]
                    with c2:
                        search = st.text_input("🔍 Szukaj (Projekt/Auto/Hala):", key=f"s_{key}")
                        if search:
                            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                # Dodanie kolumn technicznych LP i USUŃ
                df_view.insert(0, "LP", range(1, len(df_view) + 1))
                if key != "empty":
                    df_view.insert(1, "USUŃ", False)

                if view_mode == "Tradycyjny":
                    column_cfg = {
                        "LP": st.column_config.NumberColumn("LP", width="small", disabled=True),
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                        "STATUS": st.column_config.SelectboxColumn("STATUS", 
                            options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"], width="medium"),
                        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz")
                    }
                    ed = st.data_editor(df_view, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=column_cfg)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)
                    
                    # Notatka podglądu
                    if "PODGLĄD" in ed.columns and not ed[ed["PODGLĄD"] == True].empty:
                        row = ed[ed["PODGLĄD"] == True].iloc[-1]
                        st.info(f"**Notatka dla {row['Auto']}:** {row.get('NOTATKA', 'Brak notatki')}")
                else:
                    render_tiles(df_view)

        # --- 9. GLOBALNY ZAPIS ZMIAN ---
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
                        # Standardowa zmiana lub usuwanie
                        real_idx = orig_df_part.index[r_idx_int]
                        if col_ch.get("USUŃ") == True:
                            rows_to_delete.append(real_idx)
                        else:
                            for col, val in col_ch.items():
                                if col not in ["LP", "USUŃ", "PODGLĄD"]:
                                    final_df.at[real_idx, col] = val
            
            if rows_to_delete:
                final_df = final_df.drop(rows_to_delete)
            
            # Czyszczenie przed wysłaniem do GSheets
            cols_to_drop = ["LP", "USUŃ", "PODGLĄD"]
            final_df = final_df.drop(columns=[c for c in cols_to_drop if c in final_df.columns])
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("Baza zaktualizowana pomyślnie!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Krytyczny błąd: {e}")
