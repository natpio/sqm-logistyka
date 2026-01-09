import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# CONFIG & THEME 
st.set_page_config(page_title="SQM COMMAND CENTER", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Global Dark Aesthetics */
    .reportview-container { background: #0b0e11; }
    
    /* Stats Bar */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
    }

    /* Timeline Container */
    .timeline-track {
        display: flex;
        overflow-x: auto;
        padding: 20px 0;
        gap: 20px;
    }

    /* Luxury Truck Card */
    .luxury-card {
        min-width: 350px;
        background: linear-gradient(180deg, #1c2128 0%, #0d1117 100%);
        border-top: 4px solid #58a6ff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    /* Badge System */
    .badge {
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .badge-blue { background: #1f6feb; color: white; }
    .badge-amber { background: #d29922; color: black; }
    
    /* Project Detail */
    .proj-item {
        font-size: 13px;
        color: #c9d1d9;
        margin: 8px 0;
        padding-left: 10px;
        border-left: 2px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")

# --- UI HEADER ---
st.markdown("<h3 style='color: #8b949e; letter-spacing: 2px;'>FLEET COMMAND CENTER</h3>", unsafe_allow_html=True)

# Szybkie statystyki na górze (Dashboard Performance)
m1, m2, m3, m4 = st.columns(4)
with m1: st.markdown('<div class="metric-card"><span style="color:#8b949e">ACTIVE SLOTS</span><br><h2 style="color:white">14</h2></div>', unsafe_allow_html=True)
with m2: st.markdown('<div class="metric-card"><span style="color:#8b949e">IN TRANSIT</span><br><h2 style="color:#f9c000">6</h2></div>', unsafe_allow_html=True)
with m3: st.markdown('<div class="metric-card"><span style="color:#8b949e">UNLOADED</span><br><h2 style="color:#238636">28</h2></div>', unsafe_allow_html=True)
with m4: st.markdown('<div class="metric-card"><span style="color:#8b949e">EFFICIENCY</span><br><h2 style="color:#58a6ff">94%</h2></div>', unsafe_allow_html=True)

st.write("")

# --- WIDOK PER HALA (HORYZONTALNY TIMELINE) ---
hale = sorted(df['Hala'].unique())

for h in hale:
    st.markdown(f"#### 📍 LOCATION: HALA {h}")
    h_df = df[df['Hala'] == h].sort_values(by="Godzina")
    
    # Horyzontalny scroll dla naczep na danej hali
    st.markdown('<div class="timeline-track">', unsafe_allow_html=True)
    cols = st.columns(len(h_df) if len(h_df) > 0 else 1)
    
    for i, (_, row) in enumerate(h_df.iterrows()):
        with cols[i]:
            # Karta naczepy stylizowana na bilet/manifest
            st.markdown(f"""
                <div class="luxury-card">
                    <div style="display:flex; justify-content:space-between;">
                        <span class="badge badge-blue">SLOT {row['Nr Slotu']}</span>
                        <span style="color:#58a6ff; font-weight:bold;">{row['Godzina']}</span>
                    </div>
                    <div style="margin: 15px 0;">
                        <div style="color:white; font-size:20px; font-weight:900;">{row['Auto']}</div>
                        <div style="color:#8b949e; font-size:12px;">{row['Przewoźnik']}</div>
                    </div>
                    <div class="proj-item">
                        <b>{row['Nr Proj.']}</b><br>{row['Nazwa Projektu']}
                    </div>
                    <div style="margin-top:15px; font-size:11px; color:#484f58;">
                        👤 {row['Kierowca']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Action Buttons pod kartą
            btn_c1, btn_c2 = st.columns(2)
            btn_c1.button("📋 MANIFEST", key=f"m_{h}_{i}")
            btn_c2.button("📸 FOTO", key=f"p_{h}_{i}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
