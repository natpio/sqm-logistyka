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
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace('nan', '')

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

        edit_trackers = {}

        # --- ZAKŁADKA: MONTAŻE ---
        with tabs[0]:
            c1, c2, c3 = st.columns([1.5, 1, 2])
            with c1:
                d_val = st.date_input("Dzień montażu:", value=datetime.now(), key="d_in")
            with c2:
                st.write("###")
                all_d = st.checkbox("Wszystkie dni", value=False, key="a_in")
            with c3:
                search = st.text_input("🔍 Szukaj:", key="s_in")

            # POPRAWIONA MASKA: Pokazuje wszystko co nie jest rozładowane/puste
            mask_in = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & \
                      (~df['STATUS'].str.contains("PUSTY", na=False, case=False))
            df_in = df[mask_in].copy()

            if not all_d:
                df_in['Data_dt'] = pd.to_datetime(df_in['Data'], errors='coerce')
                df_in = df_in[df_in['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
            
            if search:
                df_in = df_in[df_in.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg_main, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)

        # --- ZAKŁADKA: ROZŁADOWANE ---
        with tabs[1]:
            mask_out = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
            df_out = df[mask_out].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg_main, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)

        # --- ZAKŁADKA: PUSTE TRUCKI ---
        with tabs[2]:
            mask_empty = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
            df_empty_raw = df[mask_empty].copy()
            if not df_empty_raw.empty:
                df_empty_grouped = df_empty_raw.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                ed_empty = st.data_editor(df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, key="ed_empty", hide_index=True)
                edit_trackers["ed_empty"] = (df_empty_grouped, ed_empty)

        # --- ZAKŁADKA: SLOTY NA EMPTIES ---
        with tabs[3]:
            st.subheader("Nowy Slot")
            df_puste = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
            with st.form("form_emp"):
                c1, c2, c3 = st.columns(3)
                with c1: f_d, f_s = st.date_input("DATA"), st.text_input("NR SLOTU")
                with c2: f_g, f_h = st.text_input("GODZINA"), st.selectbox("HALA", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                with c3: f_c = st.selectbox("PRZEWOŹNIK", sorted(df_puste['Przewoźnik'].unique()) if not df_puste.empty else ["Brak"])
                f_st = st.selectbox("STATUS", ["ODBIERA EMPTIES", "ZAVOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                if st.form_submit_button("DODAJ"):
                    m = df_puste[df_puste['Przewoźnik'] == f_c].iloc[0]
                    nr = {"Data": str(f_d), "Nr Slotu": f_s, "Godzina": f_g, "Hala": f_h, "Przewoźnik": f_c, "Auto": m['Auto'], "Kierowca": m['Kierowca'], "STATUS": f_st, "Nr Proj.": "EMPTIES"}
                    conn.update(spreadsheet=URL, data=pd.concat([df, pd.DataFrame([nr])], ignore_index=True))
                    st.cache_data.clear(); st.rerun()
            
            df_sl = df[df['STATUS'].str.contains("ODBIERA|ZAVOZI|POWRÓT", na=False, case=False)].copy()
            ed_sl = st.data_editor(df_sl[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], use_container_width=True, key="ed_sl", column_config=column_cfg_main, hide_index=True)
            edit_trackers["ed_sl"] = (df_sl, ed_sl)

        # --- ZAKŁADKA: BAZA ---
        with tabs[4]:
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg_main, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- 8. ZAPIS ---
        if edit_trackers:
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig, ed) in edit_trackers.items():
                    ch = st.session_state[k].get("edited_rows", {})
                    if k == "ed_empty":
                        for r, c in ch.items():
                            if "STATUS" in c: final_df.loc[final_df['Auto'] == orig.iloc[int(r)]['Auto'], 'STATUS'] = c["STATUS"]
                    else:
                        for r, c in ch.items():
                            for col, val in c.items(): final_df.at[orig.index[int(r)], col] = val
                conn.update(spreadsheet=URL, data=final_df.drop(columns=["PODGLĄD"]) if "PODGLĄD" in final_df.columns else final_df)
                st.cache_data.clear(); st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
