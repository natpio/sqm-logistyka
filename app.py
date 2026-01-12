import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA I AUTH ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")
controller = CookieController()

def check_password():
    if controller.get("sqm_login_key") == "Czaman2026": return True
    if "password_correct" not in st.session_state:
        st.title("🏗️ SQM Logistics - Control Tower")
        pwd = st.text_input("Hasło dostępu:", type="password")
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
        .truck-separator { background-color: #2c3e50; color: white; padding: 10px 20px; border-radius: 8px; margin: 20px 0 10px 0; font-weight: bold; }
        .transport-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 10px; border-left: 8px solid #ccc; }
        .status-trasie { border-left-color: #ffeb3b; } .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; } .status-zaladowany { border-left-color: #2196f3; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. POŁĄCZENIE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="5s").dropna(how="all").reset_index(drop=True)
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')
        df["PODGLĄD"] = False

        # --- 4. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            f_hala, f_status = [], []
            if view_mode == "Kafelkowy":
                st.divider()
                f_hala = st.multiselect("Hala:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Status:", options=sorted(df['STATUS'].unique()))
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # --- 5. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        p_df = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        m4.metric("PUSTE TRUCKI ⚪", p_df['Auto'].nunique())

        # --- 6. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📚 BAZA"])
        edit_trackers = {}

        for tab, key in zip(tabs, ["in", "out", "empty", "full"]):
            with tab:
                if key == "in": mask = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False, case=False))
                elif key == "out": mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty": mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                else: mask = None

                df_v = df[mask].copy() if mask is not None else df.copy()

                if key == "empty":
                    df_v = df_v.groupby('Auto').agg({'Przewoźnik':'first','Kierowca':'first','STATUS':'first'}).reset_index()[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']]
                else:
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        # KALENDARZ I FILTR DATY
                        show_all = st.checkbox("Wszystkie dni", value=True, key=f"all_{key}")
                        if not show_all:
                            target_date = st.date_input("Wybierz datę z kalendarza:", value=datetime.now(), key=f"date_{key}")
                            df_v = df_v[df_v['Data'].astype(str).str.contains(str(target_date))]
                    with c2:
                        src = st.text_input("🔍 Szukaj:", key=f"src_{key}")
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
                    if "PODGLĄD" in ed.columns and not ed[ed["PODGLĄD"] == True].empty:
                        st.info(f"**Notatka:** {ed[ed['PODGLĄD'] == True].iloc[-1]['NOTATKA']}")
                else:
                    # KAFELKI
                    dft = df_v.copy()
                    if f_hala: dft = dft[dft['Hala'].isin(f_hala)]
                    if f_status: dft = dft[dft['STATUS'].isin(f_status)]
                    for truck in dft['Auto'].unique():
                        td = dft[dft['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator">🚛 {truck} | {td.iloc[0]["Przewoźnik"]}</div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for idx, (_, r) in enumerate(td.iterrows()):
                            with cols[idx % 3]:
                                sc = "status-trasie" if "TRASIE" in r['STATUS'] else "status-rampa" if "RAMP" in r['STATUS'] else "status-rozladowany" if "ROZŁADOWANY" in r['STATUS'] else ""
                                st.markdown(f'<div class="transport-card {sc}"><b>{r["Nazwa Projektu"]}</b><br>📍 {r["Hala"]} | {r["Godzina"]}<br><small>{r["STATUS"]}</small></div>', unsafe_allow_html=True)

        # --- 7. ZAPIS ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            f_df = df.copy()
            to_del = []
            for k, (o_p, e_p) in edit_trackers.items():
                ch = st.session_state[k].get("edited_rows", {})
                for r_idx, cols in ch.items():
                    ri = int(r_idx)
                    if k == "ed_empty":
                        f_df.loc[f_df['Auto'] == o_p.iloc[ri]['Auto'], 'STATUS'] = cols.get("STATUS")
                    else:
                        real_idx = o_p.index[ri]
                        if cols.get("USUŃ"): to_del.append(real_idx)
                        else:
                            for c, v in cols.items():
                                if c not in ["LP", "USUŃ", "PODGLĄD"]: f_df.at[real_idx, c] = v
            if to_del: f_df = f_df.drop(to_del)
            conn.update(spreadsheet=URL, data=f_df.drop(columns=["LP","USUŃ","PODGLĄD"], errors='ignore'))
            st.cache_data.clear()
            st.success("Zapisano!"); time.sleep(1); st.rerun()
    except Exception as e: st.error(f"Błąd: {e}")
