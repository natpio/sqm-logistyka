import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SETUP & THEME
st.set_page_config(page_title="SQM COMMAND CENTER", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
    /* Header & Stats */
    .main-title { font-size: 32px; font-weight: 900; letter-spacing: -1px; color: white; margin-bottom: 5px; }
    .status-bar { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 30px; }
    
    /* Truck Card - Glassmorphism style */
    .truck-card {
        background: #1c2128;
        border: 1px solid #30363d;
        border-left: 5px solid #58a6ff;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: 0.3s;
    }
    .truck-card:hover { border-color: #58a6ff; background: #21262d; }
    
    .truck-id { color: white; font-size: 20px; font-weight: bold; }
    .driver-info { color: #8b949e; font-size: 13px; }
    .slot-time { font-family: monospace; color: #58a6ff; font-weight: bold; font-size: 16px; }
    
    /* Scrollable Timeline */
    .scroll-container {
        display: flex;
        overflow-x: auto;
        gap: 15px;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. DATA LOAD
try:
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")

    # FIX: Standaryzacja typów danych
    df['Hala'] = df['Hala'].astype(str).replace('nan', '')
    df['Auto'] = df['Auto'].astype(str).replace('nan', 'BRAK MOCY')

    # 3. HEADER
    st.markdown('<div class="main-title">SQM LOGISTICS <span style="color:#58a6ff">TERMINAL</span></div>', unsafe_allow_html=True)
    
    # 4. FILTRY (Centrum Dowodzenia)
    with st.container():
        c1, c2, c3 = st.columns([2, 1, 1])
        search = c1.text_input("🔍 SEARCH SHIPMENT", placeholder="Enter Plate, Project or Driver...")
        
        # BEZPIECZNE SORTOWANIE HAL
        hale_list = sorted([h for h in df['Hala'].unique() if h.strip()])
        sel_hale = c2.multiselect("LOCATIONS", options=hale_list, default=hale_list)
        
        status_list = sorted(df['STATUS'].unique())
        sel_stats = c3.multiselect("STATUS", options=status_list, default=status_list)

    # Filtrowanie danych
    filtered_df = df[(df['Hala'].isin(sel_hale)) & (df['STATUS'].isin(sel_stats))]
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # 5. RENDER - MISSION CONTROL VIEW
    for h_name in sel_hale:
        st.markdown(f"### 📍 HALA {h_name}")
        h_df = filtered_df[filtered_df['Hala'] == h_name].sort_values(by="Godzina")
        
        if h_df.empty:
            st.caption("No active shipments for this location.")
            continue

        # Poziomy scroll dla naczep
        cols = st.columns(len(h_df) if len(h_df) < 5 else 4) # Max 4 kafelki w rzędzie, reszta niżej
        
        for idx, (_, row) in enumerate(h_df.iterrows()):
            with cols[idx % 4]:
                st.markdown(f"""
                    <div class="truck-card">
                        <div style="display:flex; justify-content:space-between;">
                            <span class="slot-time">⏰ {row['Godzina']}</span>
                            <span style="font-size:10px; color:#8b949e;">SLOT {row['Nr Slotu']}</span>
                        </div>
                        <div class="truck-id">{row['Auto']}</div>
                        <div class="driver-info">👤 {row['Kierowca']}</div>
                        <hr style="border:0; border-top:1px solid #30363d; margin:10px 0;">
                        <div style="font-size:14px; font-weight:bold; color:#f0f6fc;">{row['Nr Proj.']}</div>
                        <div style="font-size:12px; color:#8b949e;">{row['Nazwa Projektu']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Interakcja pod kafelkiem
                sub_c1, sub_c2 = st.columns(2)
                if "http" in str(row['spis casów']):
                    sub_c1.link_button("📋 LIST", row['spis casów'], use_container_width=True)
                if "http" in str(row['zdjęcie po załadunku']):
                    sub_c2.link_button("📸 FOTO", row['zdjęcie po załadunku'], use_container_width=True)

except Exception as e:
    st.error(f"CRITICAL ERROR: {e}")
