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
        else:
            st.session_state["password_correct"] = False

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
        .truck-separator { background-color: #2c3e50; color: white; padding: 10px 20px; border-radius: 8px; margin-top: 30px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }
        .transport-card { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin-bottom: 10px; border-left: 8px solid #ccc; }
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
        df_raw = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        for col in all_cols:
            if col not in df_raw.columns: df_raw[col] = ""
        df_raw = df_raw.astype(str).replace('nan', '')

        # --- 5. KALENDARZ / WYBÓR DNIA (Kluczowy element) ---
        st.title("🏗️ SQM Logistics - Control Tower")
        selected_date = st.date_input("📅 Wybierz dzień operacyjny:", datetime.now())
        df = df_raw[df_raw['Data'] == str(selected_date)].copy()

        # --- 6. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Filtry widoku")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny (Tabela)", "Kafelkowy (Operacyjny)"])
            st.divider()
            f_hala = st.multiselect("Filtruj Halę:", options=sorted(df_raw['Hala'].unique()))
            f_status = st.multiselect("Filtruj Status:", options=sorted(df_raw['STATUS'].unique()))
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Dodatkowe filtrowanie (jeśli wybrano)
        if f_hala: df = df[df['Hala'].isin(f_hala)]
        if f_status: df = df[df['STATUS'].isin(f_status)]

        # Metryki (Dla wybranego dnia)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len([a for a in p_fiz if a and a != '']))

        # Słowniki
        carriers_list = sorted([c for c in df_raw['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 7. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA (CAŁOŚĆ)"])
        edit_trackers = {}

        # Logika dla zakładek (Montaże, Rozładowane, Baza)
        for i, (t_idx, key, m_filt) in enumerate([
            (0, "in", (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops))),
            (1, "out", df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False)),
            (4, "all", None) # Tu pokazujemy wszystko dla wybranego dnia lub całą bazę (w zależności od preferencji - tu: wybrany dzień)
        ]):
            with tabs[t_idx]:
                df_v = df[m_filt].copy() if m_filt is not None else (df_raw.copy() if t_idx == 4 else df.copy())
                src = st.text_input("🔍 Szukaj (Nr Proj / Auto / Klient):", key=f"src_{key}")
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                if view_mode == "Tradycyjny (Tabela)":
                    df_v.insert(0, "USUŃ", False)
                    df_v.insert(df_v.columns.get_loc("NOTATKA") + 1, "PODGLĄD", False)
                    
                    ed = st.data_editor(df_v, use_container_width=True, hide_index=True, key=f"ed_{key}",
                        column_config={
                            "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                            "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options + empties_ops),
                            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Curr", display_text="Otwórz"),
                            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                            "NOTATKA DODATKOWA": None
                        })
                    edit_trackers[key] = (df_v, ed)
                    if not ed[ed["PODGLĄD"] == True].empty:
                        r = ed[ed["PODGLĄD"] == True].iloc[-1]
                        st.info(f"📝 {r['NOTATKA']} | 💡 {r['NOTATKA DODATKOWA']}")
                else:
                    # KAFELKI
                    for truck in df_v['Auto'].unique():
                        t_data = df_v[df_v['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for idx_c, (_, r) in enumerate(t_data.iterrows()):
                            with cols[idx_c % 3]:
                                st.markdown(f'<div class="transport-card"><b>{r["Nazwa Projektu"]}</b><br>📍 {r["Hala"]} | {r["Godzina"]} | {r["STATUS"]}</div>', unsafe_allow_html=True)

        # SLOTY NA EMPTIES (T3)
        with tabs[3]:
            with st.form("f_emp"):
                c1, c2 = st.columns(2)
                with c1: nd, nh, nt = st.date_input("Data", selected_date), st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"]), st.text_input("Godzina")
                with c2: np, nst = st.selectbox("Przewoźnik", [""] + carriers_list), st.selectbox("Status", empties_ops)
                if st.form_submit_button("💾 DODAJ SLOT"):
                    db_f = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                    nr = pd.DataFrame([{'Data': str(nd), 'Hala': nh, 'Godzina': nt, 'Przewoźnik': np, 'STATUS': nst, 'Nazwa Projektu': '--- EMPTIES ---'}])
                    conn.update(spreadsheet=URL, data=pd.concat([db_f, nr], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

        # --- 8. GLOBALNY ZAPIS I USUWANIE ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            full_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
            to_del = []
            for k, (orig, edit) in edit_trackers.items():
                for i in range(len(edit)):
                    real_idx = orig.index[i]
                    if edit.iloc[i]["USUŃ"]: to_del.append(real_idx)
                    else:
                        for col in edit.columns:
                            if col in full_db.columns: full_db.at[real_idx, col] = edit.iloc[i][col]
            if to_del: full_db = full_db.drop(to_del)
            conn.update(spreadsheet=URL, data=full_db[all_cols])
            st.cache_data.clear()
            st.rerun()

    except Exception as e: st.error(f"Błąd: {e}")
