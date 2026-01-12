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
            background-color: #2c3e50; color: white; padding: 10px 20px; border-radius: 8px; margin: 30px 0 15px 0;
            display: flex; justify-content: space-between; align-items: center;
        }
        .transport-card {
            background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 10px; border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
        hr.truck-line { border: 0; height: 2px; background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0)); margin-top: 40px; }
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
            df[col] = df[col].astype(str).replace('nan', '')

        # --- FIX DLA KOLUMNY PODGLĄD ---
        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        
        # Konwersja na bool, aby uniknąć błędu FLOAT
        df['PODGLĄD'] = df['PODGLĄD'].map({'True': True, 'False': False, True: True, False: False, '1': True, '0': False, '1.0': True, '0.0': False}).fillna(False)

        # --- DANE POMOCNICZE ---
        statusy_puste_filter = "PUSTY|EMPTIES"
        df_empties_source = df[df['STATUS'].str.contains(statusy_puste_filter, na=False, case=False)]
        available_carriers = sorted(df_empties_source['Przewoźnik'].unique().tolist())
        carriers_list = ["", "--- BRAK ---"] + available_carriers

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracje kolumn
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", "ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"]
        hala_options = ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"]
        
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options, width="medium"),
            "Hala": st.column_config.SelectboxColumn("Hala", options=hala_options),
            "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list),
            "Auto": st.column_config.TextColumn("Auto", disabled=True),
            "Kierowca": st.column_config.TextColumn("Kierowca", disabled=True),
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
        unique_empty_trucks = df_empties_source['Auto'].nunique()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        m4.metric("WOLNE AUTA 📦", unique_empty_trucks)

        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_empties_slots = "ODBIERA EMPTIES|ZAWOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        edit_trackers = {}

        for i, tab in enumerate(tabs):
            key = ["in", "out", "empty", "empties_slots", "full"][i]
            with tab:
                mask = None
                if key == "in":
                    mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & (~df['STATUS'].str.contains(statusy_puste_filter, na=False, case=False)) & (~df['STATUS'].str.contains(statusy_empties_slots, na=False, case=False))
                elif key == "out":
                    mask = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
                elif key == "empty":
                    mask = df['STATUS'].str.contains(statusy_puste_filter, na=False, case=False)
                elif key == "empties_slots":
                    mask = df['STATUS'].str.contains(statusy_empties_slots, na=False, case=False)

                df_view = df[mask].copy() if mask is not None else df.copy()

                if key == "empty":
                    df_empty_grouped = df_view.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                    df_empty_grouped = df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']]
                    ed_p = st.data_editor(
                        df_empty_grouped, use_container_width=True, key="ed_empty", hide_index=True,
                        column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=["⚪ PUSTY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "🟡 W TRASIE"])}
                    )
                    edit_trackers["ed_empty"] = (df_empty_grouped, ed_p)

                elif key == "empties_slots":
                    ed_es = st.data_editor(
                        df_view[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'SLOT', 'STATUS', 'NOTATKA']], 
                        use_container_width=True, column_config=column_cfg_main, key="ed_empties_slots", hide_index=True, num_rows="dynamic"
                    )
                    edit_trackers["ed_empties_slots"] = (df_view, ed_es)
                    
                    with st.expander("➕ Dodaj nowy slot"):
                        with st.form("new_empty_slot", clear_on_submit=True):
                            c1, c2, c3, c4 = st.columns(4)
                            f_date = c1.date_input("Data", value=datetime.now())
                            f_slot = c2.text_input("Numer Slotu")
                            f_time = c3.text_input("Godzina")
                            f_hala = c4.selectbox("Hala", hala_options)
                            c5, c6, c7 = st.columns(3)
                            f_carrier = c5.selectbox("Przewoźnik", options=carriers_list)
                            f_status = c6.selectbox("Status", ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                            f_pdf = c7.text_input("Link do PDF")
                            f_note = st.text_area("Notatka")
                            if st.form_submit_button("DODAJ DO BAZY"):
                                new_row = {col: "" for col in df.columns}
                                a_v, k_v, c_v = "", "", ""
                                if f_carrier not in ["", "--- BRAK ---"]:
                                    match = df_empties_source[df_empties_source['Przewoźnik'] == f_carrier]
                                    if not match.empty:
                                        info = match.iloc[0]; c_v, a_v, k_v = f_carrier, info['Auto'], info['Kierowca']
                                new_row.update({"Data": f_date.strftime("%Y-%m-%d"), "Nr Slotu": f_slot, "Godzina": f_time, "Hala": f_hala, "Przewoźnik": c_v, "Auto": a_v, "Kierowca": k_v, "STATUS": f_status, "SLOT": f_pdf, "NOTATKA": f_note, "PODGLĄD": False})
                                updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                                conn.update(spreadsheet=URL, data=updated_df)
                                st.cache_data.clear(); st.rerun()

                else:
                    ed = st.data_editor(df_view, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)

        # --- 7. ZAPIS ZMIAN ---
        st.divider()
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
            final_df = df.copy()
            for k, (orig_df_part, ed_df) in edit_trackers.items():
                state = st.session_state[k]
                if state.get("deleted_rows"):
                    final_df = final_df.drop(orig_df_part.index[state["deleted_rows"]])
                for r_idx_str, col_ch in state.get("edited_rows", {}).items():
                    real_idx = orig_df_part.index[int(r_idx_str)]
                    if real_idx in final_df.index:
                        for col, val in col_ch.items():
                            final_df.at[real_idx, col] = val
                            if k == "ed_empty" and col == "STATUS":
                                truck_id = orig_df_part.iloc[int(r_idx_str)]['Auto']
                                final_df.loc[final_df['Auto'] == truck_id, 'STATUS'] = val
                            if k == "ed_empties_slots" and col == "Przewoźnik":
                                if val in ["", "--- BRAK ---"]:
                                    final_df.at[real_idx, "Auto"] = ""; final_df.at[real_idx, "Kierowca"] = ""
                                else:
                                    match = df_empties_source[df_empties_source['Przewoźnik'] == val]
                                    if not match.empty:
                                        final_df.at[real_idx, "Auto"] = match.iloc[0]['Auto']
                                        final_df.at[real_idx, "Kierowca"] = match.iloc[0]['Kierowca']

            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear(); st.success("Zmiany zapisane!"); st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
