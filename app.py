import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide")

# Parametry stałe
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_drive_service():
    # Pobiera poświadczenia z Twoich nowych Secrets
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=True)
    
    # supportsAllDrives=True pozwala na zapis na Twoim firmowym dysku
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Publiczny link do podglądu dla pracowników
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- INTERFEJS ---
st.title("🚀 SQM Logistics Operations")

try:
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")
    
    # Edytor statusów
    st.subheader("📋 Rejestr Transportowy")
    updated_df = st.data_editor(
        df,
        use_container_width=True,
        disabled=[col for col in df.columns if col != "STATUS"],
        column_config={"Foto1": st.column_config.LinkColumn("🔗 Dokumentacja")}
    )

    if not updated_df.equals(df):
        if st.button("💾 ZAPISZ ZMIANY STATUSÓW"):
            conn.update(spreadsheet=URL, data=updated_df)
            st.success("Zaktualizowano arkusz!")
            st.rerun()

    st.divider()

    # Wysyłka plików
    st.subheader("📁 Dodaj załącznik")
    if not df.empty:
        selected_index = st.selectbox("Wybierz wiersz do aktualizacji:", options=df.index.tolist())
        uploaded_file = st.file_uploader("Wgraj plik (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        if st.button("📤 WYŚLIJ DOKUMENT"):
            if uploaded_file:
                with st.spinner("Przesyłanie..."):
                    try:
                        file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                        df.at[selected_index, 'Foto1'] = file_url
                        conn.update(spreadsheet=URL, data=df)
                        st.success("Plik wgrany pomyślnie!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd: {e}")
            else:
                st.warning("Najpierw wybierz plik.")

except Exception as e:
    st.error(f"Błąd połączenia: {e}")
