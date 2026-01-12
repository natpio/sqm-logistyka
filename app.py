import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
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
        else: st.session_state["password_correct"] = False
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
        .transport-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
        hr.truck-line {
            border: 0;
            height: 2px;
            background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0));
            margin-top: 40px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).astype(bool)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            
            if view_mode == "Kafelkowy":
                st.divider()
                st.subheader("🔍 Filtry Widoku")
                f_hala = st.multiselect("Filtruj wg Hali:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Filtruj wg Statusu:", options=sorted(df['STATUS'].unique()))
                f_carrier = st.multiselect("Filtruj wg Przewoźnika:", options=sorted(df['Przewoźnik'].unique()))
            
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracja edytora głównego
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", "ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Foto", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
        }

        # --- 6. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # --- 7. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"
        statusy_nowe_empties = "ODBIERA EMPTIES|ZAVOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        edit_trackers = {}

        for i, (tab, key) in enumerate(zip(tabs, ["in", "out", "empty", "slots_empties", "full"])):
            with tab:
                # SEKCJA: PUSTE TRUCKI (ZAKŁADKA 3)
                if key == "empty":
                    mask = df['STATUS'].str.contains(statusy_puste, na=False, case=False)
                    df_empty = df[mask].copy()
                    
                    if not df_empty.empty:
                        # Grupowanie po Auto, aby wyświetlić unikalne pojazdy
                        df_empty_grouped = df_empty.groupby('Auto').agg({
                            'Przewoźnik': 'first',
                            'Kierowca': 'first',
                            'STATUS': 'first'
                        }).reset_index()
                        
                        st.info("Lista unikalnych pojazdów o statusie PUSTY lub EMPTIES.")
                        
                        # Zmieniona konfiguracja kolumn na żądanie użytkownika
                        ed_p = st.data_editor(
                            df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], 
                            use_container_width=True, 
                            key="ed_empty",
                            column_config={
                                "Auto": st.column_config.TextColumn("DANE AUTA"),
                                "STATUS": st.column_config.SelectboxColumn("STATUS (Zmień dla całego auta)", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"], width="large")
                            },
                            hide_index=True
                        )
                        edit_trackers["ed_empty"] = (df_empty_grouped, ed_p)
                    else:
                        st.info("Obecnie brak pojazdów w statusie Pusty/Empties.")

                # SEKCJA: SLOTY NA EMPTIES (ZAKŁADKA 4)
                elif key == "slots_empties":
                    st.subheader("Planowanie Slotów na Empties")
                    df_base_empties = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
                    carriers_list = sorted(df_base_empties['Przewoźnik'].unique())
                    
                    with st.form("new_slot_form"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            f_data = st.date_input("DATA", value=datetime.now())
                            f_slot = st.text_input("NUMER SLOTU")
                        with c2:
                            f_godz = st.text_input("GODZINA")
                            f_hala = st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                        with c3:
                            f_carr = st.selectbox("PRZEWOŹNIK", carriers_list)
                            f_stat = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                        
                        if st.form_submit_button("DODAJ SLOT", use_container_width=True):
                            match = df_base_empties[df_base_empties['Przewoźnik'] == f_carr].iloc[0]
                            new_row = {
                                "Data": str(f_data), "Nr Slotu": f_slot, "Godzina": f_godz, "Hala": f_hala,
                                "Przewoźnik": f_carr, "Auto": match['Auto'], "Kierowca": match['Kierowca'],
                                "STATUS": f_stat, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "OBSŁUGA EMPTIES"
                            }
                            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            if "PODGLĄD" in new_df.columns: new_df = new_df.drop(columns=["PODGLĄD"])
                            conn.update(spreadsheet=URL, data=new_df)
                            st.cache_data.clear()
                            st.rerun()

                    st.divider()
                    df_slots = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)]
                    st.dataframe(df_slots[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, hide_index=True)

                # SEKCJA: POZOSTAŁE ZAKŁADKI (MONTAŻE, ROZŁADOWANE, BAZA)
                else:
                    if key == "in":
                        mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & \
                               (~df['STATUS'].str.contains(statusy_puste, na=False, case=False)) & \
                               (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False))
                    elif key == "out":
                        mask = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
                    else: mask = None

                    df_view = df[mask].copy() if mask is not None else df.copy()

                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    with c1:
                        if key == "in":
                            d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                            all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                    with c3:
                        st.write("###")
                        if st.button("🔄 Odśwież", key=f"r_{key}"):
                            st.cache_data.clear()
                            st.rerun()

                    if key == "in" and not all_d:
                        df_view['Data_dt'] = pd.to_datetime(df_view['Data'], errors='coerce')
                        df_view = df_view[df_view['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
                    if search:
                        df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                    if view_mode == "Tradycyjny":
                        ed = st.data_editor(df_view, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main)
                        edit_trackers[f"ed_{key}"] = (df_view, ed)
                    else:
                        st.info("Widok kafelkowy dostępny po przełączeniu w Sidebarze.")

        # --- 8. GLOBALNY ZAPIS ZMIAN ---
        if view_mode == "Tradycyjny" and edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig_df_part, ed_df) in edit_trackers.items():
                    changes = st.session_state[k].get("edited_rows", {})
                    if k == "ed_empty":
                        for r_idx_str, col_ch in changes.items():
                            if "STATUS" in col_ch:
                                truck_id = orig_df_part.iloc[int(r_idx_str)]['Auto']
                                final_df.loc[final_df['Auto'] == truck_id, 'STATUS'] = col_ch["STATUS"]
                    else:
                        for r_idx_str, col_ch in changes.items():
                            real_idx = orig_df_part.index[int(r_idx_str)]
                            for col, val in col_ch.items():
                                final_df.at[real_idx, col] = val
                
                if "PODGLĄD" in final_df.columns: final_df = final_df.drop(columns=["PODGLĄD"])
                conn.update(spreadsheet=URL, data=final_df)
                st.cache_data.clear()
                st.success("Wszystkie zmiany zostały zapisane!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")
