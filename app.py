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
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

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

        # Konfiguracje dla edytora
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Foto", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
        }

        def render_grouped_tiles(dataframe):
            dff = dataframe.copy()
            if view_mode == "Kafelkowy":
                if f_hala: dff = dff[dff['Hala'].isin(f_hala)]
                if f_status: dff = dff[dff['STATUS'].isin(f_status)]
                if f_carrier: dff = dff[dff['Przewoźnik'].isin(f_carrier)]

            if dff.empty:
                st.info("Brak danych dla wybranych filtrów.")
                return
            
            trucks = dff['Auto'].unique()
            for truck in trucks:
                truck_data = dff[dff['Auto'] == truck]
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
                                <div style="font-weight: bold; font-size: 1.1em; color: #1f77b4; margin: 5px 0;">[{row['Nr Proj.']}] {row['Nazwa Projektu']}</div>
                                <div style="font-size: 0.9em; margin-bottom: 8px;">👤 {row['Kierowca']}<br>📍 Hala: {row['Hala']} | Godz: {row['Godzina']}</div>
                                <div style="font-weight: bold; text-align: center; background: #eee; border-radius: 4px; padding: 2px; font-size: 0.85em;">{row['STATUS']}</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        b1, b2 = st.columns(2)
                        with b1:
                            if row['spis casów'] and row['spis casów'] != "": st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                            if row['SLOT'] and row['SLOT'] != "": st.link_button("⏰ Slot", row['SLOT'], use_container_width=True)
                        with b2:
                            if row['zdjęcie po załadunku'] and row['zdjęcie po załadunku'] != "": st.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                            if row['zrzut z currenta'] and row['zrzut z currenta'] != "": st.link_button("🖼️ Current", row['zrzut z currenta'], use_container_width=True)
                        
                        with st.expander("📝 Notatka"):
                            st.write(row['NOTATKA'] if row['NOTATKA'] else "Brak")
                st.markdown('<hr class="truck-line">', unsafe_allow_html=True)

        # --- 6. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # DEFINICJA ZAKŁADEK
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"

        edit_trackers = {}

        # GŁÓWNA LOGIKA ZAKŁADEK
        for i, (tab, key) in enumerate(zip(tabs, ["in", "out", "empty", "slots_empties", "full"])):
            with tab:
                # A. NOWA ZAKŁADKA: SLOTY NA EMPTIES
                if key == "slots_empties":
                    st.subheader("Planowanie Slotów na Empties")
                    
                    # Pobranie przewoźników z aktualnych "EMPTIES" (czyli statusy PUSTY/EMPTIES)
                    df_empties_source = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
                    unique_carriers = sorted(df_empties_source['Przewoźnik'].unique())
                    
                    with st.form("new_slot_empties_form"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            f_data = st.date_input("DATA", value=datetime.now())
                            f_slot = st.text_input("NUMER SLOTU")
                        with c2:
                            f_godzina = st.text_input("GODZINA")
                            f_hala = st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                        with c3:
                            f_carrier = st.selectbox("PRZEWOŹNIK", unique_carriers)
                            f_status = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                        
                        submit_slot = st.form_submit_button("DODAJ SLOT", use_container_width=True)
                        
                        if submit_slot:
                            # Pobierz dane auta i kierowcy dla wybranego przewoźnika
                            carrier_info = df_empties_source[df_empties_source['Przewoźnik'] == f_carrier].iloc[0]
                            
                            new_row = {
                                "Data": str(f_data),
                                "Nr Slotu": f_slot,
                                "Godzina": f_godzina,
                                "Hala": f_hala,
                                "Przewoźnik": f_carrier,
                                "Auto": carrier_info['Auto'],
                                "Kierowca": carrier_info['Kierowca'],
                                "STATUS": f_status,
                                "Nr Proj.": "EMPTIES",
                                "Nazwa Projektu": f_status
                            }
                            
                            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            if "PODGLĄD" in new_df.columns: new_df = new_df.drop(columns=["PODGLĄD"])
                            conn.update(spreadsheet=URL, data=new_df)
                            st.success("Dodano nowy slot!")
                            st.cache_data.clear()
                            st.rerun()

                    st.divider()
                    # Podgląd aktualnych slotów Empties (filtrowanie po statusach specyficznych dla tej zakładki)
                    view_slots = df[df['STATUS'].isin(["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])]
                    st.dataframe(view_slots[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, hide_index=True)

                # B. LOGIKA DLA POZOSTAŁYCH ZAKŁADEK
                elif key != "slots_empties":
                    if key == "in":
                        mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & (~df['STATUS'].str.contains(statusy_puste, na=False, case=False)) & (~df['STATUS'].str.contains("EMPTIES|KOMORNIK", na=False))
                    elif key == "out":
                        mask = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
                    elif key == "empty":
                        mask = df['STATUS'].str.contains(statusy_puste, na=False, case=False)
                    else: mask = None

                    df_view = df[mask].copy() if mask is not None else df.copy()

                    # Specyficzny interfejs dla PUSTE TRUCKI
                    if key == "empty":
                        if not df_view.empty:
                            df_empty_grouped = df_view.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                            st.info("Lista pojazdów o statusie PUSTY lub EMPTIES.")
                            ed_p = st.data_editor(df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, key="ed_empty", 
                                                 column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"], width="large")}, hide_index=True)
                            edit_trackers["ed_empty"] = (df_empty_grouped, ed_p)
                        else: st.info("Brak pojazdów w statusie Pusty/Empties.")

                    # Standardowe widoki
                    else:
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
                            render_grouped_tiles(df_view)

        # --- 7. GLOBALNY ZAPIS ZMIAN ---
        if view_mode == "Tradycyjny" or "ed_empty" in edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ ZMIANY W TABELACH", type="primary", use_container_width=True):
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
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
