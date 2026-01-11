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

# --- 2. AUTORYZACJA (Cookie Controller) ---
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
        st.error("😕 Błędne hasło. Spróbuj ponownie.")
        return False
    else:
        return True

if check_password():
    # --- 3. STYLE CSS (Pełny zestaw) ---
    st.markdown("""
        <style>
        .main { background-color: #f5f7f9; }
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
            font-size: 1.1em;
        }
        .transport-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 18px;
            margin-bottom: 12px;
            border-left: 10px solid #ccc;
            transition: transform 0.2s;
        }
        .transport-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
        
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #e0e0e0;
            border-radius: 5px 5px 0 0;
            padding: 10px 20px;
        }
        .stTabs [aria-selected="true"] { background-color: #2c3e50 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df_raw = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        for col in all_cols:
            if col not in df_raw.columns:
                df_raw[col] = ""
        
        df_raw = df_raw.astype(str).replace('nan', '')

        # --- 5. WYBÓR DNIA (Widok Kalendarza) ---
        c_top1, c_top2 = st.columns([2, 1])
        with c_top1:
            st.title("🏗️ SQM Logistics - Control Tower")
        with c_top2:
            # Wybór dnia filtrujący całą aplikację
            selected_date = st.date_input("📅 Wybierz dzień operacyjny:", datetime.now())
        
        # Filtrujemy bazę do wybranego dnia (z zachowaniem dostępu do całości w zakładce Baza)
        df_day = df_raw[df_raw['Data'] == str(selected_date)].copy()

        # --- 6. SIDEBAR ---
        with st.sidebar:
            st.image("https://sqm.pl/wp-content/uploads/2021/03/logo-sqm.png", width=150)
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Widok danych:", ["Tradycyjny (Tabela)", "Kafelkowy (Operacyjny)"])
            st.divider()
            st.subheader("🔍 Filtry dodatkowe")
            f_hala = st.multiselect("Hala:", options=sorted(df_raw['Hala'].unique()))
            f_status = st.multiselect("Status:", options=sorted(df_raw['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Aplikowanie filtrów bocznych
        if f_hala: df_day = df_day[df_day['Hala'].isin(f_hala)]
        if f_status: df_day = df_day[df_day['STATUS'].isin(f_status)]

        # --- 7. METRYKI (Dla wybranego dnia) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df_day[df_day['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df_day[df_day['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df_day[df_day['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df_day[df_day['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len([a for a in p_fiz if a and a != '']))

        # Słowniki pomocnicze
        carriers_list = sorted([c for c in df_raw['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 8. KONFIGURACJA KOLUMN ---
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

        # --- 9. ZAKŁADKI ---
        t1, t2, t3, t4, t5 = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA (CAŁA)"])
        edit_trackers = {}

        # MONTAŻE (T1), ROZŁADOWANE (T2), BAZA (T5)
        for tab, key, m_filter, is_full_base in zip([t1, t2, t5], ["in", "out", "all"], [
            (~df_day['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df_day['STATUS'].isin(empties_ops)),
            df_day['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False),
            None
        ], [False, False, True]):
            with tab:
                src = st.text_input("🔍 Szukaj (Nr Proj / Auto / Klient):", key=f"s_{key}")
                data_to_show = df_raw.copy() if is_full_base else df_day[m_filter].copy()
                
                if src:
                    data_to_show = data_to_show[data_to_show.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                if view_mode == "Tradycyjny (Tabela)":
                    data_to_show.insert(0, "USUŃ", False)
                    data_to_show.insert(data_to_show.columns.get_loc("NOTATKA") + 1, "PODGLĄD", False)
                    
                    ed = st.data_editor(data_to_show, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=column_cfg)
                    edit_trackers[key] = (data_to_show, ed)
                    
                    sel = ed[ed["PODGLĄD"] == True]
                    if not sel.empty:
                        r = sel.iloc[-1]
                        st.info(f"📝 **Notatka:** {r['NOTATKA']}")
                        if r['NOTATKA DODATKOWA']: st.warning(f"💡 **Dodatkowa:** {r['NOTATKA DODATKOWA']}")
                else:
                    # KAFELKOWY
                    for truck in data_to_show['Auto'].unique():
                        t_data = data_to_show[data_to_show['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for idx_c, (_, r) in enumerate(t_data.iterrows()):
                            with cols[idx_c % 3]:
                                s_val = str(r['STATUS']).upper()
                                c_class = "status-trasie" if "TRASIE" in s_val else "status-rampa" if "RAMP" in s_val else "status-rozladowany" if "ROZŁADOWANY" in s_val else "status-empties" if "EMPTIES" in s_val else "status-zaladowany" if "ZAŁADOWANY" in s_val else "status-pusty"
                                st.markdown(f"""<div class="transport-card {c_class}">
                                    <b>[{r['Nr Proj.']}] {r['Nazwa Projektu']}</b><br>
                                    📍 {r['Hala']} | ⏰ {r['Godzina']}<br>
                                    Status: <b>{r['STATUS']}</b>
                                </div>""", unsafe_allow_html=True)
                                if r['spis casów']: st.link_button("📋 Spis Casów", r['spis casów'], use_container_width=True)

        with t3: # PUSTE
            df_p = df_day[df_day['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_p.empty:
                st.dataframe(df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index(), use_container_width=True, hide_index=True)

        with t4: # SLOTY EMPTIES
            st.subheader("Nowa operacja Empties")
            with st.form("f_emp_full", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1: 
                    nd = st.date_input("Data", selected_date)
                    nh = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c2:
                    nt = st.text_input("Godzina")
                    np = st.selectbox("Przewoźnik", [""] + carriers_list)
                with c3:
                    nst = st.selectbox("Status", empties_ops)
                    nn = st.text_area("Notatka")
                if st.form_submit_button("💾 DODAJ DO PLANU"):
                    db_fresh = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                    new_r = pd.DataFrame([{'Data': str(nd), 'Hala': nh, 'Godzina': nt, 'Przewoźnik': np, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': nn}])
                    conn.update(spreadsheet=URL, data=pd.concat([db_fresh, new_r], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

            st.divider()
            df_e_v = df_day[df_day['STATUS'].isin(empties_ops)].copy()
            if not df_e_v.empty:
                df_e_v.insert(0, "USUŃ", False)
                ed_e = st.data_editor(df_e_v[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'STATUS', 'NOTATKA DODATKOWA']], 
                                      use_container_width=True, hide_index=True, key="ed_e_full",
                                      column_config={"USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"), "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list)})
                edit_trackers["empties"] = (df_e_v, ed_e)

        # --- 10. GLOBALNY ZAPIS I USUWANIE (Prawidłowa Logika) ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            f_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
            to_delete_idx = []
            
            for k, (orig_df, edited_df) in edit_trackers.items():
                for i in range(len(edited_df)):
                    real_index = orig_df.index[i]
                    if edited_df.iloc[i]["USUŃ"]:
                        to_delete_idx.append(real_index)
                    else:
                        for col in edited_df.columns:
                            if col in f_db.columns:
                                f_db.at[real_index, col] = edited_df.iloc[i][col]
            
            if to_delete_idx:
                f_db = f_db.drop(to_delete_idx)
            
            conn.update(spreadsheet=URL, data=f_db[all_cols])
            st.cache_data.clear()
            st.success(f"Zapisano zmiany. Usunięto {len(to_delete_idx)} rekordów.")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Wystąpił błąd krytyczny: {e}")
