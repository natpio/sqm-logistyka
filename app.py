import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNKCJE GOOGLE DRIVE ---
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

# --- 3. GŁÓWNA LOGIKA APLIKACJI ---
try:
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")

    # --- NAPRAWA TYPÓW DANYCH (KLUCZOWE) ---
    # Naprawa dla NOTATKI
    if 'NOTATKA' not in df.columns:
        df['NOTATKA'] = ""
    df['NOTATKA'] = df['NOTATKA'].astype(str).replace('nan', '')

    # NAPRAWA BŁĘDU ColumnDataKind.FLOAT dla Foto1:
    if 'Foto1' not in df.columns:
        df['Foto1'] = ""
    # Wymuszamy, aby Foto1 zawsze było tekstem (String), co pozwala na użycie LinkColumn
    df['Foto1'] = df['Foto1'].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")
    
    if st.button("🔄 ODSWIEŻ DANE (WYMUŚ)"):
        st.cache_data.clear()
        st.rerun()

    search = st.text_input("🔍 Wyszukaj (Auto, Projekt, Hala...):", placeholder="Szukaj...")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- 4. EDYTOR DANYCH ---
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=False,
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["W TRASIE", "POD RAMPĄ", "ROZŁADOWANY", "EMPTIES - ZAŁADUNEK", "ZAŁADOWANY NA POWRÓT", "status-planned"],
                required=True
            ),
            "Foto1": st.column_config.LinkColumn(
                "🔗 Dokumentacja", 
                display_text="Otwórz plik",
                help="Wklej link do Drive lub użyj sekcji poniżej"
            ),
            "NOTATKA": st.column_config.TextColumn(
                "📝 notatka dodatkowa", 
                width="large"
            ),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

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

    # --- 5. SEKCJA ZAŁĄCZNIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj dokumentację do transportu")
    
    if not display_df.empty:
        selected_index = st.selectbox(
            "Wybierz transport:",
            options=display_df.index.tolist(),
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto'] if 'Auto' in df.columns else 'NOWY'}"
        )
        
        uploaded_file = st.file_uploader("Wgraj plik", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        if st.button("📤 WYŚLIJ I PODLINKUJ", use_container_width=True):
            if uploaded_file:
                with st.spinner("Przesyłanie..."):
                    try:
                        file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                        df.at[selected_index, 'Foto1'] = file_url
                        conn.update(spreadsheet=URL, data=df)
                        st.cache_data.clear()
                        st.success("Gotowe! Link dodany.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Błąd: {ex}")

except Exception as e:
    if "429" in str(e):
        st.error("Limit Google Sheets. Poczekaj minutę.")
    else:
        st.error(f"Błąd: {e}")
