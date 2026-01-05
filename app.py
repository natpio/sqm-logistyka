import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_drive_service():
    # Wykorzystuje dane uwierzytelniające z Secrets
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=False)
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    return uploaded_file.get('webViewLink')

# --- LOGIKA APLIKACJI ---
try:
    # 1. Pobieramy dane
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

    # 2. NAPRAWA I DOPASOWANIE KOLUMN
    # Jeśli kolumna NOTATKA nie istnieje w Sheets, tworzymy ją tymczasowo, żeby edytor nie zgłosił błędu
    if 'NOTATKA' not in df.columns:
        df['NOTATKA'] = ""
    
    # Wymuszamy typ tekstowy, aby uniknąć błędów FLOAT przy edycji
    df['NOTATKA'] = df['NOTATKA'].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")
    st.info("💡 Kliknij dwukrotnie w komórkę, aby edytować. Użyj '+' na dole tabeli, aby dodać nowy wiersz.")

    # Wyszukiwarka
    search = st.text_input("🔍 Wyszukaj transport (Auto, Projekt, Hala...):")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- EDYTOR DANYCH ---
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=False,
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja", disabled=True),
            
            # ZMIANA NAZWY NA: notatka dodatkowa
            "NOTATKA": st.column_config.TextColumn(
                "📝 notatka dodatkowa", 
                width="large"
            ),
            
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # PRZYCISK ZAPISU
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Zapisywanie w Google Sheets..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                st.success("Dane zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    # --- SEKCJA PLIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj załącznik (CMR / Foto / PDF)")
    
    if not display_df.empty:
        selected_index = st.selectbox(
            "Wybierz transport do przypisania pliku:",
            options=display_df.index.tolist(),
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto'] if x in df.index else 'NOWY'}"
        )
        
        uploaded_file = st.file_uploader("Wgraj dokumentację", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        if st.button("📤 WYŚLIJ NA DRIVE", use_container_width=True):
            if uploaded_file:
                with st.spinner("Przesyłanie..."):
                    try:
                        file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                        df.at[selected_index, 'Foto1'] = file_url
                        conn.update(spreadsheet=URL, data=df)
                        st.success("Plik przesłany!")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Błąd przesyłania: {ex}")

except Exception as e:
    st.error(f"Wystąpił błąd krytyczny aplikacji: {e}")
