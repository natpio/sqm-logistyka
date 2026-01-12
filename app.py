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
        
        # Standaryzacja kolumn
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'PODGLĄD']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            if col != 'PODGLĄD':
                df[col] = df[col].astype(str).replace('nan', '')

        # --- 5. SIDEBAR (FILTRY) ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            st.divider()
            st.subheader("🔍 Filtry")
            f_hala = st.multiselect("Hala:", options=sorted([x for x in df['Hala'].unique() if x]))
            f_status = st.multiselect("Status:", options=sorted([x for x in df['STATUS'].unique() if x]))
            f_carrier = st.multiselect("Przewoźnik:", options=sorted([x for x in df['Przewoźnik'].unique() if x]))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracje kolumn
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", "ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"]
        hala_options = ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"]
        
        # Puste trucki do autouzupełniania
        df_empties_source = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        carriers_list = ["", "--- BRAK ---"] + sorted(df_empties_source['Przewoźnik'].unique().tolist())

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
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA"),
            "PODGLĄD": None # Ukrywamy kolumnę powodującą błędy
        }

        # --- FUNKCJA KAFELKÓW ---
        def render_grouped_tiles(dataframe):
            if dataframe.empty:
                st.info("Brak danych dla wybranych filtrów.")
                return
            
            trucks = dataframe['Auto'].unique()
            for truck in trucks:
                truck_data = dataframe[dataframe['Auto'] == truck]
                carrier = truck_data.iloc[0]['Przewoźnik']
                st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span style="font-size: 0.8em; opacity: 0.9;">PRZEWOŹNIK: {carrier}</span></div>', unsafe_allow_html=True)
                t_cols = st.columns(3)
                for idx, (_, row) in enumerate(truck_data.iterrows()):
                    with t_cols[idx % 3]:
                        s = str(row['STATUS']).upper()
                        s_class = ""
                        if "TRASIE" in s: s_class = "status-trasie"
                        elif "RAMP" in s: s_class = "status-rampa"
                        elif "ROZŁADOWANY" in s: s_class = "status-rozladowany"
                        elif "EMPTIES" in s: s_class = "status-empties"
                        elif "ZAŁADOWANY" in s: s_class = "status-zaladowany"
                        elif "PUSTY" in s: s_class = "status-pusty"

                        st.markdown(f"""
                            <div class="transport-card {s_class}">
                                <div style="font-size: 0.8em; color: #666;">{row['Data']} | Slot: {row['Nr Slotu']}</div>
                                <div style="font-weight: bold; font-size: 1.1em; color: #1f77b4; margin: 5px 0;">{row['Nazwa Projektu'] if row['Nazwa Projektu'] else 'Operacja Empties'}</div>
                                <div style="font-size: 0.9em; margin-bottom: 8px;">👤 {row['Kierowca']}<br>📍 Hala: {row['Hala']} | Godz: {row['Godzina']}</div>
                                <div style="font-weight: bold; text-align: center; background: #eee; border-radius: 4px; padding: 2px; font-size: 0.85em;">{row['STATUS']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        b1, b2 = st.columns(2)
                        with b1:
                            if row['spis casów']: st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                            if row['SLOT']: st.link_button("⏰ Slot", row['SLOT'], use_container_width=True)
                        with b2:
                            if row['zdjęcie po załadunku']: st.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                            if row['zrzut z currenta']: st.link_button("🖼️ Current", row['zrzut z currenta'], use_container_width=True)

        # --- 6. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        m4.metric("WOLNE AUTA 📦", df_empties_source['Auto'].nunique())

        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        edit_trackers = {}

        for i, tab in enumerate(tabs):
            key = ["in", "out", "empty", "empties_slots", "full"][i]
            with tab:
                # Logika filtracji dla zakładek
                if key == "in":
                    mask = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES|ODBIERA|ZAWOZI|POWRÓT", na=False, case=False))
                elif key == "out":
                    mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty":
                    mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                elif key == "empties_slots":
                    mask = df['STATUS'].str.contains("ODBIERA|ZAWOZI|POWRÓT", na=False, case=False)
                else:
                    mask = pd.Series([True] * len(df))

                df_view = df[mask].copy()

                # Aplikacja filtrów z sidebar (FIX dla isin)
                if f_hala: df_view = df_view[df_view['Hala'].isin(list(f_hala))]
                if f_status: df_view = df_view[df_view['STATUS'].isin(list(f_status))]
                if f_carrier: df_view = df_view[df_view['Przewoźnik'].isin(list(f_carrier))]

                if key == "empty":
                    df_empty_grouped = df_view.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                    ed = st.data_editor(df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, key="ed_empty", hide_index=True, column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=["⚪ PUSTY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "🟡 W TRASIE"])})
                    edit_trackers["ed_empty"] = (df_empty_grouped, ed)

                elif key == "empties_slots":
                    ed = st.data_editor(df_view[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'SLOT', 'STATUS', 'NOTATKA']], use_container_width=True, key="ed_empties_slots", hide_index=True, num_rows="dynamic", column_config=column_cfg_main)
                    edit_trackers["ed_empties_slots"] = (df_view, ed)
                    with st.expander("➕ Dodaj nowy slot"):
                        with st.form("new_slot"):
                            c1, c2, c3 = st.columns(3); f_d = c1.date_input("Data"); f_s = c2.text_input("Slot"); f_h = c3.selectbox("Hala", hala_options)
                            f_c = st.selectbox("Przewoźnik", carriers_list)
                            if st.form_submit_button("DODAJ"):
                                new_row = {col: "" for col in df.columns}
                                if f_c not in ["", "--- BRAK ---"]:
                                    m = df_empties_source[df_empties_source['Przewoźnik'] == f_c].iloc[0]
                                    new_row.update({"Auto": m['Auto'], "Kierowca": m['Kierowca']})
                                new_row.update({"Data": str(f_d), "Nr Slotu": f_s, "Hala": f_h, "Przewoźnik": f_c, "STATUS": "ODBIERA EMPTIES"})
                                conn.update(spreadsheet=URL, data=pd.concat([df, pd.DataFrame([new_row])]))
                                st.cache_data.clear(); st.rerun()

                else:
                    if view_mode == "Tradycyjny":
                        ed = st.data_editor(df_view, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main, hide_index=True, num_rows="fixed")
                        edit_trackers[f"ed_{key}"] = (df_view, ed)
                    else:
                        render_grouped_tiles(df_view)

        # --- 7. ZAPIS ---
        if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
            new_df = df.copy()
            for k, (orig_part, ed_part) in edit_trackers.items():
                state = st.session_state[k]
                for r_idx_str, col_ch in state.get("edited_rows", {}).items():
                    real_idx = orig_part.index[int(r_idx_str)]
                    for col, val in col_ch.items():
                        new_df.at[real_idx, col] = val
                        if k == "ed_empty" and col == "STATUS":
                            new_df.loc[new_df['Auto'] == orig_part.iloc[int(r_idx_str)]['Auto'], 'STATUS'] = val
            conn.update(spreadsheet=URL, data=new_df)
            st.cache_data.clear(); st.success("Zapisano!"); st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
