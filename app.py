import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. KONFIGURACJA STRONY I NOWA STYLIZACJA
# ==========================================
st.set_page_config(
    page_title="SQM LOGISTICS PRO", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Naprawione style CSS - tła i ramki dla dashboardu
st.markdown("""
    <style>
    /* Kontener dla każdej metryki */
    div[data-testid="stMetric"] {
        background-color: #f8f9fb;
        border: 1px solid #e0e0e0;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    /* Kolor samej liczby */
    div[data-testid="stMetricValue"] > div {
        color: #1f77b4;
        font-weight: bold;
    }
    /* Odstępy między kolumnami metryk */
    [data-testid="column"] {
        padding: 0 10px;
    }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. POBIERANIE I NAPRAWA DANYCH
# ==========================================
try:
    df = conn.read(spreadsheet=URL, ttl=10).dropna(how="all")

    all_cols = [
        'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 
        'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 
        'STATUS', 'spis casów', 'zdjęcie po załadunku', 
        'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
    ]
    
    for col in all_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    # ==========================================
    # 3. DASHBOARD Z TŁEM
    # ==========================================
    st.title("🚀 SQM Logistics Operations")
    
    total_trucks = len(df)
    under_ramp = len(df[df['STATUS'].str.contains("RAMP", na=False)])
    in_transit = len(df[df['STATUS'].str.contains("TRASIE", na=False)])
    completed = len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Wszystkie transporty", total_trucks)
    m2.metric("Pod rampą 🔴", under_ramp)
    m3.metric("W trasie 🟡", in_transit)
    m4.metric("Zakończone 🟢", completed)

    st.markdown("---")

    # Sekcja wyszukiwania
    c1, c2 = st.columns([4, 1])
    with c1:
        search = st.text_input("🔍 Wyszukaj transport:", placeholder="Nr rejestracyjny, projekt...")
    with c2:
        st.write("##")
        if st.button("🔄 Odśwież dane", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # ==========================================
    # 4. EDYTOR DANYCH
    # ==========================================
    updated_df = st.data_editor(
        display_df,
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
                ],
                required=True
            ),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large"),
        }
    )

    # ==========================================
    # 5. ZAPIS
    # ==========================================
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Zapisywanie..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                st.cache_data.clear()
                st.success("Dane zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

except Exception as e:
    st.error(f"Błąd: {e}")
