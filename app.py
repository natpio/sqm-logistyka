import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")
controller = CookieController()

def check_password():
    if controller.get("sqm_login_key") == "Czaman2026":
        return True
    if "password_correct" not in st.session_state:
        st.title("🏗️ SQM Logistics - Control Tower")
        pwd = st.text_input("Hasło:", type="password", key="pwd_input")
        if pwd == "Czaman2026":
            st.session_state["password_correct"] = True
            controller.set("sqm_login_key", "Czaman2026", max_age=3600*24*30)
            st.rerun()
        return False
    return True

if check_password():
    # --- 2. STYLE CSS ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .truck-separator { background-color: #2c3e50; color: white; padding: 10px; border-radius: 8px; margin: 20px 0 10px 0; font-weight: bold; }
        .transport-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 10px; padding: 12px; margin-bottom: 10px; border-left: 8px solid #ccc; }
        .status-trasie { border-left-color: #ffeb3b; } .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; } .status-zaladowany { border-left-color: #2196f3; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="5s").dropna(how="all").reset_index(drop=True)
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')
        df["PODGLĄD"] = False

        # --- 4. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Menu")
            view_mode = st.radio("Widok:", ["Tradycyjny", "Kafelkowy"])
            f_hala = st.multiselect("Hala:", sorted(df['Hala'].unique())) if view_mode == "Kafelkowy" else []
            f_stat = st.multiselect("Status:", sorted(df['STATUS'].unique())) if view_mode == "Kafelkowy" else []
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # --- 5. METRYKI ---
        st.title("🏗️ SQM Control Tower")
        puste_q = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        m4.metric("PUSTE TRUCKI ⚪", puste_q['Auto'].nunique())

        # --- 6. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📚 BAZA"])
        edit_trackers = {}

        for tab, key in zip(tabs, ["in", "out", "empty", "full"]):
            with tab:
                if key == "in": mask = ~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False, case=False)
                elif key == "out": mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty": mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                else: mask = None
                
                df_v = df[mask].copy() if mask is not None else df.copy()

                if key == "empty":
                    df_v = df_v.groupby('Auto').agg({'Przewoźnik':'first','Kierowca':'first','STATUS':'first'}).reset_index()
                    df_v = df_v[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']]
                else:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if not st.checkbox("Wszystkie dni", True, key=f"a_{key}"):
                            df_v = df_v[df_v['Data'] == str(st.date_input("Dzień", datetime.now(), key=f"d_{key}"))]
                    with c2:
                        src = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                        if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                df_v.insert(0, "LP", range(1, len(df_v) + 1))
                if key != "empty": df_v.insert(1, "USUŃ", False)

                if view_mode == "Tradycyjny":
                    cfg = {"LP": st.column_config.NumberColumn("LP", width="small", disabled=True),
                           "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                           "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                           "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"])}
                    ed = st.data_editor(df_v, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=cfg)
                    edit_trackers[f"ed_{key}"] = (df_v, ed)
                    if not ed[ed["PODGLĄD"] == True].empty:
                        st.info(f"Notatka: {ed[ed['PODGLĄD'] == True].iloc[-1]['NOTATKA']}")
                else:
                    # Rendering kafelków
                    dff_tile = df_v.copy()
                    if f_hala: dff_tile = dff_tile[dff_tile['Hala'].isin(f_hala)]
                    if f_stat: dff_tile = dff_tile[dff_tile['STATUS'].isin(f_stat)]
                    for truck in dff_tile['Auto'].unique():
                        t_data = dff_tile[dff_tile['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator">🚛 {truck} | {t_data.iloc[0]["Przewoźnik"]}</div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for idx, (_, r) in enumerate(t_data.iterrows()):
                            with cols[idx % 3]:
                                s_c = "status-trasie" if "TRASIE" in r['STATUS'] else "status-rampa" if "RAMP" in r['STATUS'] else "status-rozladowany" if "ROZŁADOWANY" in r['STATUS'] else ""
                                st.markdown(f'<div class="transport-card {s_c}"><b>{r["Nazwa Projektu"]}</b><br>{r["Hala"]} | {r["Godzina"]}<br>{r["STATUS"]}</div>', unsafe_allow_html=True)

        # --- 7. ZAPIS ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
            final_df = df.copy()
            for k, (orig_p, ed_p) in edit_trackers.items():
                ch = st.session_state[k].get("edited_rows", {})
                for r_idx, cols in ch.items():
                    r_int = int(r_idx)
                    if k == "ed_empty":
                        final_df.loc[final_df['Auto'] == orig_p.iloc[r_int]['Auto'], 'STATUS'] = cols.get("STATUS")
                    else:
                        real_idx = orig_p.index[r_int]
                        if cols.get("USUŃ"): final_df = final_df.drop(real_idx)
                        else:
                            for c, v in cols.items():
                                if c not in ["LP", "USUŃ", "PODGLĄD"]: final_df.at[real_idx, c] = v
            
            conn.update(spreadsheet=URL, data=final_df.drop(columns=["LP","USUŃ","PODGLĄD"], errors='ignore'))
            st.cache_data.clear()
            st.success("Zapisano!"); time.sleep(1); st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
