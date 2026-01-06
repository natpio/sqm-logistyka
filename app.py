import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# --- STYLIZACJA (Opcjonalne logo lub nagłówek) ---
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")
    
    # Naprawa danych
    all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
    for col in all_cols:
        if col not in df.columns: df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    # --- SEKCJA KPI ---
    st.title("🚀 SQM Logistics Operations")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Suma aut", len(df))
    with m2: st.metric("Pod rampą", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
    with m3: st.metric("W trasie", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
    with m4: st.metric("Zakończone", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

    st.divider()

    # --- TABELA ---
    updated_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=[
                    "🟡 W TRASIE", 
                    "🔴 POD RAMPĄ", 
                    "🟢 ROZŁADOWANY", 
                    "📦 EMPTIES - ZAŁADUNEK", 
                    "🚚 ZAŁADOWANY NA POWRÓT", 
                    "⚪ status-planned"
                ]
            ),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large"),
        }
    )

    if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
        conn.update(spreadsheet=URL, data=updated_df)
        st.cache_data.clear()
        st.success("Dane zsynchronizowane!")
        st.rerun()

except Exception as e:
    st.error(f"Błąd: {e}")
