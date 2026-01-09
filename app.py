import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_cookies_controller import CookieController

# 1. AUTORYZACJA
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
        st.markdown("<h1 style='text-align: center; color: #1f77b4;'>SQM LOGISTICS SYSTEM</h1>", unsafe_allow_html=True)
        st.text_input("ACCESS CODE:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER PRO", layout="wide", initial_sidebar_state="collapsed")

    # 2. DESIGN SYSTEM (MILION DOLARÓW)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
        
        * { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #0e1117; }
        
        /* Panel filtrów - Glassmorphism */
        .filter-section {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 30px;
        }

        /* Nagłówek Dnia */
        .day-separator {
            color: #58a6ff;
            font-size: 14px;
            font-weight: 900;
            letter-spacing: 3px;
            text-transform: uppercase;
            margin: 40px 0 15px 10px;
            display: flex;
            align-items: center;
        }
        .day-separator::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, #58a6ff, transparent); margin-left: 20px; }

        /* Karta Naczepy */
        .truck-card-pro {
            background: linear-gradient(145deg, #161b22, #0d1117);
            border: 1px solid #30363d;
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 25px;
            transition: transform 0.2s ease;
        }
        .truck-card-pro:hover { border-color: #58a6ff; transform: translateY(-2px); }

        /* Projekt Row */
        .proj-box {
            background: rgba(255, 255, 255, 0.02);
            border-left: 4px solid #1f77b4;
            padding: 15px;
            border-radius: 12px;
            margin: 10px 0;
        }

        /* Statusy Neon */
        .st-pod-rampa { color: #ff7b72; border: 1px solid #ff7b72; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
        .st-w-trasie { color: #d29922; border: 1px solid #d29922; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
        .st-ok { color: #3fb950; border: 1px solid #3fb950; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
        
        /* Przyciski */
        .stButton button {
            background: #21262d !important;
            border: 1px solid #30363d !important;
            color: #c9d1d9 !important;
            border-radius: 12px !important;
            transition: all 0.3s !important;
        }
        .stButton button:hover {
            background: #30363d !important;
            border-color: #8b949e !important;
            color: #ffffff !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # 3. DATA ENGINE
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = df.reset_index(drop=True)
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None'], '').str.strip()

        # 4. HEADER
        st.markdown("<h1 style='color: white; font-weight: 900; margin-bottom: 0;'>SQM LOGISTICS <span style='color: #1f77b4;'>PRO</span></h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #8b949e; margin-bottom: 30px;'>COMMAND TOWER & FLEET MANAGEMENT</p>", unsafe_allow_html=True)

        # 5. COMMAND CENTER (FILTRY)
        st.markdown('<div class="filter-section">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1, 1])
        search = c1.text_input("🔍 SEARCH FLEET / PROJECT", placeholder="Type to filter...")
        hale = sorted(list(set(df['Hala'].unique())))
        sel_hale = c2.multiselect("LOCATIONS", options=hale, default=hale)
        stats = sorted(list(set(df['STATUS'].unique())))
        sel_stats = c3.multiselect("STATUS FILTER", options=stats, default=stats)
        st.markdown('</div>', unsafe_allow_html=True)

        # 6. PROCESSING
        f_df = df.copy()
        if search: f_df = f_df[f_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        f_df = f_df[f_df['STATUS'].isin(sel_stats)]
        f_df = f_df[f_df['Hala'].isin(sel_hale)]
        f_df = f_df.sort_values(by=['Data', 'Godzina'])

        # 7. MAIN RADAR DISPLAY
        dates = f_df['Data'].unique()
        for d in dates:
            st.markdown(f'<div class="day-separator">Operations Day: {d}</div>', unsafe_allow_html=True)
            day_df = f_df[f_df['Data'] == d]
            
            # Grupowanie po naczepie (Auto)
            for auto_nr in day_df['Auto'].unique():
                truck_projs = day_df[day_df['Auto'] == auto_nr]
                
                # Render karty naczepy
                with st.container():
                    st.markdown(f"""
                        <div class="truck-card-pro">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="color: #8b949e; font-size: 12px; font-weight: bold;">PLATE NUMBER</span>
                                    <div style="color: white; font-size: 24px; font-weight: 900;">{auto_nr}</div>
                                </div>
                                <div style="text-align: right;">
                                    <span style="color: #8b949e; font-size: 12px; font-weight: bold;">DRIVER</span>
                                    <div style="color: white; font-size: 16px; font-weight: bold;">{truck_projs.iloc[0]['Kierowca']}</div>
                                </div>
                            </div>
                            <div style="color: #1f77b4; font-size: 12px; font-weight: bold; margin-top: 5px;">
                                {truck_projs.iloc[0]['Przewoźnik'].upper()}
                            </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("")
                    
                    # Projekty na tej naczepie
                    for idx, row in truck_projs.iterrows():
                        # Dobór klasy statusu
                        s_up = row['STATUS'].upper()
                        s_class = "st-pod-rampa" if "RAMP" in s_up else "st-w-trasie" if "TRASIE" in s_up else "st-ok"
                        
                        st.markdown(f"""
                            <div class="proj-box">
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <div>
                                        <span class="slot-pill">SLOT {row['Nr Slotu']} | {row['Godzina']}</span>
                                        <div style="color: white; font-weight: bold; margin-top: 8px; font-size: 16px;">
                                            {row['Nr Proj.']} | {row['Nazwa Projektu']}
                                        </div>
                                        <div style="color: #8b949e; font-size: 13px;">📍 Location: HALA {row['Hala']}</div>
                                    </div>
                                    <div class="{s_class}">{row['STATUS']}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # High-End Buttons
                        b1, b2, b3, b4 = st.columns([1,1,1,2])
                        if "http" in row['zdjęcie po załadunku']: b1.link_button("📷 PHOTO", row['zdjęcie po załadunku'], use_container_width=True)
                        if "http" in row['spis casów']: b2.link_button("📋 MANIFEST", row['spis casów'], use_container_width=True)
                        if "http" in row['zrzut z currenta']: b3.link_button("🖼️ VIEW", row['zrzut z currenta'], use_container_width=True)
                        if row['NOTATKA']: 
                            with b4.expander("📝 INTEL"): st.caption(row['NOTATKA'])
                    
                    st.markdown("</div>", unsafe_allow_html=True) # Zamknięcie truck-card-pro

    except Exception as e:
        st.error(f"SYSTEM ERROR: {e}")

    # Logout w sidebarze (ukryty)
    with st.sidebar:
        if st.button("TERMINATE SESSION"):
            controller.remove("sqm_login_key")
            st.rerun()
