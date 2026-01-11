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
    # --- 3. STYLE CSS ---
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

    # --- 4. POŁĄCZENIE Z GOOGLE SHEETS ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="2s").dropna(how="all")
        
        # Standaryzacja kolumn
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
            f_hala = st.multiselect("Filtruj Halę:", options=sorted(df['Hala'].unique()))
            f_status = st.multiselect("Filtruj Status:", options=sorted(df['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Listy pomocnicze
        carriers_list = sorted([c for c in df['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 7. ZAKŁADKI ---
        t1, t2, t3, t4, t5 = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        
        # Słownik do śledzenia zmian w edytorach
        edit_trackers = {}

        # --- ZAKŁADKA: SLOTY NA EMPTIES ---
        with t4:
            st.subheader("Planowanie operacji Empties")
            with st.form("f_empties", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nd = st.date_input("Data", datetime.now())
                    nh = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                    ns = st.text_input("Slot (jeśli dotyczy)")
                with c2:
                    nt = st.text_input("Godzina")
                    np = st.selectbox("Przewoźnik", [""] + carriers_list)
                    nst = st.selectbox("Status", empties_ops)
                with c3:
                    nn = st.text_area("Notatka (co zabiera/zawozi)")
                    if st.form_submit_button("💾 DODAJ OPERACJĘ DO PLANU"):
                        fresh_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        new_row = pd.DataFrame([{
                            'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 
                            'Przewoźnik': np, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 
                            'NOTATKA DODATKOWA': nn
                        }])
                        conn.update(spreadsheet=URL, data=pd.concat([fresh_db, new_row], ignore_index=True))
                        st.cache_data.clear()
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
                edit_trackers["ed_empties"] = (df_empties, ed_emp)

        # --- POZOSTAŁE ZAKŁADKI (MONTAŻE, ROZŁADOWANE, BAZA) ---
        for tab, key, m_filter in zip([t1, t2, t5], ["in", "out", "all"], [
            (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops)),
            df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False),
            None
        ]):
            with tab:
                src = st.text_input("🔍 Szukaj w tej zakładce:", key=f"src_{key}")
                df_v = df[m_filter].copy() if m_filter is not None else df.copy()
                if f_hala: df_v = df_v[df_v['Hala'].isin(f_hala)]
                if f_status: df_v = df_v[df_v['STATUS'].isin(f_status)]
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                if view_mode == "Tradycyjny (Tabela)":
                    df_v.insert(0, "USUŃ", False)
                    df_v.insert(1, "PODGLĄD", False)
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
                    
                    sel = ed[ed["PODGLĄD"] == True]
                    if not sel.empty:
                        r = sel.iloc[-1]
                        st.info(f"📝 **Notatka:** {r['NOTATKA']}")
                        if r['NOTATKA DODATKOWA']: st.warning(f"💡 **Dodatkowa:** {r['NOTATKA DODATKOWA']}")
                else:
                    # WIDOK KAFELKOWY
                    for truck in df_v['Auto'].unique():
                        t_data = df_v[df_v['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for i, (_, r) in enumerate(t_data.iterrows()):
                            with cols[i % 3]:
                                s = str(r['STATUS']).upper()
                                c = "status-trasie" if "TRASIE" in s else "status-rampa" if "RAMP" in s else "status-rozladowany" if "ROZŁADOWANY" in s else "status-empties" if "EMPTIES" in s else "status-zaladowany" if "ZAŁADOWANY" in s else "status-pusty"
                                st.markdown(f'<div class="transport-card {c}"><b>[{r["Nr Proj."]}] {r["Nazwa Projektu"]}</b><br>📍 {r["Hala"]} | {r["Godzina"]}<br>Status: <b>{r["STATUS"]}</b></div>', unsafe_allow_html=True)
                                if r['spis casów']: st.link_button("📋 Spis Casów", r['spis casów'], use_container_width=True)

        with t3: # PUSTE TRUCKI
            df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_p.empty:
                df_p_g = df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                st.data_editor(df_p_g, use_container_width=True, hide_index=True)

        # --- 8. GLOBALNY ZAPIS I USUWANIE (POPRAWIONE) ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            try:
                full_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                to_delete_indices = []

                for k, (orig_sub, edited_sub) in edit_trackers.items():
                    for i in range(len(edited_sub)):
                        real_idx = orig_sub.index[i]
                        if edited_sub.iloc[i]["USUŃ"] == True:
                            to_delete_indices.append(real_idx)
                        else:
                            for col in edited_sub.columns:
                                if col in full_db.columns:
                                    full_db.at[real_idx, col] = edited_sub.iloc[i][col]

                if to_delete_indices:
                    full_db = full_db.drop(to_delete_indices)

                conn.update(spreadsheet=URL, data=full_db[all_cols])
                st.cache_data.clear()
                st.success("Baza zaktualizowana!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
