import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")

# --- 2. AUTORYZACJA I PAMIĘĆ LOGOWANIA (COOKIES) ---
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
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        
        /* Styl Kontenera Grupy Auta */
        .truck-group {
            background-color: #f1f3f6;
            padding: 15px;
            border-radius: 15px;
            margin-bottom: 25px;
            border: 1px dashed #bfc9d4;
        }
        .truck-header {
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        }

        /* Styl Kafelka Projektu */
        .transport-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        
        .notatka-display { 
            background-color: #fff3cd; 
            padding: 20px; 
            border-radius: 10px; 
            border-left: 10px solid #ffc107; 
            margin: 15px 0;
            font-size: 18px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Widok")
        view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
        st.divider()
        if st.button("Wyloguj"):
            controller.remove("sqm_login_key")
            st.rerun()

    # --- 5. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Konfiguracja dla edytora
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"], width="medium"),
        "spis casów": st.column_config.LinkColumn("📋 Spis"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
        "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT"),
        "PODGLĄD": st.column_config.CheckboxColumn("👁️"),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
    }

    # --- FUNKCJA RENDEROWANIA GRUPOWANEGO ---
    def render_grouped_tiles(dataframe):
        if dataframe.empty:
            st.info("Brak danych.")
            return
        
        # Grupowanie po aucie (rejestracji)
        trucks = dataframe['Auto'].unique()
        
        for truck in trucks:
            truck_data = dataframe[dataframe['Auto'] == truck]
            carrier = truck_data.iloc[0]['Przewoźnik']
            
            # Kontener dla auta
            st.markdown(f"""
                <div class="truck-header">🚛 AUTO: {truck} <span style="font-size:0.7em; color:gray; margin-left:15px;">(Przewoźnik: {carrier})</span></div>
            """, unsafe_allow_html=True)
            
            # Wyświetlamy kafelki ładunków pod tym autem w kolumnach
            t_cols = st.columns(3)
            for idx, (_, row) in enumerate(truck_data.iterrows()):
                with t_cols[idx % 3]:
                    s = str(row['STATUS']).upper()
                    s_class = ""
                    if "TRASIE" in s: s_class = "status-trasie"
                    elif "RAMP" in s: s_class = "status-rampa"
                    elif "ROZŁADOWANY" in s: s_class = "status-rozladowany"
                    elif "EMPTIES" in s: s_class = "status-empties"
                    elif "ZAŁADOWANY" in s: s_class = "status-zaladowany"

                    st.markdown(f"""
                        <div class="transport-card {s_class}">
                            <div style="font-size: 0.8em; color: #666;">{row['Data']} | Slot: {row['Nr Slotu']}</div>
                            <div style="font-weight: bold; font-size: 1.1em; color: #1f77b4; margin: 5px 0;">
                                [{row['Nr Proj.']}] {row['Nazwa Projektu']}
                            </div>
                            <div style="font-size: 0.9em; margin-bottom: 8px;">
                                👤 {row['Kierowca']}<br>
                                📍 Hala: {row['Hala']} | Godz: {row['Godzina']}
                            </div>
                            <div style="font-weight: bold; text-align: center; background: #eee; border-radius: 4px; padding: 2px;">{row['STATUS']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if row['spis casów']: st.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                        if row['SLOT']: st.link_button("⏰ Slot", row['SLOT'], use_container_width=True)
                    with b2:
                        if row['zdjęcie po załadunku']: st.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                        if row['zrzut z currenta']: st.link_button("🖼️ Current", row['zrzut z currenta'], use_container_width=True)
                    
                    with st.expander("📝 Notatka"):
                        st.write(row['NOTATKA'] if row['NOTATKA'] else "Brak")
            st.markdown("<br>", unsafe_allow_html=True)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        st.title("🏗️ SQM Control Tower")
        
        # Metryki
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        tabs = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])
        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"
        edit_trackers = {}

        for tab, mask, key in zip(tabs, [~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False), df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False), None], ["in", "out", "full"]):
            with tab:
                c1, c2, c3 = st.columns([1.5, 2, 1])
                with c1:
                    if key == "in":
                        d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                        all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                with c3:
                    st.write("###")
                    if st.button("🔄 Odśwież", key=f"r_{key}"):
                        st.cache_data.clear()
                        st.rerun()

                df_view = df[mask].copy() if mask is not None else df.copy()
                if key == "in" and not all_d:
                    df_view['Data_dt'] = pd.to_datetime(df_view['Data'], errors='coerce')
                    df_view = df_view[df_view['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
                if search:
                    df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                if view_mode == "Tradycyjny":
                    ed = st.data_editor(df_view, use_container_width=True, key=f"ed_{key}", column_config=column_cfg)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)
                    # Podgląd notatki pod tabelą
                    sel = ed[ed["PODGLĄD"] == True]
                    if not sel.empty:
                        row = sel.iloc[-1]
                        st.markdown(f'<div class="notatka-display"><b>[{row["Nr Proj."]}] {row["Nazwa Projektu"]}</b><br>{row["NOTATKA"]}</div>', unsafe_allow_html=True)
                else:
                    render_grouped_tiles(df_view)

        if view_mode == "Tradycyjny":
            st.divider()
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k in edit_trackers:
                    s_df, e_df = edit_trackers[k]
                    changes = st.session_state[k].get("edited_rows", {})
                    for r_idx_str, col_ch in changes.items():
                        real_idx = s_df.index[int(r_idx_str)]
                        for col, val in col_ch.items(): final_df.at[real_idx, col] = val
                
                if "PODGLĄD" in final_df.columns: final_df = final_df.drop(columns=["PODGLĄD"])
                conn.update(spreadsheet=URL, data=final_df)
                st.cache_data.clear()
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd bazy: {e}")
