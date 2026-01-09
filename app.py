import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM VISUAL YARD", layout="wide")

# --- STYLE MAPY (UX POZIOM 99) ---
st.markdown("""
    <style>
    .slot-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        padding: 10px;
    }
    .slot-box {
        height: 180px;
        border-radius: 15px;
        border: 2px solid #333;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 15px;
        position: relative;
        background: #111;
    }
    .slot-number { font-size: 12px; color: #888; font-weight: bold; }
    .truck-plate { font-size: 22px; font-weight: 900; color: white; text-align: center; margin-top: 10px; }
    .status-bar { height: 8px; border-radius: 4px; width: 100%; }
    
    /* STATUSY WIZUALNE */
    .bg-ramp { background: linear-gradient(145deg, #441111, #aa0000); border-color: #ff4b4b; }
    .bg-transit { background: linear-gradient(145deg, #332b00, #887700); border-color: #f9c000; }
    .bg-done { background: #050505; border: 1px dashed #333; opacity: 0.5; }
    .bg-empty { background: #0a0a0a; border: 1px dashed #222; }
    </style>
    """, unsafe_allow_html=True)

# --- SILNIK DANYCH ---
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(spreadsheet=URL, ttl="1m")

# Wybór dnia i hal do wyświetlenia
st.title("🛰️ SQM YARD CONTROL")
t1, t2 = st.columns(2)
day = t1.selectbox("DZIEŃ:", df['Data'].unique())
selected_hala = t2.selectbox("HALA:", sorted(df['Hala'].unique()))

day_df = df[(df['Data'] == day) & (df['Hala'] == selected_hala)]

# --- RENDER MAPY SLOTÓW ---
st.subheader(f"📍 Podgląd na żywo: HALA {selected_hala}")

# Tworzymy siatkę slotów (np. od 1 do 10 lub na podstawie danych)
max_slots = 12 # Możesz to zautomatyzować
cols = st.columns(4) # 4 sloty w rzędzie

for i in range(1, max_slots + 1):
    slot_str = str(i)
    # Szukamy czy w tym slocie jest auto
    truck = day_df[day_df['Nr Slotu'].astype(str) == slot_str]
    
    with cols[(i-1) % 4]:
        if not truck.empty:
            row = truck.iloc[0]
            status = str(row['STATUS']).upper()
            
            # Klasa stylu na podstawie statusu
            style_class = "bg-transit"
            if "RAMP" in status: style_class = "bg-ramp"
            if "ROZŁADOWANY" in status: style_class = "bg-done"
            
            st.markdown(f"""
                <div class="slot-box {style_class}">
                    <div class="slot-number">SLOT {slot_str} • {row['Godzina']}</div>
                    <div class="truck-plate">{row['Auto']}</div>
                    <div style="font-size: 11px; color: #ddd; text-align: center;">{row['Kierowca']}</div>
                    <div style="font-size: 10px; font-weight: bold; color: white; text-align: center; background: rgba(0,0,0,0.3); border-radius: 5px;">{status}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Przyciski pod slotem
            if "ROZŁADOWANY" not in status:
                st.button(f"Zwolnij Slot {slot_str}", key=f"btn_{i}", use_container_width=True)
        else:
            st.markdown(f"""
                <div class="slot-box bg-empty">
                    <div class="slot-number">SLOT {slot_str}</div>
                    <div class="truck-plate" style="color: #222; font-size: 14px;">WOLNY</div>
                </div>
            """, unsafe_allow_html=True)
