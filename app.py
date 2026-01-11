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
        hr.truck-line { border: 0; height: 2px; background-image: linear-gradient(to right, rgba(0,0,0,0), rgba(0,0,0,0.75), rgba(0,0,0,0)); margin-top: 40px; }
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

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        if "USUŃ" not in df.columns:
            df["USUŃ"] = False

        # --- METRYKI ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🚚 W TRASIE", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("🔴 POD RAMPĄ", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("🟢 ROZŁADOWANE", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        p_fiz = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]['Auto'].unique()
        m4.metric("⚪ PUSTE AUTA", len(p_fiz))

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        column_cfg_base = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"], width="medium"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
            "NOTATKA DODATKOWA": None
        }

        # --- 6. FUNKCJA KAFELKÓW ---
        def render_grouped_tiles(dataframe):
            # ... (Logika kafelków pozostaje bez zmian jak w poprzednim kroku)
            for truck in dataframe['Auto'].unique():
                t_data = dataframe[dataframe['Auto'] == truck]
                st.markdown(f'<div class="truck-separator"><span>🚛 AUTO: <b>{truck}</b></span><span>{t_data.iloc[0]["Przewoźnik"]}</span></div>', unsafe_allow_html=True)
                cols = st.columns(3)
                for i, (_, row) in enumerate(t_data.iterrows()):
                    with cols[i % 3]:
                        s = str(row['STATUS']).upper()
                        c = "status-trasie" if "TRASIE" in s else "status-rampa" if "RAMP" in s else "status-rozladowany" if "ROZŁADOWANY" in s else "status-empties" if "EMPTIES" in s else "status-zaladowany" if "ZAŁADOWANY" in s else "status-pusty"
                        st.markdown(f'<div class="transport-card {c}"><b>[{row["Nr Proj."]}] {row["Nazwa Projektu"]}</b><br>📍 {row["Hala"]} | {row["Godzina"]}</div>', unsafe_allow_html=True)

        # --- 7. ZAKŁADKI ---
        t1, t2, t3, t4, t5 = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "⏰ SLOTY NA EMPTIES", "📚 BAZA"])
        
        st_ops = ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "ZAŁADOWANY NA POWRÓT"]
        edit_trackers = {}

        with t4:
            st.subheader("Nowa operacja Empties")
            # Pobieranie listy przewoźników dla wygody, ale bez przymusu
            df_p_src = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
            p_list = df_p_src.groupby('Przewoźnik').agg({'Auto': 'first', 'Kierowca': 'first'}).reset_index()

            with st.form("f_emp_v2", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nd = st.date_input("Data", datetime.now())
                    nh = st.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                    ns = st.text_input("Slot")
                with c2:
                    nt = st.text_input("Godzina")
                    np = st.selectbox("Przewoźnik (Opcjonalnie)", [""] + p_list['Przewoźnik'].tolist())
                    nst = st.selectbox("Status", st_ops)
                with c3:
                    nn = st.text_area("Notatka dodatkowa")
                    if st.form_submit_button("💾 ZAPISZ SLOT"):
                        fresh = conn.read(spreadsheet=URL, ttl="0s").dropna(how="all")
                        
                        # Jeśli wybrano przewoźnika, uzupełnij auto i kierowcę
                        v_auto, v_kier = "", ""
                        if np != "":
                            match = p_list[p_list['Przewoźnik'] == np]
                            if not match.empty:
                                v_auto = match.iloc[0]['Auto']
                                v_kier = match.iloc[0]['Kierowca']
                        
                        new_r = pd.DataFrame([{
                            'Data': str(nd), 'Nr Slotu': ns, 'Godzina': nt, 'Hala': nh, 
                            'Przewoźnik': np, 'Auto': v_auto, 'Kierowca': v_kier, 
                            'STATUS': nst, 'Nazwa Projektu': '--- OPERACJA EMPTIES ---', 
                            'NOTATKA DODATKOWA': nn, 'USUŃ': False
                        }])
                        conn.update(spreadsheet=URL, data=pd.concat([fresh, new_r], ignore_index=True))
                        st.cache_data.clear()
                        st.rerun()

            st.divider()
            df_s_v = df[df['STATUS'].isin(st_ops)].copy()
            if not df_s_v.empty:
                st.info("💡 Zaznacz 'USUŃ' przy wierszu i kliknij przycisk na dole strony, aby skasować slot.")
                ed_s = st.data_editor(
                    df_s_v[['USUŃ', 'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA DODATKOWA']], 
                    use_container_width=True, key="ed_s", hide_index=True,
                    column_config={"USUŃ": st.column_config.CheckboxColumn("🗑️")}
                )
                edit_trackers["ed_s"] = (df_s_v, ed_s)

        # Pozostałe zakładki (t1, t2, t3, t5) analogicznie...
        with t3:
            df_e = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)].copy()
            if not df_e.empty:
                df_e_g = df_e.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                ed_e = st.data_editor(df_e_g, use_container_width=True, key="ed_e", hide_index=True)
                edit_trackers["ed_e"] = (df_e_g, ed_e)

        for tab, key in zip([t1, t2, t5], ["in", "out", "all"]):
            with tab:
                src = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                if key == "in": m = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False)) & (~df['STATUS'].isin(st_ops))
                elif key == "out": m = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False)
                else: m = None
                
                df_v = df[m].copy() if m is not None else df.copy()
                if src: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]
                ed = st.data_editor(df_v, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_base, hide_index=True)
                edit_trackers[f"ed_{key}"] = (df_v, ed)

        # --- 8. ZAPIS I USUWANIE ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            f_df = df.copy()
            for k, (o_df, e_df) in edit_trackers.items():
                # Przenoszenie zmian z edytora do głównego DataFrame
                for i, row in e_df.iterrows():
                    orig_idx = o_df.index[i]
                    for col in e_df.columns:
                        if col in f_df.columns:
                            f_df.at[orig_idx, col] = row[col]

            # USUNIĘCIE WIERSZY ZAZNACZONYCH DO SKASOWANIA
            f_df = f_df[f_df['USUŃ'] != True]
            
            # Czyszczenie kolumn technicznych przed wysyłką do GSheets
            cols_to_save = [c for c in all_cols if c in f_df.columns]
            conn.update(spreadsheet=URL, data=f_df[cols_to_save])
            st.cache_data.clear()
            st.rerun()

    except Exception as e: st.error(f"Błąd: {e}")
