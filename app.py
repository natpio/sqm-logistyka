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
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        # Standaryzacja kolumn tekstowych
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace('nan', '')

        # NAPRAWA BŁĘDU TYPU DANYCH DLA CHECKBOXA
        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).astype(bool)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            if st.button("🔄 Odśwież dane"):
                st.cache_data.clear()
                st.rerun()
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracja kolumn edytora
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", "ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
        }

        # --- 6. METRYKI ---
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
                # --- ZAKŁADKA: PUSTE TRUCKI (Wyświetla tylko 4 kolumny) ---
                if key == "empty":
                    mask = df['STATUS'].str.contains(statusy_puste, na=False, case=False)
                    df_empty = df[mask].copy()
                    if not df_empty.empty:
                        df_empty_grouped = df_empty.groupby('Auto').agg({
                            'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'
                        }).reset_index()
                        
                        ed_p = st.data_editor(
                            df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], 
                            use_container_width=True, 
                            key="ed_empty",
                            column_config={
                                "Auto": st.column_config.TextColumn("DANE AUTA"),
                                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"])
                            },
                            hide_index=True
                        )
                        edit_trackers["ed_empty"] = (df_empty_grouped, ed_p)
                    else: st.info("Brak pustych pojazdów.")

                # --- ZAKŁADKA: SLOTY NA EMPTIES (Dodawanie + Edycja) ---
                elif key == "slots_empties":
                    st.subheader("Nowy Slot na Empties")
                    df_base_empties = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
                    carriers_list = sorted(df_base_empties['Przewoźnik'].unique())
                    
                    with st.form("form_empties"):
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
                                "STATUS": f_stat, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "LOGISTYKA EMPTIES"
                            }
                            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            if "PODGLĄD" in new_df.columns: new_df = new_df.drop(columns=["PODGLĄD"])
                            conn.update(spreadsheet=URL, data=new_df)
                            st.cache_data.clear()
                            st.rerun()

                    st.divider()
                    st.subheader("Zaplanowane operacje (Edytowalne)")
                    df_slots_to_edit = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)].copy()
                    if not df_slots_to_edit.empty:
                        ed_sl = st.data_editor(
                            df_slots_to_edit[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA']], 
                            use_container_width=True, 
                            key="ed_slots",
                            column_config=column_cfg_main,
                            hide_index=True
                        )
                        edit_trackers["ed_slots"] = (df_slots_to_edit, ed_sl)

                # --- POZOSTAŁE ZAKŁADKI ---
                else:
                    if key == "in":
                        mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & \
                               (~df['STATUS'].str.contains(statusy_puste, na=False, case=False)) & \
                               (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False))
                    elif key == "out":
                        mask = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
                    else: mask = None

                    df_view = df[mask].copy() if mask is not None else df.copy()
                    search = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                    if search:
                        df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                    ed = st.data_editor(df_view, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main, hide_index=True)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)

        # --- 8. GLOBALNY ZAPIS ZMIAN ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
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
                st.success("Dane zapisane w Google Sheets!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")
