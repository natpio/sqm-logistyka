import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM Logistics: POZ-BCN", layout="centered")

# 1. Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Pobranie danych (zastąp URL swoim linkiem do arkusza z uprawnieniami "każdy z linkiem może edytować")
URL = "TU_WKLEJ_LINK_DO_TWOJEGO_ARKUSZA"
df = conn.read(spreadsheet=URL, usecols=[0, 1, 2, 3]) # Czyta pierwsze 4 kolumny

st.title("🚛 SQM: Operacje Barcelona")

# --- WIDOK DLA LOGISTYKA W TERENIE ---
st.subheader("Lista aut do obsługi")
for index, row in df.iterrows():
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.write(f"**{row['ID_Auta']}** ({row['Kierowca']})")
        col2.write(f"Slot: {row['Slot']}")
        
        # Przycisk zmiany statusu
        if col3.button("✅ Rozładowany", key=f"btn_{index}"):
            # Aktualizacja statusu w DataFrame
            df.at[index, 'Status'] = "ROZŁADOWANY"
            conn.update(spreadsheet=URL, data=df)
            st.success(f"Zaktualizowano {row['ID_Auta']}")
            st.rerun()
        st.divider()

# --- SEKCJA ZDJĘĆ ---
st.subheader("📸 Dokumentacja załadunku")
uploaded_file = st.camera_input("Zrób zdjęcie naczepy") # Otwiera aparat w telefonie

if uploaded_file:
    # W logistyce targowej zdjęcia najlepiej wysyłać na dedykowany folder Google Drive lub Dropbox
    # Tutaj uproszczona informacja:
    st.info("Zdjęcie gotowe do wysłania. W wersji docelowej zostanie przypisane do auta w Arkuszu.")
    # Logika zapisu pliku (np. przez API Google Drive)
