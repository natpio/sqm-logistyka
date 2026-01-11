import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide")

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
    # --- 3. DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Inicjalizacja stanu zakładki
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = 0

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

        # --- 4. LISTY I KONFIGURACJA ---
        carriers_list = sorted([c for c in df['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 5. TABS ---
        tab_list = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"]
        
        # Funkcja pomocnicza do zmiany zakładki w sesji
        def on_tab_change():
            # Streamlit obecnie nie wspiera bezpośredniego on_change dla tabs, 
            # więc używamy indeksu przy renderowaniu
            pass

        tabs = st.tabs(tab_list)
        edit_trackers = {}

        # --- ZAKŁADKA 3: SLOTY NA EMPTIES ---
        with tabs[3]:
            st.subheader("Planowanie operacji Empties")
            with st.form("f_emp_plan"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nd = st.date_input("Data", datetime.now())
                    nh = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                    ns = st.text_input("Slot")
                with c2:
                    nt = st.text_input("Godzina")
                    np_form = st.selectbox("Przewoźnik (opcjonalnie)", [""] + carriers_list)
                    nst = st.selectbox("Status", empties_ops)
                with c3:
                    nn = st.text_area("Notatka dodatkowa")
                    if st.form_submit_button("💾 DODAJ SLOT"):
                        fresh = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        new_r = pd.DataFrame([{'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 'Przewoźnik': np_form, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 'NOTATKA DODATKOWA': nn}])
                        conn.update(spreadsheet=URL, data=pd.concat([fresh, new_r], ignore_index=True))
                        st.cache_data.clear()
                        st.session_state.current_tab = 3
                        st.rerun()

            st.divider()
            df_s_v = df[df['STATUS'].isin(empties_ops)].copy()
            if not df_s_v.empty:
                df_s_v.insert(0, "USUŃ", False)
                ed_s = st.data_editor(
                    df_s_v[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'STATUS', 'NOTATKA DODATKOWA']], 
                    use_container_width=True, key="ed_empties", hide_index=True,
                    column_config={
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list),
                        "STATUS": st.column_config.SelectboxColumn("Status", options=empties_ops)
                    }
                )
                edit_trackers["ed_empties"] = (df_s_v, ed_s, 3)

        # --- ZAKŁADKI 0, 1, 4 (MONTAŻE, ROZŁADOWANE, BAZA) ---
        for i, (t_idx, key, m_filter) in enumerate([
            (0, "in", (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops))),
            (1, "out", df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False)),
            (4, "all", None)
        ]):
            with tabs[t_idx]:
                src = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                df_v = df[m_filter].copy() if m_filter is not None else df.copy()
                if src:
                    df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]
                
                df_v.insert(0, "USUŃ", False)
                df_v.insert(1, "PODGLĄD", False)
                
                ed = st.data_editor(
                    df_v, use_container_width=True, key=f"ed_{key}", hide_index=True,
                    column_config={
                        "USUŃ": st.column_config.CheckboxColumn("🗑️"), 
                        "PODGLĄD": st.column_config.CheckboxColumn("👁️"),
                        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options + empties_ops),
                        "NOTATKA DODATKOWA": None
                    }
                )
                edit_trackers[f"ed_{key}"] = (df_v, ed, t_idx)
                
                sel = ed[ed["PODGLĄD"] == True]
                if not sel.empty:
                    r = sel.iloc[-1]
                    st.info(f"📝 **Notatka:** {r['NOTATKA']}")
                    if r['NOTATKA DODATKOWA']: st.warning(f"💡 **Dodatkowa:** {r['NOTATKA DODATKOWA']}")

        # --- ZAKŁADKA 2: PUSTE ---
        with tabs[2]:
            df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_p.empty:
                df_p_g = df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                st.data_editor(df_p_g, use_container_width=True, hide_index=True)

        # --- 6. GLOBALNY ZAPIS I USUWANIE ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            try:
                # Pobierz aktualny stan bazy bezpośrednio przed zapisem
                current_db = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                
                to_delete_indices = []
                
                # Iteruj przez wszystkie trackery zmian (ze wszystkich widocznych tabel)
                for k, (orig_df, edited_df, t_idx) in edit_trackers.items():
                    # Sprawdź każdy wiersz w edytowanej tabeli
                    for i in range(len(edited_df)):
                        real_idx = orig_df.index[i] # Pobierz index z oryginalnej ramki danych
                        
                        # Jeśli zaznaczono USUŃ
                        if edited_df.iloc[i]["USUŃ"] == True:
                            to_delete_indices.append(real_idx)
                        else:
                            # Aktualizuj dane w głównej bazie
                            for col in edited_df.columns:
                                if col in current_db.columns:
                                    current_db.at[real_idx, col] = edited_df.iloc[i][col]

                # Usuń zaznaczone wiersze
                if to_delete_indices:
                    current_db = current_db.drop(to_delete_indices)
                
                # Zapisz do Google Sheets
                conn.update(spreadsheet=URL, data=current_db[all_cols])
                st.cache_data.clear()
                
                st.success(f"Pomyślnie zaktualizowano bazę danych. Usunięto {len(to_delete_indices)} wierszy.")
                st.rerun()

            except Exception as e:
                st.error(f"Błąd podczas zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
