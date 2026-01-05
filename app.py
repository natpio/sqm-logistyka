import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide")

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_drive_service():
    # Pobieranie danych z Twoich NOWYCH Secrets
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=True)
    
    # supportsAllDrives=True pozwala zapisać plik na Twoim dysku firmowym
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Udostępnienie do podglądu
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- INTERFEJS ---
st.title("🚀 SQM Logistics Operations")

try:
    # Pobieranie danych (zawsze świeże - ttl=0)
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")
    
    # Rejestr z edycją statusu
    st.subheader("📋 Rejestr Transportowy")
    updated_df = st.data_editor(
        df,
        use_container_width=True,
        disabled=[col for col in df.columns if col != "STATUS"],
        column_config={"Foto1": st.column_config.LinkColumn("🔗 Dokumentacja")}
    )

    if not updated_df.equals(df):
        if st.button("💾 ZAPISZ ZMIANY STATUSÓW", type="primary"):
            conn.update(spreadsheet=URL, data=updated_df)
            st.success("Zmiany zapisane w arkuszu!")
            st.rerun()

    st.divider()

    # Formularz wysyłki plików
    st.subheader("📁 Dodaj załącznik (CMR / Foto)")
    if not df.empty:
        # Możesz wybrać wiersz po ID
        selected_index = st.selectbox("Wybierz transport do aktualizacji:", options=df.index.tolist(), 
                                      format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto']} | {df.loc[x, 'Nazwa Projektu']}")
        
        uploaded_file = st.file_uploader("Wybierz plik z komputera/telefonu", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        if st.button("📤 WYŚLIJ DOKUMENT", use_container_width=True):
            if uploaded_file:
                with st.spinner("Przesyłanie dokumentu na Google Drive..."):
                    try:
                        file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                        df.at[selected_index, 'Foto1'] = file_url
                        conn.update(spreadsheet=URL, data=df)
                        st.success("Plik przesłany i przypisany do transportu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd przesyłania: {e}")
            else:
                st.warning("Najpierw wskaż plik.")

except Exception as e:
    st.error(f"Błąd połączenia z bazą danych: {e}")
