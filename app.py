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

        # Inicjalizacja kolumn technicznych
        if "PODGLĄD" not in df.columns: df.insert(0, "PODGLĄD", False)
        if "USUŃ" not in df.columns: df.insert(0, "USUŃ", False)

        # --- 5. METRYKI ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len(p_fiz))

        # --- 6. ZAKŁADKI (Z PAMIĘCIĄ SESJI) ---
        tab_titles = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"]
        
        # Zapamiętywanie wybranej zakładki
        if "active_tab" not in st.session_state:
            st.session_state.active_tab = 0

        # Funkcja do zmiany zakładki po zapisie
        def set_tab(index):
            st.session_state.active_tab = index

        tabs = st.tabs(tab_titles)
        edit_trackers = {}
        carriers_list = sorted([c for c in df['Przewoźnik'].unique() if c and c != ""])
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- T4: SLOTY NA EMPTIES ---
        with tabs[3]:
            st.subheader("Planowanie operacji Empties")
            with st.form("f_emp_plan", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nd, nh, ns = st.date_input("Data", datetime.now()), st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"]), st.text_input("Slot")
                with c2:
                    nt, np_form = st.text_input("Godzina"), st.selectbox("Przewoźnik (opcjonalnie)", [""] + carriers_list)
                    nst = st.selectbox("Status", empties_ops)
                with c3:
                    nn = st.text_area("Notatka dodatkowa")
                    if st.form_submit_button("💾 DODAJ SLOT"):
                        fresh = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        new_r = pd.DataFrame([{'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 'Przewoźnik': np_form, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': nn, 'USUŃ': False, 'PODGLĄD': False}])
                        conn.update(spreadsheet=URL, data=pd.concat([fresh, new_r], ignore_index=True))
                        st.cache_data.clear()
                        set_tab(3) # Zostajemy w tej zakładce
                        st.rerun()

            st.divider()
            df_s_v = df[df['STATUS'].isin(empties_ops)].copy()
            if not df_s_v.empty:
                ed_s = st.data_editor(
                    df_s_v[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'STATUS', 'NOTATKA DODATKOWA']], 
                    use_container_width=True, key="ed_empties", hide_index=True,
                    column_config={
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list)
                    }
                )
                edit_trackers["ed_empties"] = (df_s_v, ed_s, 3) # (oryginalne dane, edytor, index zakładki)

        # --- POZOSTAŁE ZAKŁADKI ---
        for i, (tab, key, m_filter) in enumerate(zip([tabs[0], tabs[1], tabs[4]], ["in", "out", "all"], [
            (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops)),
            df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False),
            None
        ])):
            idx = [0, 1, 4][i]
            with tab:
                src = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                df_v = df[m_filter].copy() if m_filter is not None else df.copy()
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                cfg = {
                    "STATUS": st.column_config.SelectboxColumn("STATUS", options=carriers_list + status_options + empties_ops if 'status_options' in locals() else empties_ops),
                    "PODGLĄD": st.column_config.CheckboxColumn("👁️"),
                    "USUŃ": st.column_config.CheckboxColumn("🗑️"),
                    "NOTATKA DODATKOWA": None
                }
                ed = st.data_editor(df_v, use_container_width=True, key=f"ed_{key}", column_config=cfg, hide_index=True)
                edit_trackers[f"ed_{key}"] = (df_v, ed, idx)

        with tabs[2]: # PUSTE
            df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_p.empty:
                df_p_g = df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                st.data_editor(df_p_g, use_container_width=True, hide_index=True)

        # --- 8. GLOBALNY ZAPIS Z BLOKADĄ ZAKŁADKI ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            try:
                # 1. Pobierz świeże dane
                f_df = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                target_tab = st.session_state.active_tab

                # 2. Zastosuj zmiany ze wszystkich edytorów
                for k, (orig_sub, edited_sub, tab_idx) in edit_trackers.items():
                    # Jeśli ten edytor ma jakiekolwiek zmiany
                    if not edited_sub.equals(orig_sub):
                        target_tab = tab_idx # Jeśli tu zmienialiśmy, to tu chcemy wrócić
                        for i in range(len(edited_sub)):
                            real_idx = orig_sub.index[i]
                            for col in edited_sub.columns:
                                if col in f_df.columns:
                                    f_df.at[real_idx, col] = edited_sub.iloc[i][col]

                # 3. Kluczowe usuwanie: Filtrujemy wiersze gdzie USUŃ jest True
                if "USUŃ" in f_df.columns:
                    # Konwertujemy na boolean na wypadek gdyby GSheets zwróciło stringi
                    f_df['USUŃ'] = f_df['USUŃ'].astype(str).str.lower().map({'true': True, 'false': False, '1': True, '0': False}).fillna(False)
                    f_df = f_df[f_df['USUŃ'] != True]

                # 4. Czyszczenie techniczne przed wysyłką
                final_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
                conn.update(spreadsheet=URL, data=f_df[final_cols])
                
                st.cache_data.clear()
                st.session_state.active_tab = target_tab # Ustawienie zakładki powrotnej
                st.success("Dane zaktualizowane!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Błąd: {e}")

    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
