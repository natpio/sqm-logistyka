import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

# Link do arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

# Połączenie
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

try:
    df = get_data()
    
    st.title("🚛 Operacje: Barcelona ↔ Poznań")
    st.markdown("---")

    # --- WIDOK KART (DLA KAŻDEGO AUTA) ---
    # Iterujemy przez wiersze arkusza
    for index, row in df.iterrows():
        # Stylizacja karty (wizualne oddzielenie aut)
        with st.container():
            col_info, col_action, col_photo = st.columns([2, 2, 2])
            
            with col_info:
                st.subheader(f"📍 {row.iloc[0]}") # Pierwsza kolumna (np. Numer auta)
                st.write(f"**Kierowca:** {row.get('Kierowca', 'Brak danych')}")
                st.write(f"**Slot:** {row.get('Slot', '---')}")
                current_status = row.get('Status', 'Nieokreślony')
                st.info(f"Obecny status: **{current_status}**")

            with col_action:
                st.write("**Zmień status:**")
                # Przyciski akcji - duże i wygodne
                if st.button(f"✅ ROZŁADOWANY", key=f"unl_{index}"):
                    df.at[index, 'Status'] = "ROZŁADOWANY"
                    conn.update(spreadsheet=URL, data=df)
                    st.success("Zapisano!")
                    st.rerun()
                
                if st.button(f"🏗️ ZAŁADOWANY / POWRÓT", key=f"load_{index}"):
                    df.at[index, 'Status'] = "ZAŁADOWANY"
                    conn.update(spreadsheet=URL, data=df)
                    st.success("Zapisano!")
                    st.rerun()

            with col_photo:
                st.write("**Zdjęcia załadunku:**")
                uploaded_file = st.file_uploader("Dodaj zdjęcie (JPG/PNG)", type=['png', 'jpg', 'jpeg'], key=f"img_{index}")
                if uploaded_file:
                    st.image(uploaded_file, width=150)
                    if st.button("Wyślij zdjęcie", key=f"send_{index}"):
                        # Tutaj logistyka zapisu - na razie potwierdzenie
                        st.success("Zdjęcie wysłane do bazy (Poznań)")

            st.markdown("---") # Linia oddzielająca auta

except Exception as e:
    st.error(f"Problem z arkuszem: {e}")
    st.info("Sprawdź czy kolumny w Sheets nazywają się dokładnie: 'Kierowca', 'Slot', 'Status'")
