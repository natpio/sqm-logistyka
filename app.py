import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS dla profesjonalnego wyglądu
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJE GOOGLE DRIVE ---
def get_drive_service():
    # Pobieranie poświadczeń bezpośrednio z Secrets
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=True)
    
    # supportsAllDrives=True rozwiązuje problem braku miejsca (quota) na koncie serwisowym
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Udostępnienie pliku do wyświetlania
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

def load_data():
    return conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

# --- GŁÓWNA LOGIKA APLIKACJI ---
try:
    df = load_data()

    # NAGŁÓWEK
    st.title("🚀 SQM Logistics Operations")
    st.caption("Barcelona ↔ Poznań Hub | Zarządzanie dokumentacją i statusem")
    
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

    # --- FILTROWANIE ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("🔍 Wyszukaj transport...", placeholder="Auto, Projekt, Kierowca...")
    with c2:
        hala_filter = st.multiselect("Hala", options=df['Hala'].unique() if 'Hala' in df.columns else [])
    with c3:
        status_filter = st.multiselect("Status", options=df['STATUS'].unique() if 'STATUS' in df.columns else [])

    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if hala_filter:
        filtered_df = filtered_df[filtered_df['Hala'].isin(hala_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['STATUS'].isin(status_filter)]

    # --- TABELA I EDYCJA STATUSU ---
    st.subheader("📋 Rejestr Operacyjny")
    updated_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=False,
        disabled=[col for col in df.columns if col != "STATUS"], # Wszystko zablokowane prócz STATUS
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
                required=True,
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Plik")
        },
        key="main_editor"
    )

    if not updated_df.equals(filtered_df):
        if st.button("💾 ZATWIERDŹ ZMIANY STATUSÓW", type="primary", use_container_width=True):
            df.update(updated_df)
            conn.update(spreadsheet=URL, data=df)
            st.success("Statusy zsynchronizowane!")
            st.rerun()

    # --- SEKCJA PLIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj załącznik (CMR / Foto / PDF)")
    
    if not filtered_df.empty:
        transport_options = filtered_df.index.tolist()
        selected_index = st.selectbox(
            "Wybierz ID transportu (numer wiersza z tabeli powyżej):",
            options=transport_options,
            format_func=lambda x: f"ID: {x} | Auto: {df.loc[x, 'Auto']} | Projekt: {df.loc[x, 'Nazwa Projektu']}"
        )
        
        up_col, btn_col = st.columns([3, 1])
        with up_col:
            uploaded_file = st.file_uploader("Dodaj dokument", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        with btn_col:
            st.write("##")
            if st.button("📤 WYŚLIJ DOKUMENT", use_container_width=True):
                if uploaded_file:
                    with st.spinner(f"Wysyłanie do ID {selected_index}..."):
                        try:
                            # TWOJE ID FOLDERU SQM_Logistics_Files
                            FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno" 
                            
                            file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                            
                            # Aktualizacja kolumny Foto1 w Google Sheets
                            df.at[selected_index, 'Foto1'] = file_url
                            conn.update(spreadsheet=URL, data=df)
                            
                            st.success("Plik przesłany i przypisany do arkusza!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Błąd podczas operacji: {ex}")
                else:
                    st.warning("Najpierw wybierz plik z komputera/telefonu.")
    else:
        st.info("Brak transportów do wyświetlenia.")

except Exception as e:
    st.error(f"Błąd aplikacji: {e}")
