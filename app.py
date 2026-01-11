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
    # --- 3. STYLE CSS (Twoje oryginalne) ---
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
        raw_df = conn.read(spreadsheet=URL, ttl="5s").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        # --- 5. SIDEBAR (Oryginalne filtry) ---
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

        # Konfiguracje edytora (Oryginalne linki)
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Foto", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small")
        }

        # --- 6. FUNKCJA KAFELKÓW (Pełna wersja z Twojego kodu) ---
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
                            if row['spis casów']: st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                            if row['SLOT']: st.link_button("⏰ Slot", row['SLOT'], use_container_width=True)
                        with b2:
                            if row['zdjęcie po załadunku']: st.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                            if row['zrzut z currenta']: st.link_button("🖼️ Current", row['zrzut z currenta'], use_container_width=True)
                        with st.expander("📝 Notatki"):
                            st.write(f"Główna: {row['NOTATKA']}")
                            if row['NOTATKA DODATKOWA']: st.info(f"Dodatkowa: {row['NOTATKA DODATKOWA']}")
                st.markdown('<hr class="truck-line">', unsafe_allow_html=True)

        # --- 7. ZAKŁADKI ---
        st.title("🏗️ SQM Control Tower")
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"
        statusy_operacyjne = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        edit_trackers = {}
        df_puste_source = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
        unique_carriers_data = df_puste_source.groupby('Przewoźnik').agg({'Auto': 'first', 'Kierowca': 'first'}).reset_index()

        for tab, key in zip(tabs, ["in", "out", "empty", "slots", "full"]):
            with tab:
                # NOWA ZAKŁADKA: SLOTY NA EMPTIES
                if key == "slots":
                    st.subheader("Planowanie operacji Empties")
                    with st.form("new_slot_form", clear_on_submit=True):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            ns_date = st.date_input("Data", datetime.now())
                            ns_hala = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                            ns_slot = st.text_input("Numer Slotu")
                        with c2:
                            ns_time = st.text_input("Godzina")
                            ns_carrier = st.selectbox("Przewoźnik (z zakładki Puste)", [""] + unique_carriers_data['Przewoźnik'].tolist())
                            ns_status = st.selectbox("Status", statusy_operacyjne)
                        with c3:
                            ns_note = st.text_area("Notatka dodatkowa")
                            if st.form_submit_button("➕ DODAJ SLOT"):
                                if ns_carrier:
                                    info = unique_carriers_data[unique_carriers_data['Przewoźnik'] == ns_carrier].iloc[0]
                                    new_row = pd.DataFrame([{
                                        'Data': str(ns_date), 'Nr Slotu': ns_slot, 'Godzina': ns_time, 'Hala': ns_hala,
                                        'Przewoźnik': ns_carrier, 'Auto': info['Auto'], 'Kierowca': info['Kierowca'],
                                        'STATUS': ns_status, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': ns_note
                                    }])
                                    conn.update(spreadsheet=URL, data=pd.concat([df, new_row], ignore_index=True))
                                    st.cache_data.clear()
                                    st.rerun()
                                else: st.error("Wybierz przewoźnika!")

                    st.divider()
                    df_s = df[df['STATUS'].isin(statusy_operacyjne)].copy()
                    if not df_s.empty:
                        ed_s = st.data_editor(df_s[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA DODATKOWA']], use_container_width=True, key="ed_slots", hide_index=True)
                        edit_trackers["ed_slots"] = (df_s, ed_s)

                # PUSTE TRUCKI
                elif key == "empty":
                    df_p = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)].copy()
                    if not df_p.empty:
                        df_p_g = df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                        ed_e = st.data_editor(df_p_g[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, key="ed_empty", hide_index=True)
                        edit_trackers["ed_empty"] = (df_p_g, ed_e)

                # POZOSTAŁE (MONTAŻE, ROZŁADOWANE, BAZA)
                else:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if key == "in":
                            d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                            all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")

                    mask = None
                    if key == "in":
                        mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False)) & (~df['STATUS'].str.contains(statusy_puste, na=False)) & (~df['STATUS'].isin(statusy_operacyjne))
                    elif key == "out":
                        mask = df['STATUS'].str.contains(statusy_rozladowane, na=False)
                    
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

        # --- 8. ZAPIS GLOBALNY ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY W TABELACH", type="primary", use_container_width=True):
            final_df = df.copy()
            for k, (orig_df, edited_df) in edit_trackers.items():
                changes = st.session_state[k].get("edited_rows", {})
                for r_idx, col_ch in changes.items():
                    real_idx = orig_df.index[int(r_idx)]
                    if k == "ed_empty" and "STATUS" in col_ch:
                        final_df.loc[final_df['Auto'] == orig_df.iloc[int(r_idx)]['Auto'], 'STATUS'] = col_ch["STATUS"]
                    else:
                        for col, val in col_ch.items(): final_df.at[real_idx, col] = val
            
            conn.update(spreadsheet=URL, data=final_df.drop(columns=["PODGLĄD"]) if "PODGLĄD" in final_df.columns else final_df)
            st.cache_data.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
