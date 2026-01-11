import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")

# --- 2. AUTORYZACJA ---
controller = CookieController()
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

def check_password():
    saved_auth = controller.get("sqm_login_key")
    if saved_auth == "Czaman2026" or st.session_state["password_correct"]:
        return True
    st.title("🏗️ SQM Logistics - Control Tower")
    pwd = st.text_input("Hasło dostępu:", type="password")
    if pwd == "Czaman2026":
        st.session_state["password_correct"] = True
        controller.set("sqm_login_key", "Czaman2026", max_age=3600*24*30)
        st.rerun()
    return False

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
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        # Metryki
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len([a for a in p_fiz if a and a != '']))

        # --- SIDEBAR (Filtry i Widok) ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            st.divider()
            f_hala = st.multiselect("Filtruj Halę:", options=sorted(df['Hala'].unique()))
            f_status = st.multiselect("Filtruj Status:", options=sorted(df['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.session_state["password_correct"] = False
                st.rerun()

        # Listy wyborów
        carriers_list = sorted([c for c in df['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 5. FUNKCJA KAFELKÓW ---
        def render_tiles(dataframe):
            dff = dataframe.copy()
            if f_hala: dff = dff[dff['Hala'].isin(f_hala)]
            if f_status: dff = dff[dff['STATUS'].isin(f_status)]
            
            for truck in dff['Auto'].unique():
                t_data = dff[dff['Auto'] == truck]
                st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                cols = st.columns(3)
                for i, (_, row) in enumerate(t_data.iterrows()):
                    with cols[i % 3]:
                        s = str(row['STATUS']).upper()
                        c = "status-trasie" if "TRASIE" in s else "status-rampa" if "RAMP" in s else "status-rozladowany" if "ROZŁADOWANY" in s else "status-empties" if "EMPTIES" in s else "status-zaladowany" if "ZAŁADOWANY" in s else "status-pusty"
                        st.markdown(f'<div class="transport-card {c}"><b>[{row["Nr Proj."]}] {row["Nazwa Projektu"]}</b><br>📍 {row["Hala"]} | {row["Godzina"]}<br><b>{row["STATUS"]}</b></div>', unsafe_allow_html=True)
                        if row['spis casów']: st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                        with st.expander("📝 Notatki"):
                            st.write(f"Główna: {row['NOTATKA']}")
                            st.write(f"Dodatkowa: {row['NOTATKA DODATKOWA']}")

        # --- 6. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        edit_trackers = {}

        # SLOTY NA EMPTIES
        with tabs[3]:
            with st.form("f_emp"):
                c1, c2, c3 = st.columns(3)
                with c1: nd, nh, ns = st.date_input("Data"), st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"]), st.text_input("Slot")
                with c2: nt, np_f = st.text_input("Godzina"), st.selectbox("Przewoźnik", [""] + carriers_list)
                with c3: nst, nn = st.selectbox("Status", empties_ops), st.text_area("Notatka")
                if st.form_submit_button("💾 DODAJ SLOT"):
                    fr = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                    nr = pd.DataFrame([{'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 'Przewoźnik': np_f, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': nn}])
                    conn.update(spreadsheet=URL, data=pd.concat([fr, nr], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

            st.divider()
            df_s = df[df['STATUS'].isin(empties_ops)].copy()
            if not df_s.empty:
                df_s.insert(0, "USUŃ", False)
                ed_s = st.data_editor(df_s[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'STATUS', 'NOTATKA DODATKOWA']], use_container_width=True, hide_index=True, column_config={"USUŃ": st.column_config.CheckboxColumn("🗑️"), "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list)})
                edit_trackers["empties"] = (df_s, ed_s)

        # MONTAŻE (0), ROZŁADOWANE (1), BAZA (4)
        for t_idx, m_filt, key in [(0, (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops)), "in"), (1, df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False), "out"), (4, None, "all")]:
            with tabs[t_idx]:
                df_v = df[m_filt].copy() if m_filt is not None else df.copy()
                src = st.text_input("🔍 Szukaj:", key=f"src_{key}")
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]
                
                if view_mode == "Tradycyjny":
                    df_v.insert(0, "USUŃ", False)
                    df_v.insert(1, "PODGLĄD", False)
                    ed = st.data_editor(df_v, use_container_width=True, hide_index=True, column_config={
                        "USUŃ": st.column_config.CheckboxColumn("🗑️"), "PODGLĄD": st.column_config.CheckboxColumn("👁️"),
                        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options + empties_ops),
                        "NOTATKA DODATKOWA": None
                    })
                    edit_trackers[key] = (df_v, ed)
                    sel = ed[ed["PODGLĄD"] == True]
                    if not sel.empty:
                        st.info(f"📝 {sel.iloc[-1]['NOTATKA']} | 💡 {sel.iloc[-1]['NOTATKA DODATKOWA']}")
                else: render_tiles(df_v)

        with tabs[2]: # PUSTE
            df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            st.data_editor(df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'STATUS': 'first'}).reset_index(), use_container_width=True, hide_index=True)

        # --- 7. GLOBALNY ZAPIS ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
            to_del = []
            for k, (orig, edit) in edit_trackers.items():
                for i in range(len(edit)):
                    idx = orig.index[i]
                    if edit.iloc[i]["USUŃ"]: to_del.append(idx)
                    else:
                        for col in edit.columns:
                            if col in db.columns: db.at[idx, col] = edit.iloc[i][col]
            db = db.drop(to_del)
            conn.update(spreadsheet=URL, data=db[all_cols])
            st.cache_data.clear()
            st.rerun()

    except Exception as e: st.error(f"Błąd: {e}")
