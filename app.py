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
    # --- 3. STYLE CSS (Pełne i oryginalne) ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .truck-separator {
            background-color: #2c3e50; color: white; padding: 10px 20px; border-radius: 8px;
            margin: 30px 0 15px 0; display: flex; justify-content: space-between; align-items: center;
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
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
        hr.truck-line { border: 0; height: 2px; background-image: linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,0.75), rgba(0,0,0,0)); margin-top: 40px; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        # Bardzo niski TTL, aby uniknąć konfliktów przy dodawaniu
        df = conn.read(spreadsheet=URL, ttl="1s").dropna(how="all")
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        # --- 5. SIDEBAR (Pełne filtry) ---
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

        # Konfiguracja kolumn z linkami
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Foto", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small")
        }

        # --- 6. FUNKCJA KAFELKÓW (Pełne funkcje przycisków) ---
        def render_grouped_tiles(dataframe):
            dff = dataframe.copy()
            if view_mode == "Kafelkowy":
                if f_hala: dff = dff[dff['Hala'].isin(f_hala)]
                if f_status: dff = dff[dff['STATUS'].isin(f_status)]
                if 'f_carrier' in locals() and f_carrier: dff = dff[dff['Przewoźnik'].isin(f_carrier)]

            if dff.empty:
                st.info("Brak danych.")
                return
            
            for truck in dff['Auto'].unique():
                truck_data = dff[dff['Auto'] == truck]
                st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{truck_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                t_cols = st.columns(3)
                for idx, (_, row) in enumerate(truck_data.iterrows()):
                    with t_cols[idx % 3]:
                        s = str(row['STATUS']).upper()
                        s_class = "status-trasie" if "TRASIE" in s else "status-rampa" if "RAMP" in s else "status-rozladowany" if "ROZŁADOWANY" in s else "status-empties" if "EMPTIES" in s else "status-zaladowany" if "ZAŁADOWANY" in s else "status-pusty"
                        
                        st.markdown(f"""
                            <div class="transport-card {s_class}">
                                <div style="font-size: 0.8em; color: #666;">{row['Data']} | {row['Nr Slotu']}</div>
                                <div style="font-weight: bold; color: #1f77b4;">[{row['Nr Proj.']}] {row['Nazwa Projektu']}</div>
                                <div style="font-size: 0.9em;">👤 {row['Kierowca']}<br>📍 {row['Hala']} | {row['Godzina']}</div>
                                <div style="text-align: center; background: #eee; border-radius: 4px; padding: 2px; font-size: 0.85em; margin-top:5px;"><b>{row['STATUS']}</b></div>
                            </div>
                        """, unsafe_allow_html=True)
                        b1, b2 = st.columns(2)
                        with b1:
                            if row['spis casów']: st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                            if row['SLOT']: st.link_button("⏰ Slot", row['SLOT'], use_container_width=True)
                        with b2:
                            if row['zdjęcie po załadunku']: st.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                            if row['zrzut z currenta']: st.link_button("🖼️ Curr", row['zrzut z currenta'], use_container_width=True)
                        with st.expander("📝 Notatki"):
                            st.write(f"**Główna:** {row['NOTATKA']}")
                            if row['NOTATKA DODATKOWA']: st.info(f"**Dodatkowa:** {row['NOTATKA DODATKOWA']}")
                st.markdown('<hr class="truck-line">', unsafe_allow_html=True)

        # --- 7. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"
        statusy_operacyjne = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        edit_trackers = {}
        df_p_source = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
        p_data = df_p_source.groupby('Przewoźnik').agg({'Auto': 'first', 'Kierowca': 'first'}).reset_index()

        for tab, key in zip(tabs, ["in", "out", "empty", "slots", "full"]):
            with tab:
                if key == "slots":
                    st.subheader("Planowanie operacji na puste skrzynie")
                    # FORMULARZ Z WYMUSZONYM ZAPISEM
                    with st.form("add_empties_form", clear_on_submit=True):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            f_d = st.date_input("Data operacji", datetime.now())
                            f_h = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                            f_s = st.text_input("Numer Slotu")
                        with c2:
                            f_t = st.text_input("Godzina")
                            f_p = st.selectbox("Przewoźnik (z zakładki Puste)", [""] + p_data['Przewoźnik'].tolist())
                            f_st = st.selectbox("Status operacji", statusy_operacyjne)
                        with c3:
                            f_n = st.text_area("Notatka dodatkowa")
                            submitted = st.form_submit_button("💾 DODAJ SLOT DO BAZY")

                        if submitted:
                            if f_p:
                                # POBIERAMY ŚWIEŻE DANE PRZED ZŁĄCZENIEM
                                current_all = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                                carrier_info = p_data[p_data['Przewoźnik'] == f_p].iloc[0]
                                
                                new_entry = pd.DataFrame([{
                                    'Data': str(f_d), 'Nr Slotu': f_s, 'Godzina': f_t, 'Hala': f_h,
                                    'Przewoźnik': f_p, 'Auto': carrier_info['Auto'], 'Kierowca': carrier_info['Kierowca'],
                                    'STATUS': f_st, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': f_n
                                }])
                                
                                final_to_save = pd.concat([current_all, new_entry], ignore_index=True)
                                # CZYSZCZENIE KOLUMN PRZED ZAPISEM
                                if "PODGLĄD" in final_to_save.columns: final_to_save = final_to_save.drop(columns=["PODGLĄD"])
                                
                                conn.update(spreadsheet=URL, data=final_all_cols_save(final_to_save, all_cols))
                                st.cache_data.clear()
                                st.success("Pomyślnie dodano i zapisano w arkuszu!")
                                st.rerun()
                            else: st.error("Musisz wybrać przewoźnika!")

                    st.divider()
                    df_slots_view = df[df['STATUS'].isin(statusy_operacyjne)].copy()
                    if not df_slots_view.empty:
                        ed_s = st.data_editor(df_slots_view[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA DODATKOWA']], use_container_width=True, key="ed_slots", hide_index=True)
                        edit_trackers["ed_slots"] = (df_slots_view, ed_s)

                elif key == "empty":
                    df_e = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)].copy()
                    if not df_e.empty:
                        df_e_g = df_e.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                        ed_e = st.data_editor(df_e_g, use_container_width=True, key="ed_empty", hide_index=True)
                        edit_trackers["ed_empty"] = (df_e_g, ed_e)

                else:
                    c1, c2 = st.columns([1.5, 2])
                    with c1:
                        if key == "in":
                            d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                            all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj ładunku:", key=f"s_{key}")

                    mask = None
                    if key == "in": mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False)) & (~df['STATUS'].str.contains(statusy_puste, na=False)) & (~df['STATUS'].isin(statusy_operacyjne))
                    elif key == "out": mask = df['STATUS'].str.contains(statusy_rozladowane, na=False)
                    
                    df_v = df[mask].copy() if mask is not None else df.copy()
                    if key == "in" and not all_d:
                        df_v = df_v[pd.to_datetime(df_v['Data'], errors='coerce').dt.date == d_val]
                    if search:
                        df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                    if view_mode == "Tradycyjny":
                        ed = st.data_editor(df_v, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main)
                        edit_trackers[f"ed_{key}"] = (df_v, ed)
                        sel = ed[ed["PODGLĄD"] == True]
                        if not sel.empty:
                            r = sel.iloc[-1]
                            st.info(f"**[{r['Nr Proj.']}] {r['Nazwa Projektu']}**\n\n{r['NOTATKA']}\n\n*Dodatkowa:* {r['NOTATKA DODATKOWA']}")
                    else:
                        render_grouped_tiles(df_v)

        # FUNKCJA POMOCNICZA DO ZACHOWANIA KOLUMN
        def final_all_cols_save(dataframe, cols):
            for col in cols:
                if col not in dataframe.columns: dataframe[col] = ""
            return dataframe[cols]

        # --- 8. ZAPIS GLOBALNY ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY W TABELACH", type="primary", use_container_width=True):
            f_df = df.copy()
            for k, (o_df, e_df) in edit_trackers.items():
                changes = st.session_state[k].get("edited_rows", {})
                for r_idx, col_v in changes.items():
                    ridx = o_df.index[int(r_idx)]
                    if k == "ed_empty" and "STATUS" in col_v:
                        f_df.loc[f_df['Auto'] == o_df.iloc[int(r_idx)]['Auto'], 'STATUS'] = col_v["STATUS"]
                    else:
                        for col, val in col_v.items(): f_df.at[ridx, col] = val
            
            conn.update(spreadsheet=URL, data=final_all_cols_save(f_df, all_cols))
            st.cache_data.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")
