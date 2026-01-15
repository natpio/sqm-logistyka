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
        .note-box { background-color: #fff3cd; border-left: 5px solid #ffa000; padding: 10px; border-radius: 5px; margin: 10px 0; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m")
        df = raw_df.dropna(how="all").reset_index(drop=True)
        
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 
            'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
        ]
        
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', 'nan nan', '<NA>', 'None None'], '')

        # Naprawa kolumny PODGLĄD (Checkbox) - globalna inicjalizacja
        if "PODGLĄD" not in df.columns:
            df.insert(0, "PODGLĄD", False)
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

        # Konfiguracja wyświetlania kolumn
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
            "NOTATKA": st.column_config.LinkColumn("📝 NOTATKA", width="large") # Zmieniono na LinkColumn dla wykrywania linków
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

            mask_in = (
                (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & 
                (~df['STATUS'].str.contains("PUSTY", na=False, case=False)) & 
                (~df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)) &
                (~df['Nr Proj.'].str.contains("EMPTIES", na=False, case=False)) &
                (df['Nr Proj.'] != "")
            )
            df_in = df[mask_in].copy()

            if not all_d:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce', dayfirst=True)
                df_in = df_in[df_in['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
            if search_in:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search_in, case=False).any(), axis=1)]

            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)
            
            # Podgląd notatek dla Montaży
            selected_notes = ed_in[ed_in["PODGLĄD"] == True]
            for _, row in selected_notes.iterrows():
                st.info(f"**Notatka ({row['Nr Proj.']} - {row['Nazwa Projektu']}):**\n\n{row['NOTATKA']}")

        # --- ZAKŁADKA 2: ROZŁADOWANE ---
        with tabs[1]:
            mask_out = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
            df_out = df[mask_out].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)

        # --- ZAKŁADKA 3: PUSTE TRUCKI ---
        with tabs[2]:
            st.info("Pojazdy gotowe do planowania (Status: PUSTY / EMPTIES)")
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
            lista_przew = sorted(df_puste_form['Przewoźnik'].unique()) if not df_puste_form.empty else []
            
            with st.form("form_emp"):
                c1, c2, c3 = st.columns(3)
                with c1: 
                    f_d = st.date_input("DATA")
                    f_s = st.text_input("NR SLOTU")
                with c2: 
                    f_g = st.text_input("GODZINA")
                    f_h = st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c3: 
                    f_c = st.selectbox("PRZEWOŹNIK (Opcjonalnie)", ["-- Brak / Nowy --"] + lista_przew)
                    f_st = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                
                if st.form_submit_button("DODAJ SLOT", use_container_width=True):
                    auto_val, kier_val = "", ""
                    curr_carr = f_c if f_c != "-- Brak / Nowy --" else ""
                    if curr_carr and not df_puste_form[df_puste_form['Przewoźnik'] == f_c].empty:
                        match = df_puste_form[df_puste_form['Przewoźnik'] == f_c].iloc[0]
                        auto_val, kier_val = match['Auto'], match['Kierowca']

                    new_row_data = {
                        "Data": str(f_d), "Nr Slotu": f_s, "Godzina": f_g, "Hala": f_h,
                        "Przewoźnik": curr_carr, "Auto": auto_val, "Kierowca": kier_val,
                        "STATUS": f_st, "Nr Proj.": "EMPTIES", "Nazwa Projektu": "OBSŁUGA EMPTIES",
                        "PODGLĄD": False
                    }
                    
                    row_full = {col: new_row_data.get(col, "") for col in all_cols}
                    save_df = pd.concat([df, pd.DataFrame([row_full])], ignore_index=True)
                    if "PODGLĄD" in save_df.columns: save_df = save_df.drop(columns=["PODGLĄD"])
                    
                    conn.update(spreadsheet=URL, data=save_df[all_cols])
                    st.cache_data.clear(); st.success("Slot zarezerwowany!"); st.rerun()

            st.divider()
            # Widok istniejących slotów na empties
            df_sl = df[df['STATUS'].str.contains(statusy_nowe_empties, na=False, case=False)].copy()
            df_sl = df_sl[(df_sl['Auto'] != "") | (df_sl['Nr Slotu'] != "")] 
            
            # Dodanie oka do konfiguracji wyświetlania
            ed_sl = st.data_editor(
                df_sl[['PODGLĄD', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA']], 
                use_container_width=True, key="ed_sl", column_config=column_cfg, hide_index=True
            )
            edit_trackers["ed_sl"] = (df_sl, ed_sl)

            # Podgląd notatek dla Empties (Oko)
            selected_sl_notes = ed_sl[ed_sl["PODGLĄD"] == True]
            for _, row in selected_sl_notes.iterrows():
                st.warning(f"**Notatka (Slot: {row['Nr Slotu']} - {row['Auto']}):**\n\n{row['NOTATKA']}")

        # --- ZAKŁADKA 5: BAZA ---
        with tabs[4]:
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- 8. GLOBALNY ZAPIS ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig_df, ed_component) in edit_trackers.items():
                    state_key = k
                    if state_key in st.session_state:
                        changes = st.session_state[state_key].get("edited_rows", {})
                        
                        if k == "ed_empty":
                            for r_idx, c_vals in changes.items():
                                if "STATUS" in c_vals:
                                    a_id = orig_df.iloc[int(r_idx)]['Auto']
                                    final_df.loc[final_df['Auto'] == a_id, 'STATUS'] = c_vals["STATUS"]
                        else:
                            for r_idx, c_vals in changes.items():
                                actual_idx = orig_df.index[int(r_idx)]
                                for col, val in c_vals.items():
                                    final_df.at[actual_idx, col] = val
                
                to_save = final_df.copy()
                if "PODGLĄD" in to_save.columns: to_save = to_save.drop(columns=["PODGLĄD"])
                
                conn.update(spreadsheet=URL, data=to_save[all_cols])
                st.cache_data.clear()
                st.success("Dane zsynchronizowane z arkuszem!")
                st.rerun()

    except Exception as e:
        st.error(f"Krytyczny błąd aplikacji: {e}")
