import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM CONTROL TOWER | Logistics",
    page_icon="🏗️",
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
    elif not st.session_state["password_correct"]:
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        st.error("😕 Błędne hasło")
        return False
    else:
        return True

if check_password():
    # --- 3. STYLE CSS (Twoje oryginalne, pełne) ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .truck-separator {
            background-color: #2c3e50;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            margin-top: 35px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: bold;
        }
        .transport-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 12px;
            border-left: 10px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z BAZĄ ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df_raw = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        for col in all_cols:
            if col not in df_raw.columns:
                df_raw[col] = ""
        
        df_raw = df_raw.astype(str).replace('nan', '')

        # --- 5. WIDOK KALENDARZA (Wybór dnia) ---
        st.title("🏗️ SQM Logistics - Control Tower")
        selected_date = st.date_input("📅 Wybierz dzień operacyjny:", datetime.now())
        
        # Filtrowanie główne po dacie
        df_day = df_raw[df_raw['Data'] == str(selected_date)].copy()

        # --- 6. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia widoku")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny (Tabela)", "Kafelkowy (Operacyjny)"])
            st.divider()
            f_hala = st.multiselect("Filtruj Halę:", options=sorted(df_raw['Hala'].unique()))
            f_status = st.multiselect("Filtruj Status:", options=sorted(df_raw['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        if f_hala: df_day = df_day[df_day['Hala'].isin(f_hala)]
        if f_status: df_day = df_day[df_day['STATUS'].isin(f_status)]

        # Metryki
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df_day[df_day['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df_day[df_day['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df_day[df_day['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df_day[df_day['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len([a for a in p_fiz if a and a != '']))

        # Słowniki
        carriers_list = sorted([c for c in df_raw['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 7. KONFIGURACJA KOLUMN (Linki, Checkboxy, Widoczność) ---
        column_cfg = {
            "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options + empties_ops),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Curr", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("🖼️ Dod.", display_text="Otwórz"),
            "NOTATKA DODATKOWA": None
        }

        # --- 8. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        edit_trackers = {}

        for tab, key, m_filter, is_full in zip([tabs[0], tabs[1], tabs[4]], ["in", "out", "all"], [
            (~df_day['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df_day['STATUS'].isin(empties_ops)),
            df_day['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False),
            None
        ], [False, False, True]):
            with tab:
                data = df_raw.copy() if is_full else df_day[m_filter].copy()
                src = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                if src:
                    data = data[data.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                if view_mode == "Tradycyjny (Tabela)":
                    data.insert(0, "USUŃ", False)
                    data.insert(data.columns.get_loc("NOTATKA") + 1, "PODGLĄD", False)
                    ed = st.data_editor(data, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=column_cfg)
                    edit_trackers[key] = (data, ed)
                    if not ed[ed["PODGLĄD"] == True].empty:
                        r = ed[ed["PODGLĄD"] == True].iloc[-1]
                        st.info(f"📝 {r['NOTATKA']} | 💡 {r['NOTATKA DODATKOWA']}")
                else:
                    for truck in data['Auto'].unique():
                        t_data = data[data['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator">🚛 {truck} | {t_data.iloc[0]["Przewoźnik"]}</div>', unsafe_allow_html=True)
                        for _, r in t_data.iterrows():
                            st.markdown(f'<div class="transport-card"><b>{r["Nazwa Projektu"]}</b><br>{r["Hala"]} | {r["Godzina"]} | {r["STATUS"]}</div>', unsafe_allow_html=True)

        with tabs[3]: # SLOTY EMPTIES
            with st.form("f_emp"):
                c1, c2, c3 = st.columns(3)
                with c1: nd, nh = st.date_input("Data", selected_date), st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c2: nt, np = st.text_input("Godzina"), st.selectbox("Przewoźnik", [""] + carriers_list)
                with c3: nst, nn = st.selectbox("Status", empties_ops), st.text_area("Notatka")
                if st.form_submit_button("💾 DODAJ"):
                    f_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                    nr = pd.DataFrame([{'Data': str(nd), 'Hala': nh, 'Godzina': nt, 'Przewoźnik': np, 'STATUS': nst, 'Nazwa Projektu': '--- EMPTIES ---', 'NOTATKA DODATKOWA': nn}])
                    conn.update(spreadsheet=URL, data=pd.concat([f_db, nr], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

        # --- 9. ZAPIS I USUWANIE (Prawidłowa Logika Indeksowania) ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            full_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
            to_delete = []
            for k, (orig, edit) in edit_trackers.items():
                for i in range(len(edit)):
                    idx = orig.index[i] # Pobranie oryginalnego indeksu z bazy
                    if edit.iloc[i]["USUŃ"]: to_delete.append(idx)
                    else:
                        for col in edit.columns:
                            if col in full_db.columns: full_db.at[idx, col] = edit.iloc[i][col]
            if to_delete: full_db = full_db.drop(to_delete)
            conn.update(spreadsheet=URL, data=full_db[all_cols])
            st.cache_data.clear()
            st.success("Baza zaktualizowana!")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
