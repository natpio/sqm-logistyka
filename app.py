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
        # Odczyt danych z niskim TTL dla lepszej responsywności
        df = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
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
                st.subheader("🔍 Filtry")
                f_hala = st.multiselect("Hala:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Status:", options=sorted(df['STATUS'].unique()))
                f_carrier = st.multiselect("Przewoźnik:", options=sorted(df['Przewoźnik'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # --- 6. FUNKCJA KAFELKÓW ---
        def render_tiles(dataframe):
            dff = dataframe.copy()
            if view_mode == "Kafelkowy":
                if f_hala: dff = dff[dff['Hala'].isin(f_hala)]
                if f_status: dff = dff[dff['STATUS'].isin(f_status)]
                if 'f_carrier' in locals() and f_carrier: dff = dff[dff['Przewoźnik'].isin(f_carrier)]

            for truck in dff['Auto'].unique():
                t_data = dff[dff['Auto'] == truck]
                st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                cols = st.columns(3)
                for i, (_, row) in enumerate(t_data.iterrows()):
                    with cols[i % 3]:
                        s = str(row['STATUS']).upper()
                        c = "status-trasie" if "TRASIE" in s else "status-rampa" if "RAMP" in s else "status-rozladowany" if "ROZŁADOWANY" in s else "status-empties" if "EMPTIES" in s else "status-zaladowany" if "ZAŁADOWANY" in s else "status-pusty"
                        st.markdown(f'<div class="transport-card {c}"><b>{row["Data"]} | {row["Nr Slotu"]}</b><br><span style="color:#1f77b4">[{row["Nr Proj."]}] {row["Nazwa Projektu"]}</span><br>📍 {row["Hala"]} | {row["Godzina"]}<br><div style="text-align:center; background:#eee; margin-top:5px; padding:2px; font-size:0.8em"><b>{row["STATUS"]}</b></div></div>', unsafe_allow_html=True)
                        b1, b2 = st.columns(2)
                        with b1:
                            if row['spis casów']: st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                            if row['SLOT']: st.link_button("⏰ Slot", row['SLOT'], use_container_width=True)
                        with b2:
                            if row['zdjęcie po załadunku']: st.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                            if row['zrzut z currenta']: st.link_button("🖼️ Curr", row['zrzut z currenta'], use_container_width=True)

        # --- 7. ZAKŁADKI ---
        t1, t2, t3, t4, t5 = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        
        st_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]
        edit_trackers = {}

        # Słownik aut z "pustych"
        df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        p_data = df_p.groupby('Przewoźnik').agg({'Auto': 'first', 'Kierowca': 'first'}).reset_index()

        # --- ZAKŁADKA 4: SLOTY NA EMPTIES (POPRAWIONA) ---
        with t4:
            st.subheader("Nowy slot operacyjny")
            with st.form("form_empties", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    d_d = st.date_input("Data", datetime.now())
                    d_h = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                    d_s = st.text_input("Nr Slotu")
                with c2:
                    d_t = st.text_input("Godzina")
                    d_p = st.selectbox("Przewoźnik", [""] + p_data['Przewoźnik'].tolist())
                    d_st = st.selectbox("Status", st_ops)
                with c3:
                    d_n = st.text_area("Notatka dodatkowa")
                    btn_add = st.form_submit_button("💾 DODAJ I ZAPISZ SLOT")

                if btn_add:
                    if d_p:
                        # Pobieramy najnowsze dane tuż przed zapisem
                        current_df = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        info = p_data[p_data['Przewoźnik'] == d_p].iloc[0]
                        new_row = {
                            'Data': str(d_d), 'Nr Slotu': d_s, 'Godzina': d_t, 'Hala': d_h,
                            'Przewoźnik': d_p, 'Auto': info['Auto'], 'Kierowca': info['Kierowca'],
                            'STATUS': d_st, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': d_n
                        }
                        updated_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
                        conn.update(spreadsheet=URL, data=updated_df)
                        st.cache_data.clear()
                        st.success("Slot dodany pomyślnie!")
                        st.rerun()
                    else: st.error("Wybierz przewoźnika!")

            st.divider()
            df_s_view = df[df['STATUS'].isin(st_ops)].copy()
            if not df_s_view.empty:
                ed_s = st.data_editor(df_s_view[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA DODATKOWA']], use_container_width=True, key="ed_s", hide_index=True)
                edit_trackers["ed_s"] = (df_s_view, ed_s)

        # --- ZAKŁADKA 3: PUSTE TRUCKI ---
        with t3:
            df_e = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_e.empty:
                df_e_g = df_e.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                ed_e = st.data_editor(df_e_g, use_container_width=True, key="ed_e", hide_index=True)
                edit_trackers["ed_e"] = (df_e_g, ed_e)

        # --- ZAKŁADKA 1, 2, 5 ---
        for tab, key in zip([t1, t2, t5], ["in", "out", "all"]):
            with tab:
                search = st.text_input("🔍 Szukaj:", key=f"src_{key}")
                if key == "in": m = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(st_ops))
                elif key == "out": m = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False)
                else: m = None
                
                df_v = df[m].copy() if m is not None else df.copy()
                if search: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
                
                if view_mode == "Tradycyjny":
                    ed = st.data_editor(df_v, use_container_width=True, key=f"ed_{key}", column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"])})
                    edit_trackers[f"ed_{key}"] = (df_v, ed)
                else: render_tiles(df_v)

        # --- 8. ZAPIS GLOBALNY ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY W TABELACH", type="primary", use_container_width=True):
            f_df = df.copy()
            for k, (o_df, e_df) in edit_trackers.items():
                ch = st.session_state[k].get("edited_rows", {})
                for r_idx, col_v in ch.items():
                    ridx = o_df.index[int(r_idx)]
                    if k == "ed_e" and "STATUS" in col_v:
                        f_df.loc[f_df['Auto'] == o_df.iloc[int(r_idx)]['Auto'], 'STATUS'] = col_v["STATUS"]
                    else:
                        for col, val in col_v.items(): f_df.at[ridx, col] = val
            if "PODGLĄD" in f_df.columns: f_df = f_df.drop(columns=["PODGLĄD"])
            conn.update(spreadsheet=URL, data=f_df)
            st.cache_data.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
