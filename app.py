import streamlit as st
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Configuración de Google API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credenciales.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Nombre del archivo en Google Sheets
SHEET_NAME = "registro_individual_horas"
sheet = client.open(SHEET_NAME).sheet1

# ───────────────────────────────────────────────
# Función para verificar y crear encabezados si es necesario
def verificar_encabezados():
    encabezados = [
        "Fecha", "Hora Entrada", "Hora Salida", "Recargo",
        "Horas Trabajadas", "Pago Base", "Pago con Recargo"
    ]
    
    # Obtener todos los datos de la hoja
    datos = sheet.get_all_values()
    
    # Si la hoja está vacía o no tiene encabezados, crearlos
    if not datos or datos[0] != encabezados:
        # Limpiar la hoja si tiene datos pero no los encabezados correctos
        if datos:
            sheet.clear()
        # Agregar los encabezados
        sheet.append_row(encabezados)
        return True
    return False

# Verificar encabezados al iniciar la aplicación
verificar_encabezados()
# ───────────────────────────────────────────────

st.title("🕒 Registro de horarios con recargos y cálculo de pago")

# Selección de fecha
fecha = st.date_input("Selecciona la fecha:", datetime.date.today())

# Función auxiliar para seleccionar hora en formato 12h
def seleccionar_hora(label, default_hour=8):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        hora = st.number_input(f"{label} - Hora", 1, 12, default_hour, key=f"{label}_hora")
    with col2:
        minuto = st.number_input(f"{label} - Minuto", 0, 59, 0, key=f"{label}_minuto")
    with col3:
        periodo = st.selectbox("AM/PM", ["AM", "PM"], key=f"{label}_periodo")

    # Convertir a 24h para cálculos
    if periodo == "PM" and hora != 12:
        hora_24 = hora + 12
    elif periodo == "AM" and hora == 12:
        hora_24 = 0
    else:
        hora_24 = hora
    return datetime.time(hora_24, minuto)

# ───────────────────────────────────────────────
# Entrada y salida (formato 12h)
st.subheader("⏰ Selecciona las horas")
hora_entrada = seleccionar_hora("Entrada", 8)
hora_salida = seleccionar_hora("Salida", 5)
# ───────────────────────────────────────────────

# Recargo
opciones_recargo = [0, 5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000]
recargo = st.selectbox("Recargo:", opciones_recargo, index=0,
                       format_func=lambda x: f"$ {x:,}" if x else "Ninguno")

# Calcular duración
entrada_dt = datetime.datetime.combine(datetime.date.today(), hora_entrada)
salida_dt = datetime.datetime.combine(datetime.date.today(), hora_salida)
diferencia = salida_dt - entrada_dt

# Convertir a formato hh:mm
total_segundos = diferencia.total_seconds()
horas = total_segundos / 3600
horas_int = int(total_segundos // 3600)
minutos = int((total_segundos % 3600) // 60)
horas_trabajadas = f"{horas_int:02d}:{minutos:02d}"

# ───────────────────────────────────────────────
# Cálculos según reglas
VALOR_HORA = 15500
BONO_6H = 100000

if horas < 6:
    pago_base = horas * VALOR_HORA
elif abs(horas - 6) < 0.01:  # tolerancia por redondeo
    pago_base = BONO_6H
else:
    horas_extra = horas - 6
    pago_base = BONO_6H + (horas_extra * VALOR_HORA)

pago_total = pago_base + recargo
# ───────────────────────────────────────────────

# Mostrar resultados
st.markdown(f"**Horas trabajadas:** {horas_trabajadas}")
st.markdown(f"**Pago base:** $ {pago_base:,.0f}")
st.markdown(f"**Pago total (con recargo):** $ {pago_total:,.0f}")

# ───────────────────────────────────────────────
# Guardar en Google Sheets
if st.button("Registrar horario"):
    # Verificar encabezados antes de guardar
    verificar_encabezados()
    
    # Preparar los datos para guardar
    fila = [
        str(fecha),
        hora_entrada.strftime("%I:%M %p"),
        hora_salida.strftime("%I:%M %p"),
        recargo,
        horas_trabajadas,
        f"$ {pago_base:,.0f}",
        f"$ {pago_total:,.0f}"
    ]
    
    # Guardar en Google Sheets
    sheet.append_row(fila)
    st.success("✅ Registro guardado correctamente en Google Sheets.")
    
    # Mostrar confirmación de lo guardado
    st.info(f"**Datos guardados:** {fila}")
# ───────────────────────────────────────────────