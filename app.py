import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS dla wyglądu operacyjnego
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJE GOOGLE DRIVE (Obsługa plików) ---
def get_drive_service():
    creds = conn._instance._creds
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=True)
    uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    
    service.permissions().create(fileId=uploaded_file.get('id'), body={'type': 'anyone', 'role': 'viewer'}).execute()
    return uploaded_file.get('webViewLink')

def load_data():
    # Pobieramy dane i dodajemy pomocniczą kolumnę z ID (numerem wiersza)
    data = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")
    return data

# --- GŁÓWNA LOGIKA APLIKACJI ---
try:
    df = load_data()

    # NAGŁÓWEK OPERACYJNY
    col_t, col_s = st.columns([3, 1])
    with col_t:
        st.title("🚀 SQM Logistics Operations")
        st.caption("Zarządzanie transportem i dokumentacją | Barcelona ↔ Poznań Hub")
    
    # KPI
    total = len(df)
    in_transit = len(df[df['STATUS'] == 'w trasie'])
    unloaded = len(df[df['STATUS'] == 'ROZŁADOWANY'])
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Wszystkie transporty", total)
    kpi2.metric("W trasie", in_transit)
    kpi3.metric("Rozładowane", unloaded, delta=f"{int(unloaded/total*100) if total > 0 else 0}%")
    kpi4.metric("Pod rampą", len(df[df['STATUS'] == 'pod rampą']))

    st.divider()

    # --- PANEL FILTROWANIA ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("🔍 Wyszukaj (Auto, Kierowca, Projekt...)", placeholder="Wpisz szukaną frazę...")
    with c2:
        hala_filter = st.multiselect("Hala", options=df['Hala'].unique())
    with c3:
        status_filter = st.multiselect("Status", options=df['STATUS'].unique())

    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if hala_filter:
        filtered_df = filtered_df[filtered_df['Hala'].isin(hala_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['STATUS'].isin(status_filter)]

    # --- EDYCJA STATUSÓW ---
    st.subheader("📋 Rejestr Transportowy")
    
    updated_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=False, # Pokazujemy index jako ID wiersza
        disabled=["Data", "Nr Slotu", "Godzina", "Hala", "Przewoźnik", "Auto", "Kierowca", "Nr Proj.", "Nazwa Projektu", "Foto1"],
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
                required=True,
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja")
        },
        key="main_editor"
    )

    if not updated_df.equals(filtered_df):
        if st.button("💾 ZATWIERDŹ ZMIANY STATUSÓW", type="primary", use_container_width=True):
            df.update(updated_df)
            conn.update(spreadsheet=URL, data=df)
            st.success("Statusy zaktualizowane!")
            st.rerun()

    # --- SEKCJA PRZESYŁANIA PLIKÓW (G-DRIVE) PO NUMERZE WIERSZA (ID) ---
    st.divider()
    st.subheader("📁 Dodaj załącznik (CMR / Zdjęcie / PDF)")
    
    if not filtered_df.empty:
        # POBIERAMY INDEXY Z PRZEFILTROWANEJ TABELI
        transport_options = filtered_df.index.tolist()
        
        # WYBÓR PO ID (INDEXIE)
        selected_index = st.selectbox(
            "Wybierz ID transportu (numer wiersza):",
            options=transport_options,
            format_func=lambda x: f"ID: {x} | Auto: {df.loc[x, 'Auto']} | Projekt: {df.loc[x, 'Nazwa Projektu']}"
        )
        
        up_col, btn_col = st.columns([3, 1])
        with up_col:
            uploaded_file = st.file_uploader("Wybierz plik dokumentacji", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        with btn_col:
            st.write("##")
            if st.button("📤 WYŚLIJ DOKUMENT", use_container_width=True):
                if uploaded_file:
                    with st.spinner(f"Przesyłanie dla transportu ID {selected_index}..."):
                        try:
                            # --- WPISZ TUTAJ SWOJE ID FOLDERU ---
                            FOLDER_ID = "WPISZ_TUTAJ_ID_FOLDERU" 
                            
                            file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                            
                            # Precyzyjny zapis do wiersza o konkretnym ID
                            df.at[selected_index, 'Foto1'] = file_url
                            conn.update(spreadsheet=URL, data=df)
                            
                            st.success(f"Plik przypisany do wiersza ID {selected_index}!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Błąd: {ex}")
                else:
                    st.warning("Najpierw wskaż plik.")
    else:
        st.info("Brak transportów w widoku.")

except Exception as e:
    st.error(f"Krytyczny błąd: {e}")
