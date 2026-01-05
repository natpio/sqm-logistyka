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
    # ZMIANA: ttl=15 zamiast ttl=0. Dane będą odświeżane co 15 sekund, co drastycznie zmniejsza liczbę zapytań API.
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")

    if 'NOTATKA' not in df.columns:
        df['NOTATKA'] = ""
    df['NOTATKA'] = df['NOTATKA'].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")
    
    # Dodajemy przycisk ręcznego odświeżania, abyś mógł wymusić pobranie danych
    if st.button("🔄 ODSWIEŻ DANE (WYMUŚ)"):
        st.cache_data.clear()
        st.rerun()

    # --- WYSZUKIWARKA ---
    search = st.text_input("🔍 Wyszukaj transport:", placeholder="Wpisz frazę...")
    
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
                options=["W TRASIE", "POD RAMPĄ", "ROZŁADOWANY", "EMPTIES - ZAŁADUNEK", "ZAŁADOWANY NA POWRÓT", "status-planned"],
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja", disabled=True),
            "NOTATKA": st.column_config.TextColumn("📝 notatka dodatkowa", width="large"),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # --- PRZYCISK ZAPISU ---
    if st.button("💾 ZAPISZ ZMIANY W ARKUSZU", type="primary", use_container_width=True):
        with st.spinner("Zapisywanie..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                
                # Czyścimy cache po zapisie, aby od razu zobaczyć zmiany
                st.cache_data.clear()
                st.success("Dane zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    # --- SEKCJA PLIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj załącznik (CMR / Foto)")
    if not display_df.empty:
        selected_index = st.selectbox("Wybierz transport:", options=display_df.index.tolist())
        uploaded_file = st.file_uploader("Wybierz plik", type=['pdf', 'jpg', 'png', 'jpeg'])
        if st.button("📤 WYŚLIJ PLIK", use_container_width=True):
            if uploaded_file:
                with st.spinner("Przesyłanie..."):
                    try:
                        file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                        df.at[selected_index, 'Foto1'] = file_url
                        conn.update(spreadsheet=URL, data=df)
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Błąd: {ex}")

except Exception as e:
    # Obsługa błędu Quota w interfejsie
    if "429" in str(e):
        st.error("Przekroczono limit zapytań do Google Sheets. Poczekaj 60 sekund i spróbuj ponownie.")
    else:
        st.error(f"Wystąpił błąd: {e}")
