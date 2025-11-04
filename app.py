import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuración de Google API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

def get_credentials():
    try:
        if "google_sheets" not in st.secrets:
            st.error("❌ No se encontraron las credenciales en secrets.toml")
            return None
        
        secrets = st.secrets["google_sheets"]
        
        creds_dict = {
            "type": secrets["type"],
            "project_id": secrets["project_id"],
            "private_key_id": secrets["private_key_id"],
            "private_key": secrets["private_key"],
            "client_email": secrets["client_email"],
            "client_id": secrets["client_id"],
            "auth_uri": secrets["auth_uri"],
            "token_uri": secrets["token_uri"],
            "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": secrets["client_x509_cert_url"],
            "universe_domain": secrets.get("universe_domain", "googleapis.com")
        }
        
        return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        
    except Exception as e:
        st.error(f"❌ Error al cargar credenciales: {e}")
        return None

# Verificar conexión
st.title("🕒 Registro de horarios con recargos")

# Mostrar información de diagnóstico
with st.expander("🔧 Diagnóstico de conexión"):
    if "google_sheets" in st.secrets:
        st.success("✅ Secrets.toml encontrado")
        secrets = st.secrets["google_sheets"]
        st.write(f"**Project ID:** {secrets['project_id']}")
        st.write(f"**Client Email:** {secrets['client_email']}")
        st.write(f"**Spreadsheet:** {secrets['spreadsheet_name']}")
    else:
        st.error("❌ No se encontró la sección [google_sheets] en secrets.toml")

# Intentar conexión
creds = get_credentials()
if creds:
    try:
        client = gspread.authorize(creds)
        SHEET_NAME = st.secrets["google_sheets"]["spreadsheet_name"]
        sheet = client.open(SHEET_NAME).sheet1
        st.success("✅ Conectado exitosamente a Google Sheets")
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.info("""
        **Para solucionar este problema:**
        1. Verifica que hayas compartido la hoja 'registro_individual_horas' con el email: 
           `calculadora-salarios@calculadora-salarios.iam.gserviceaccount.com`
        2. Asegúrate de que la hoja exista y tenga ese nombre exacto
        3. Verifica que la API de Google Sheets esté habilitada
        """)
        st.stop()
else:
    st.stop()

# ───────────────────────────────────────────────
# Resto del código (igual que antes)
# ───────────────────────────────────────────────

def verificar_encabezados():
    encabezados = [
        "Fecha", "Hora Entrada", "Hora Salida", "Recargo",
        "Horas Trabajadas", "Pago Base", "Pago con Recargo"
    ]
    
    try:
        datos = sheet.get_all_values()
        if not datos or datos[0] != encabezados:
            if datos:
                sheet.clear()
            sheet.append_row(encabezados)
            return True
        return False
    except Exception as e:
        st.error(f"❌ Error al verificar encabezados: {e}")
        return False

# Verificar encabezados
try:
    if verificar_encabezados():
        st.info("📋 Encabezados creados exitosamente")
except Exception as e:
    st.error(f"❌ Error al verificar encabezados: {e}")

# Selección de fecha
fecha = st.date_input("Selecciona la fecha:", datetime.date.today())

def seleccionar_hora(label, default_hour=8):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        hora = st.number_input(f"{label} - Hora", 1, 12, default_hour, key=f"{label}_hora")
    with col2:
        minuto = st.number_input(f"{label} - Minuto", 0, 59, 0, key=f"{label}_minuto")
    with col3:
        periodo = st.selectbox("AM/PM", ["AM", "PM"], key=f"{label}_periodo")

    if periodo == "PM" and hora != 12:
        hora_24 = hora + 12
    elif periodo == "AM" and hora == 12:
        hora_24 = 0
    else:
        hora_24 = hora
    return datetime.time(hora_24, minuto)

st.subheader("⏰ Selecciona las horas")
hora_entrada = seleccionar_hora("Entrada", 8)
hora_salida = seleccionar_hora("Salida", 5)

# Recargo
opciones_recargo = [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]
recargo = st.selectbox("Recargo:", opciones_recargo, index=0,
                       format_func=lambda x: f"$ {x:,}" if x else "Ninguno")

# Cálculos
entrada_dt = datetime.datetime.combine(datetime.date.today(), hora_entrada)
salida_dt = datetime.datetime.combine(datetime.date.today(), hora_salida)
diferencia = salida_dt - entrada_dt

total_segundos = diferencia.total_seconds()
horas = total_segundos / 3600
horas_int = int(total_segundos // 3600)
minutos = int((total_segundos % 3600) // 60)
horas_trabajadas = f"{horas_int:02d}:{minutos:02d}"

VALOR_HORA = 15500
BONO_6H = 100000

if horas < 6:
    pago_base = horas * VALOR_HORA
elif abs(horas - 6) < 0.01:
    pago_base = BONO_6H
else:
    horas_extra = horas - 6
    pago_base = BONO_6H + (horas_extra * VALOR_HORA)

pago_total = pago_base + recargo

# Mostrar resultados
st.markdown(f"**Horas trabajadas:** {horas_trabajadas}")
st.markdown(f"**Pago base:** $ {pago_base:,.0f}")
st.markdown(f"**Pago total (con recargo):** $ {pago_total:,.0f}")

# Guardar en Google Sheets
if st.button("Registrar horario"):
    try:
        verificar_encabezados()
        
        fila = [
            str(fecha),
            hora_entrada.strftime("%I:%M %p"),
            hora_salida.strftime("%I:%M %p"),
            recargo,
            horas_trabajadas,
            f"$ {pago_base:,.0f}",
            f"$ {pago_total:,.0f}"
        ]
        
        sheet.append_row(fila)
        st.success("✅ Registro guardado correctamente en Google Sheets.")
        
    except Exception as e:
        st.error(f"❌ Error al guardar : {e}")