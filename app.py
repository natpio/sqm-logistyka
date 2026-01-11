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
    elif not st.session_state["password_correct"]:
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        st.error("😕 Błędne hasło")
        return False
    else:
        return True

if check_password():
    # --- 3. STYLE CSS (Pełne) ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #f8f9fb;
            border: 1px solid #e0e0e0;
            padding: 15px;
            border-radius: 10px;
        }
        .truck-separator {
            background-color: #2c3e50;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            margin-top: 30px;
            margin-bottom: 15px;
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
            background-image: linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,0.75), rgba(0,0,0,0));
            margin-top: 40px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Zapamiętywanie zakładki po rerun
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = 0

    try:
        df = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
        
        df = df.astype(str).replace('nan', '')

        # --- 5. METRYKI ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA (FIZYCZNIE)", len([a for a in p_fiz if a and a != '']))

        # --- 6. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia widoku")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny (Tabela)", "Kafelkowy (Operacyjny)"])
            st.divider()
            st.subheader("🔍 Filtry globalne")
            f_date = st.text_input("📅 Szukaj po dacie (RRRR-MM-DD):", "")
            f_hala = st.multiselect("Filtruj Halę:", options=sorted(df['Hala'].unique()))
            f_status = st.multiselect("Filtruj Status:", options=sorted(df['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Filtracja
        if f_date: df = df[df['Data'].str.contains(f_date)]
        if f_hala: df = df[df['Hala'].isin(f_hala)]
        if f_status: df = df[df['STATUS'].isin(f_status)]

        # Słowniki
        carriers_list = sorted([c for c in df['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 7. ZAKŁADKI ---
        tab_list = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"]
        tabs = st.tabs(tab_list)
        edit_trackers = {}

        # --- T4: SLOTY NA EMPTIES ---
        with tabs[3]:
            st.subheader("Planowanie operacji Empties")
            with st.form("f_empties_new", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nd = st.date_input("Data", datetime.now())
                    nh = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                    ns = st.text_input("Slot")
                with c2:
                    nt = st.text_input("Godzina")
                    np = st.selectbox("Przewoźnik", [""] + carriers_list)
                    nst = st.selectbox("Status", empties_ops)
                with c3:
                    nn = st.text_area("Notatka")
                    if st.form_submit_button("💾 DODAJ OPERACJĘ"):
                        fresh = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        nr = pd.DataFrame([{'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 'Przewoźnik': np, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': nn}])
                        conn.update(spreadsheet=URL, data=pd.concat([fresh, nr], ignore_index=True))
                        st.cache_data.clear()
                        st.session_state.active_tab = 3
                        st.rerun()

            st.divider()
            df_empties = df[df['STATUS'].isin(empties_ops)].copy()
            if not df_empties.empty:
                df_empties.insert(0, "USUŃ", False)
                ed_emp = st.data_editor(
                    df_empties[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'STATUS', 'NOTATKA DODATKOWA']],
                    use_container_width=True, hide_index=True, key="ed_empties",
                    column_config={
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list),
                        "STATUS": st.column_config.SelectboxColumn("Status", options=empties_ops)
                    }
                )
                edit_trackers["empties"] = (df_empties, ed_emp, 3)

        # --- T1, T2, T5 ---
        for i, (t_idx, k, m_filt) in enumerate([(0, "in", (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops))), 
                                               (1, "out", df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False)), 
                                               (4, "all", None)]):
            with tabs[t_idx]:
                src = st.text_input("🔍 Szukaj:", key=f"src_{k}")
                df_v = df[m_filt].copy() if m_filt is not None else df.copy()
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                if view_mode == "Tradycyjny (Tabela)":
                    df_v.insert(0, "USUŃ", False)
                    # PODGLĄD obok NOTATKI
                    df_v.insert(df_v.columns.get_loc("NOTATKA") + 1, "PODGLĄD", False)
                    
                    ed = st.data_editor(df_v, use_container_width=True, hide_index=True, key=f"ed_{k}",
                        column_config={
                            "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                            "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options + empties_ops),
                            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Curr", display_text="Otwórz"),
                            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                            "dodatkowe zdjęcie": st.column_config.LinkColumn("🖼️ Dod.", display_text="Otwórz"),
                            "NOTATKA DODATKOWA": None
                        })
                    edit_trackers[k] = (df_v, ed, t_idx)
                    
                    sel = ed[ed["PODGLĄD"] == True]
                    if not sel.empty:
                        r = sel.iloc[-1]
                        st.info(f"📝 **Notatka:** {r['NOTATKA']}")
                        if r['NOTATKA DODATKOWA']: st.warning(f"💡 **Dodatkowa:** {r['NOTATKA DODATKOWA']}")
                else:
                    # KAFELKI
                    for truck in df_v['Auto'].unique():
                        t_data = df_v[df_v['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for idx_c, (_, r) in enumerate(t_data.iterrows()):
                            with cols[idx_c % 3]:
                                s = str(r['STATUS']).upper()
                                c = "status-trasie" if "TRASIE" in s else "status-rampa" if "RAMP" in s else "status-rozladowany" if "ROZŁADOWANY" in s else "status-empties" if "EMPTIES" in s else "status-zaladowany" if "ZAŁADOWANY" in s else "status-pusty"
                                st.markdown(f'<div class="transport-card {c}"><b>[{r["Nr Proj."]}] {r["Nazwa Projektu"]}</b><br>📍 {r["Hala"]} | {r["Godzina"]}<br>Status: <b>{r["STATUS"]}</b></div>', unsafe_allow_html=True)
                                if r['spis casów']: st.link_button("📋 Spis Casów", r['spis casów'], use_container_width=True)

        with tabs[2]: # PUSTE
            df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_p.empty:
                df_p_g = df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                st.data_editor(df_p_g, use_container_width=True, hide_index=True)

        # --- 8. ZAPIS I USUWANIE ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            try:
                full_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                to_delete = []
                target_tab = st.session_state.active_tab

                for k, (orig, edit, t_idx) in edit_trackers.items():
                    for i in range(len(edit)):
                        real_idx = orig.index[i]
                        if edit.iloc[i]["USUŃ"] == True:
                            to_delete.append(real_idx)
                            target_tab = t_idx
                        else:
                            for col in edit.columns:
                                if col in full_db.columns:
                                    full_db.at[real_idx, col] = edit.iloc[i][col]

                if to_delete:
                    full_db = full_db.drop(to_delete)

                conn.update(spreadsheet=URL, data=full_db[all_cols])
                st.cache_data.clear()
                st.session_state.active_tab = target_tab
                st.success("Zapisano!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd: {e}")

    except Exception as e:
        st.error(f"Błąd: {e}")
