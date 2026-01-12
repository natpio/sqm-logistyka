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
        .status-trasie { border-left: 8px solid #ffeb3b; }
        .status-rampa { border-left: 8px solid #f44336; }
        .status-rozladowany { border-left: 8px solid #4caf50; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        # Standaryzacja kolumn
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace('nan', '')

        # Wymuszenie typu Boolean dla kolumny PODGLĄD (naprawa błędu FLOAT)
        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).astype(bool)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            if st.button("🔄 Odśwież dane"):
                st.cache_data.clear()
                st.rerun()
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracja edytora
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", "ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
        }

        # --- 6. METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # --- 7. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"
        statusy_nowe_empties = "ODBIERA EMPTIES|ZAVOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        edit_trackers = {}

        for i, (tab, key) in enumerate(zip(tabs, ["in", "out", "empty", "slots_empties", "full"])):
            with tab:
                # --- MONTAŻE: Z filtrem daty i wyszukiwarką ---
                if key == "in":
                    col_d1, col_d2, col_s = st.columns([1.5, 1, 2])
                    with col_d1:
                        d_val = st.date_input("Dzień montażu:", value=datetime.now(), key="date_in")
                    with col_d2:
                        st.write("###")
                        all_d = st.checkbox("Wszystkie dni", value=False, key="all_in")
                    with col_s:
                        search = st.text_input("🔍 Szukaj projektu/auta:", key="search_in")

                    mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & \
                           (~df['STATUS'].str.contains(statusy_puste, na=False, case=False)) & \
                           (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False))
                    df_view = df[mask].copy()

                    if not all_d:
                        df_view['Data_dt'] = pd.to_datetime(df_view['Data'], errors='coerce')
                        df_view = df_view[df_view['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
                    
                    if search:
                        df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                    ed = st.data_editor(df_view, use_container_width=True, key="ed_in", column_config=column_cfg_main, hide_index=True)
                    edit_trackers["ed_in"] = (df_view, ed)

                # --- PUSTE TRUCKI: 4 kolumny ---
                elif key == "empty":
                    mask = df['STATUS'].str.contains(statusy_puste, na=False, case=False)
                    df_empty = df[mask].copy()
                    if not df_empty.empty:
                        df_empty_grouped = df_empty.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                        ed_p = st.data_editor(
                            df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], 
                            use_container_width=True, 
                            key="ed_empty",
                            column_config={"Auto": st.column_config.TextColumn("DANE AUTA")}, 
                            hide_index=True
                        )
                        edit_trackers["ed_empty"] = (df_empty_grouped, ed_p)
                    else:
                        st.info("Brak pustych aut.")

                # --- SLOTY NA EMPTIES: Formularz + Edytowalna tabela ---
                elif key == "slots_empties":
                    st.subheader("Zaplanuj nowy slot")
                    df_base_empties = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
                    carriers_list = sorted(df_base_empties['Przewoźnik'].unique())
                    
                    with st.form("form_new_empty"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            f_d = st.date_input("DATA")
                            f_s = st.text_input("NR SLOTU")
                        with c2:
                            f_g = st.text_input("GODZINA")
                            f_h = st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                        with c3:
                            f_c = st.selectbox("PRZEWOŹNIK", carriers_list)
                            f_st = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                        
                        if st.form_submit_button("DODAJ SLOT DO PLANU", use_container_width=True):
                            match = df_base_empties[df_base_empties['Przewoźnik'] == f_c].iloc[0]
                            new_row = {
                                "Data": str(f_d), "Nr Slotu": f_s, "Godzina": f_g, "Hala": f_h, 
                                "Przewoźnik": f_c, "Auto": match['Auto'], "Kierowca": match['Kierowca'], 
                                "STATUS": f_st, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "OBSŁUGA EMPTIES"
                            }
                            new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            conn.update(spreadsheet=URL, data=new_df)
                            st.cache_data.clear()
                            st.rerun()
                    
                    st.divider()
                    st.subheader("Zarządzaj dodanymi slotami")
                    df_sl = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)].copy()
                    ed_sl = st.data_editor(
                        df_sl[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA']], 
                        use_container_width=True, 
                        key="ed_sl", 
                        column_config=column_cfg_main, 
                        hide_index=True
                    )
                    edit_trackers["ed_sl"] = (df_sl, ed_sl)

                # --- ROZŁADOWANE / BAZA ---
                else:
                    if key == "out":
                        mask = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
                        df_v = df[mask].copy()
                    else:
                        df_v = df.copy()
                    
                    search_v = st.text_input("🔍 Szukaj w tej zakładce:", key=f"s_{key}")
                    if search_v:
                        df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(search_v, case=False).any(), axis=1)]
                    
                    ed_v = st.data_editor(df_v, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main, hide_index=True)
                    edit_trackers[f"ed_{key}"] = (df_v, ed_v)

        # --- 8. ZAPIS ZMIAN ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig, ed) in edit_trackers.items():
                    ch = st.session_state[k].get("edited_rows", {})
                    if k == "ed_empty":
                        for r, c in ch.items():
                            if "STATUS" in c:
                                auto = orig.iloc[int(r)]['Auto']
                                final_df.loc[final_df['Auto'] == auto, 'STATUS'] = c["STATUS"]
                    else:
                        for r, c in ch.items():
                            real_idx = orig.index[int(r)]
                            for col, val in c.items():
                                final_df.at[real_idx, col] = val
                
                # Usuwamy pomocniczą kolumnę PODGLĄD przed wysyłką, jeśli nie ma jej być w arkuszu (opcjonalnie)
                to_save = final_df.copy()
                if "PODGLĄD" in to_save.columns:
                    to_save = to_save.drop(columns=["PODGLĄD"])
                
                conn.update(spreadsheet=URL, data=to_save)
                st.cache_data.clear()
                st.success("Wszystkie dane zostały zsynchronizowane z arkuszem!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny aplikacji: {e}")
