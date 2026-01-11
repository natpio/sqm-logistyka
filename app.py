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
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
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

        # Kolumny techniczne (tylko w sesji, nie w GSheets)
        if "PODGLĄD" not in df.columns: df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        if "USUŃ" not in df.columns: df["USUŃ"] = False

        # --- 5. METRYKI ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len(p_fiz))

        # --- 6. LISTY WYBORU ---
        # Dynamiczna lista przewoźników z bazy
        carriers_list = sorted([c for c in df['Przewoźnik'].unique() if c and c != ""])
        status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"]
        empties_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]

        # --- 7. ZAKŁADKI ---
        t1, t2, t3, t4, t5 = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        edit_trackers = {}

        # --- ZAKŁADKA: SLOTY NA EMPTIES ---
        with t4:
            st.subheader("Planowanie operacji Empties")
            
            with st.form("f_emp_plan", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nd = st.date_input("Data", datetime.now())
                    nh = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                    ns = st.text_input("Slot")
                with c2:
                    nt = st.text_input("Godzina")
                    np_form = st.selectbox("Przewoźnik (można przypisać później)", [""] + carriers_list)
                    nst = st.selectbox("Status początkowy", empties_ops)
                with c3:
                    nn = st.text_area("Notatka dodatkowa (np. co zabiera)")
                    if st.form_submit_button("💾 DODAJ SLOT DO PLANU"):
                        fresh = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        new_r = pd.DataFrame([{
                            'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 
                            'Przewoźnik': np_form, 'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 
                            'NOTATKA DODATKOWA': nn, 'USUŃ': False
                        }])
                        conn.update(spreadsheet=URL, data=pd.concat([fresh, new_r], ignore_index=True))
                        st.cache_data.clear()
                        st.rerun()

            st.divider()
            df_s_v = df[df['STATUS'].isin(empties_ops)].copy()
            if not df_s_v.empty:
                st.info("💡 Możesz przypisać przewoźnika wybierając go z listy w tabeli.")
                ed_s = st.data_editor(
                    df_s_v[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'STATUS', 'NOTATKA DODATKOWA']], 
                    use_container_width=True, 
                    key="ed_empties", 
                    hide_index=True,
                    column_config={
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=carriers_list, width="medium"),
                        "STATUS": st.column_config.SelectboxColumn("Status", options=empties_ops)
                    }
                )
                edit_trackers["ed_empties"] = (df_s_v, ed_s)

        # --- ZAKŁADKA: MONTAŻE / ROZŁADOWANE / BAZA ---
        for tab, key, m_filter in zip([t1, t2, t5], ["in", "out", "all"], [
            (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(empties_ops)),
            df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False),
            None
        ]):
            with tab:
                src = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                df_v = df[m_filter].copy() if m_filter is not None else df.copy()
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                cfg = {
                    "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options + empties_ops),
                    "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                    "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                    "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                    "PODGLĄD": st.column_config.CheckboxColumn("👁️"),
                    "USUŃ": st.column_config.CheckboxColumn("🗑️"),
                    "NOTATKA DODATKOWA": None # Ukryta w głównej tabeli
                }
                
                ed = st.data_editor(df_v, use_container_width=True, key=f"ed_{key}", column_config=cfg, hide_index=True)
                edit_trackers[f"ed_{key}"] = (df_v, ed)
                
                # Podgląd notatek pod tabelą
                sel = ed[ed["PODGLĄD"] == True]
                if not sel.empty:
                    r = sel.iloc[-1]
                    st.info(f"📝 **Notatka:** {r['NOTATKA']}")
                    if r['NOTATKA DODATKOWA']: st.warning(f"💡 **Dodatkowa:** {r['NOTATKA DODATKOWA']}")

        # --- ZAKŁADKA: PUSTE ---
        with t3:
            df_p = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_p.empty:
                df_p_g = df_p.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                ed_p = st.data_editor(df_p_g, use_container_width=True, key="ed_puste", hide_index=True)
                edit_trackers["ed_puste"] = (df_p_g, ed_p)

        # --- 8. BEZPIECZNY ZAPIS I USUWANIE ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            try:
                # Pobierz świeże dane
                f_df = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                
                # Zastosuj zmiany z edytorów używając indeksów oryginalnych
                for k, (orig_sub_df, edited_sub_df) in edit_trackers.items():
                    for i in range(len(edited_sub_df)):
                        real_idx = orig_sub_df.index[i]
                        for col in edited_sub_df.columns:
                            if col in f_df.columns:
                                f_df.at[real_idx, col] = edited_sub_df.iloc[i][col]

                # Obsługa usuwania
                if "USUŃ" in f_df.columns:
                    f_df = f_df[f_df['USUŃ'] != True]
                
                # Czyszczenie przed wysyłką do GSheets
                cols_to_save = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'NOTATKA DODATKOWA']
                conn.update(spreadsheet=URL, data=f_df[cols_to_save])
                
                st.cache_data.clear()
                st.success("Baza zaktualizowana pomyślnie!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    except Exception as e:
        st.error(f"Błąd połączenia: {e}")
