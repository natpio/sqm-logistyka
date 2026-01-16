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
        .stRadio [data-testid="stWidgetLabel"] { display: none; }
        .note-box {
            background-color: #1e1e1e;
            color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #00ff00;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m")
        df = raw_df.dropna(how="all").reset_index(drop=True)
        
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 
            'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'Opłata'
        ]
        
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', 'nan nan', '<NA>', 'None None'], '')

        if "PODGLĄD" not in df.columns:
            idx = df.columns.get_loc("NOTATKA")
            df.insert(idx, "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).map(lambda x: True if x == 1 or x is True else False)

        # Pobieranie bazy przewoźników dla list rozwijanych i autofill
        carriers_db = df[df['Przewoźnik'] != ""].groupby('Przewoźnik').agg({'Auto': 'last', 'Kierowca': 'last'}).to_dict('index')
        lista_przewoznikow = sorted(list(carriers_db.keys()))

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ SQM Logistics")
            if st.button("🔄 Odśwież dane"):
                st.cache_data.clear()
                st.rerun()
            st.divider()
            if st.button("🚪 Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracja kolumn - ujednolicona
        column_cfg = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=[
                "🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", 
                "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", 
                "ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK",
                "DO ZAPLANOWANIA", "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"
            ]),
            "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=lista_przewoznikow),
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

        # --- 7. NAWIGACJA ---
        menu_options = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "🛠️ DEMONTAŻE", "📚 BAZA"]
        choice = st.radio("Widok:", menu_options, horizontal=True, key="main_nav")
        st.divider()

        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_wolne = "PUSTY|📦 EMPTIES"
        statusy_nowe_empties = "ODBIERA EMPTIES|ZAVOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        edit_trackers = {}

        # --- SEKTYCJA: MONTAŻE ---
        if choice == "📅 MONTAŻE":
            c1, c2, c3 = st.columns([1.5, 1, 2])
            with c1: d_val = st.date_input("Dzień:", value=datetime.now(), key="d_in")
            with c2: 
                st.write("###")
                all_d = st.checkbox("Wszystkie dni", value=False, key="a_in")
            with c3: search_in = st.text_input("🔍 Szukaj projektu:", key="s_in")

            mask_in = (
                (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & 
                (~df['STATUS'].str.contains("PUSTY", na=False, case=False)) & 
                (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)) &
                (~df['Nr Proj.'].str.contains("EMPTIES", na=False, case=False)) &
                (df['Nr Proj.'] != "")
            )
            df_in = df[mask_in].copy()
            if not all_d:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce', dayfirst=True)
                df_in = df_in[df_in['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)
            
            for _, row in ed_in[ed_in["PODGLĄD"] == True].iterrows():
                st.markdown(f"<div class='note-box'><b>PROJEKT: {row['Nr Proj.']}</b></div>", unsafe_allow_html=True)
                st.info(row['NOTATKA'])

        # --- SEKTYCJA: ROZŁADOWANE ---
        elif choice == "🟢 ROZŁADOWANE":
            mask_out = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
            df_out = df[mask_out].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)

        # --- SEKTYCJA: PUSTE TRUCKI ---
        elif choice == "⚪ PUSTE TRUCKI":
            st.info("Pojazdy gotowe do planowania (Status: PUSTY / EMPTIES)")
            mask_empty = (df['STATUS'].str.contains(statusy_wolne, na=False, case=False)) & (df['Auto'] != "")
            df_empty = df[mask_empty].copy()
            if not df_empty.empty:
                df_empty_grouped = df_empty.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                ed_empty = st.data_editor(df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, key="ed_empty", column_config={"Auto": st.column_config.TextColumn("DANE AUTA")}, hide_index=True)
                edit_trackers["ed_empty"] = (df_empty_grouped, ed_empty)

        # --- SEKTYCJA: SLOTY NA EMPTIES ---
        elif choice == "📦 SLOTY NA EMPTIES":
            st.subheader("➕ Zaplanuj slot")
            df_puste_form = df[(df['STATUS'].str.contains(statusy_wolne, na=False, case=False)) & (df['Auto'] != "")]
            lista_przew = sorted(df_puste_form['Przewoźnik'].unique()) if not df_puste_form.empty else []
            with st.form("form_emp"):
                c1, c2, c3 = st.columns(3)
                with c1: f_d, f_s = st.date_input("DATA"), st.text_input("NR SLOTU")
                with c2: f_g, f_h = st.text_input("GODZINA"), st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c3: 
                    f_c = st.selectbox("PRZEWOŹNIK (Opcjonalnie)", ["-- Brak / Nowy --"] + lista_przew)
                    f_st = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                if st.form_submit_button("DODAJ SLOT", use_container_width=True):
                    auto_val, kier_val = "", ""
                    curr_carr = f_c if f_c != "-- Brak / Nowy --" else ""
                    if curr_carr and not df_puste_form[df_puste_form['Przewoźnik'] == f_c].empty:
                        match = df_puste_form[df_puste_form['Przewoźnik'] == f_c].iloc[0]
                        auto_val, kier_val = match['Auto'], match['Kierowca']
                    new_row = {col: "" for col in all_cols}
                    new_row.update({"Data": str(f_d), "Nr Slotu": f_s, "Godzina": f_g, "Hala": f_h, "Przewoźnik": curr_carr, "Auto": auto_val, "Kierowca": kier_val, "STATUS": f_st, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "OBSŁUGA EMPTIES"})
                    save_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    conn.update(spreadsheet=URL, data=save_df[all_cols]); st.cache_data.clear(); st.rerun()

            st.divider()
            df_sl = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)].copy()
            ed_sl = st.data_editor(df_sl[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'PODGLĄD', 'NOTATKA']], use_container_width=True, key="ed_sl", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_sl"] = (df_sl, ed_sl)
            for _, row in ed_sl[ed_sl["PODGLĄD"] == True].iterrows():
                st.markdown(f"<div class='note-box'><b>SLOT: {row['Nr Slotu']} ({row['Auto']})</b></div>", unsafe_allow_html=True)
                st.info(row['NOTATKA'])

        # --- SEKTYCJA: DEMONTAŻE ---
        elif choice == "🛠️ DEMONTAŻE":
            st.subheader("🚛 Planowanie Demontaży")
            s_query = st.text_input("🔍 Szukaj projektu (Nr/Nazwa):", key="s_demo").lower()
            
            # Pobieramy unikalne projekty z bazy, aby móc dla nich zaplanować demontaż
            df_projs = df[(df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES")].drop_duplicates(subset=['Nr Proj.']).copy()
            
            df_demo_view = pd.DataFrame(columns=all_cols)
            df_demo_view['Nr Proj.'] = df_projs['Nr Proj.']
            df_demo_view['Nazwa Projektu'] = df_projs['Nazwa Projektu']
            df_demo_view['Hala'] = df_projs['Hala']
            df_demo_view['PODGLĄD'] = False
            df_demo_view = df_demo_view.fillna("")

            if s_query:
                df_demo_view = df_demo_view[df_demo_view['Nr Proj.'].str.lower().str.contains(s_query) | df_demo_view['Nazwa Projektu'].str.lower().str.contains(s_query)]

            cols_demo = ['PODGLĄD', 'Nr Proj.', 'Nazwa Projektu', 'Hala', 'Nr Slotu', 'Data', 'Godzina', 'STATUS', 'Przewoźnik', 'Auto', 'Kierowca', 'Opłata', 'SLOT', 'NOTATKA']
            ed_demo = st.data_editor(df_demo_view[cols_demo], use_container_width=True, key="ed_demo", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_demo"] = (df_demo_view, ed_demo)

            for _, row in ed_demo[ed_demo["PODGLĄD"] == True].iterrows():
                st.markdown(f"<div class='note-box'><b>PROJEKT: {row['Nr Proj.']} - {row['Nazwa Projektu']}</b></div>", unsafe_allow_html=True)
                st.info(row['NOTATKA'] if row['NOTATKA'] and row['NOTATKA'] != "" else "Brak notatki dla tego wiersza.")

        # --- SEKTYCJA: BAZA ---
        elif choice == "📚 BAZA":
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- 8. GLOBALNY ZAPIS ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig_df, ed_comp) in edit_trackers.items():
                    changes = st.session_state[k].get("edited_rows", {})
                    
                    if k == "ed_demo":
                        new_rows = []
                        for r_idx, c_vals in changes.items():
                            row_data = orig_df.iloc[int(r_idx)].to_dict()
                            row_data.update(c_vals)
                            
                            # Logika Autofill dla nowych demontaży
                            p_name = row_data.get('Przewoźnik')
                            if p_name in carriers_db:
                                if not row_data.get('Auto') or row_data.get('Auto') == "":
                                    row_data['Auto'] = carriers_db[p_name]['Auto']
                                if not row_data.get('Kierowca') or row_data.get('Kierowca') == "":
                                    row_data['Kierowca'] = carriers_db[p_name]['Kierowca']
                            new_rows.append(row_data)
                        if new_rows: final_df = pd.concat([final_df, pd.DataFrame(new_rows)], ignore_index=True)
                    
                    elif k == "ed_empty":
                        for r_idx, c_vals in changes.items():
                            if "STATUS" in c_vals:
                                a_id = orig_df.iloc[int(r_idx)]['Auto']
                                final_df.loc[final_df['Auto'] == a_id, 'STATUS'] = c_vals["STATUS"]
                    else:
                        for r_idx, c_vals in changes.items():
                            actual_idx = orig_df.index[int(r_idx)]
                            for col, val in c_vals.items():
                                final_df.at[actual_idx, col] = val

                to_save = final_df.copy()
                if "PODGLĄD" in to_save.columns: to_save = to_save.drop(columns=["PODGLĄD"])
                conn.update(spreadsheet=URL, data=to_save[all_cols])
                st.cache_data.clear(); st.success("Dane zsynchronizowane!"); st.rerun()

    except Exception as e:
        st.error(f"Krytyczny błąd: {e}")
