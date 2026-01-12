import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM CONTROL TOWER", 
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
    return True

if check_password():
    # --- 3. STYLE CSS ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        # Odczyt i usuwanie wierszy całkowicie pustych
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 
            'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
        ]
        
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', 'nan nan'], '')

        # POPRAWKA PODGLĄD: Wymuszenie typu bool (naprawia błąd ColumnDataKind.FLOAT)
        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).map(lambda x: True if x == 1 or x is True else False)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ SQM Logistics")
            if st.button("🔄 Odśwież dane"):
                st.cache_data.clear()
                st.rerun()
            st.divider()
            if st.button("🚪 Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        column_cfg = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=[
                "🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", 
                "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", 
                "ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"
            ], width="medium"),
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
        statusy_wolne = "PUSTY|📦 EMPTIES"
        statusy_nowe_empties = "ODBIERA EMPTIES|ZAVOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        edit_trackers = {}

        # --- ZAKŁADKA 1: MONTAŻE ---
        with tabs[0]:
            c1, c2, c3 = st.columns([1.5, 1, 2])
            with c1: d_val = st.date_input("Dzień:", value=datetime.now(), key="d_in")
            with c2: 
                st.write("###")
                all_d = st.checkbox("Wszystkie dni", value=False, key="a_in")
            with c3: search_in = st.text_input("🔍 Szukaj projektu:", key="s_in")

            # Maska wykluczająca rozładowane, puste, nowe statusy empties i rekordy "projektowe" Empties
            mask_in = (
                (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & 
                (~df['STATUS'].str.contains("PUSTY", na=False, case=False)) & 
                (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)) &
                (~df['Nr Proj.'].str.contains("EMPTIES", na=False, case=False)) &
                (df['Auto'] != "") # Ukrywa wiersze bez przypisanego auta
            )
            df_in = df[mask_in].copy()

            if not all_d:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)

        # --- ZAKŁADKA 2: ROZŁADOWANE ---
        with tabs[1]:
            mask_out = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
            df_out = df[mask_out].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)

        # --- ZAKŁADKA 3: PUSTE TRUCKI ---
        with tabs[2]:
            st.info("Pojazdy gotowe do planowania (Status: PUSTY / EMPTIES)")
            # FILTR: Musi być status wolny ORAZ wypełnione pole Auto (usuwa widmo z samej góry)
            mask_empty = (df['STATUS'].str.contains(statusy_wolne, na=False, case=False)) & (df['Auto'] != "")
            df_empty = df[mask_empty].copy()
            
            if not df_empty.empty:
                df_empty_grouped = df_empty.groupby('Auto').agg({
                    'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'
                }).reset_index()
                
                ed_empty = st.data_editor(
                    df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], 
                    use_container_width=True, key="ed_empty",
                    column_config={"Auto": st.column_config.TextColumn("DANE AUTA")},
                    hide_index=True
                )
                edit_trackers["ed_empty"] = (df_empty_grouped, ed_empty)
            else:
                st.warning("Brak dostępnych pojazdów.")

        # --- ZAKŁADKA 4: SLOTY NA EMPTIES ---
        with tabs[3]:
            st.subheader("➕ Zaplanuj slot")
            df_puste_form = df[(df['STATUS'].str.contains(statusy_wolne, na=False, case=False)) & (df['Auto'] != "")]
            
            with st.form("form_emp"):
                c1, c2, c3 = st.columns(3)
                with c1: f_d, f_s = st.date_input("DATA"), st.text_input("NR SLOTU")
                with c2: f_g, f_h = st.text_input("GODZINA"), st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c3: 
                    f_c = st.selectbox("PRZEWOŹNIK", sorted(df_puste_form['Przewoźnik'].unique()) if not df_puste_form.empty else ["Brak"])
                    f_st = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                
                if st.form_submit_button("DODAJ SLOT", use_container_width=True):
                    if not df_puste_form.empty and f_c != "Brak":
                        match = df_puste_form[df_puste_form['Przewoźnik'] == f_c].iloc[0]
                        new_row = {
                            "Data": str(f_d), "Nr Slotu": f_s, "Godzina": f_g, "Hala": f_h,
                            "Przewoźnik": f_c, "Auto": match['Auto'], "Kierowca": match['Kierowca'],
                            "STATUS": f_st, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "OBSŁUGA EMPTIES"
                        }
                        conn.update(spreadsheet=URL, data=pd.concat([df, pd.DataFrame([new_row])], ignore_index=True))
                        st.cache_data.clear(); st.rerun()

            st.divider()
            # Tabela dolna - tylko aktywne sloty empties, bez pustych "widm"
            df_sl = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)].copy()
            df_sl = df_sl[df_sl['Auto'] != ""] 
            
            ed_sl = st.data_editor(
                df_sl[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA']], 
                use_container_width=True, key="ed_sl", column_config=column_cfg, hide_index=True
            )
            edit_trackers["ed_sl"] = (df_sl, ed_sl)

        # --- ZAKŁADKA 5: BAZA ---
        with tabs[4]:
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- 8. GLOBALNY ZAPIS ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig, ed) in edit_trackers.items():
                    ch = st.session_state[k].get("edited_rows", {})
                    if k == "ed_empty":
                        for r, c in ch.items():
                            if "STATUS" in c:
                                auto_val = orig.iloc[int(r)]['Auto']
                                final_df.loc[final_df['Auto'] == auto_val, 'STATUS'] = c["STATUS"]
                    else:
                        for r, c in ch.items():
                            for col, val in c.items():
                                final_df.at[orig.index[int(r)], col] = val
                
                # Usuwamy techniczny PODGLĄD przed wysyłką do Sheets
                to_save = final_df.copy()
                if "PODGLĄD" in to_save.columns: to_save = to_save.drop(columns=["PODGLĄD"])
                conn.update(spreadsheet=URL, data=to_save)
                st.cache_data.clear(); st.success("Zapisano!"); st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")
