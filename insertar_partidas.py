import streamlit as st
import urllib.request
import urllib.parse
import json
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = "https://supabase.co"
# IMPORTANTE: Cambia esto por tu clave de Supabase. 
# Si tienes políticas RLS estrictas, usa la clave 'service_role'.
SUPABASE_KEY = "TU_SUPABASE_ANON_OR_SERVICE_KEY" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"  # Permite que Supabase devuelva el ID creado inmediatamente
}

st.set_page_config(page_title="Introducir Partidas - Liga Mahjong Madrid", page_icon="🎴")
st.title("🀄 Introducir Nueva Partida")

# ==========================================
# FUNCIONES DE CONEXIÓN (URLLIB)
# ==========================================
@st.cache_data(ttl=60)  # Cachea los jugadores 1 minuto para evitar llamadas constantes
def obtener_jugadores():
    """Trae la lista de jugadores ordenados por nombre."""
    try:
        url = f"{SUPABASE_URL}/jugadores?select=id,nombre&order=nombre.asc"
        req = urllib.request.Request(url, headers=HEADERS, method="GET")
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        st.error(f"Error al cargar jugadores de la base de datos: {e}")
        return []

def insertar_registro(tabla, datos):
    """Inserta datos en la tabla indicada y devuelve la respuesta JSON."""
    try:
        url = f"{SUPABASE_URL}/{tabla}"
        data_json = json.dumps(datos).encode("utf-8")
        req = urllib.request.Request(url, data=data_json, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        st.error(f"Error al insertar en la tabla '{tabla}': {e}")
        return None

# ==========================================
# CARGA DE DATOS INICIALES
# ==========================================
lista_jugadores = obtener_jugadores()

if not lista_jugadores:
    st.warning("No se pudieron recuperar los jugadores. Verifica la configuración de Supabase.")
    st.stop()

# Crear un diccionario para mapear "Nombre del Jugador" -> ID
dict_jugadores = {j["nombre"]: j["id"] for j in lista_jugadores}
nombres_para_combo = list(dict_jugadores.keys())

# ==========================================
# FORMULARIO DE ENTRADA
# ==========================================
with st.form("formulario_partida", clear_on_submit=False):
    st.subheader("1. Datos Generales de la Partida")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_juego = st.radio("Tipo de Juego:", ["RIICHI", "MCR"], horizontal=True)
    with col2:
        # Temporada fijada según tus instrucciones
        temporada = st.text_input("Temporada:", value="Oct 2026 - Sept 2027", disabled=True)
        
    fecha = st.date_input("Fecha de la partida:", datetime.today())
    nombre_partida = st.text_input("Nombre de la partida:", placeholder="Ej: RIICHI-20261003-Mesa 1")
    
    st.markdown("---")
    st.subheader("2. Resultados de los Jugadores")
    
    # Determinar dinámicamente la cantidad de jugadores permitidos
    num_jugadores = 4 if tipo_juego == "RIICHI" else st.number_input("Número de jugadores para MCR:", min_value=4, max_value=5, value=4, step=1)
    
    st.info("Introduce los jugadores y sus puntuaciones. Las posiciones se asignarán automáticamente según el orden (1º al último).")
    
    # Listas vacías para almacenar las selecciones del formulario
    jugadores_seleccionados = []
    puntuaciones = []
    
    # Generar dinámicamente las entradas del 1º al 4º o 5º puesto
    for i in range(int(num_jugadores)):
        st.markdown(f"**Posición {i+1}**")
        c1, c2 = st.columns([2, 1])
        
        with c1:
            # Ponemos un índice por defecto diferente para cada combo para agilizar la entrada
            idx_defecto = min(i, len(nombres_para_combo) - 1)
            jugador = st.selectbox(
                f"Selecciona al jugador {i+1}:", 
                nombres_para_combo, 
                index=idx_defecto, 
                key=f"jugador_{i}"
            )
            jugadores_seleccionados.append(jugador)
            
        with c2:
            puntos = st.number_input(
                f"Puntuación {i+1}:", 
                value=0, 
                step=100 if tipo_juego == "RIICHI" else 1, 
                key=f"puntos_{i}"
            )
            puntuaciones.append(puntos)

    # Botón de envío del formulario
    enviar = st.form_submit_button("Guardar Partida y Resultados en Supabase")

# ==========================================
# PROCESAMIENTO Y ENVÍO A SUPABASE
# ==========================================
if enviar:
    # --- Validaciones previas ---
    if not nombre_partida.strip():
        st.error("Por favor, introduce un nombre para la partida.")
        st.stop()
        
    if len(jugadores_seleccionados) != len(set(jugadores_seleccionados)):
        st.error("Error: No puedes seleccionar al mismo jugador en múltiples posiciones.")
        st.stop()
        
    # --- Paso 1: Insertar en la tabla 'partidas' ---
    datos_partida = {
        "fecha": str(fecha),
        "tipo_juego": tipo_juego,
        "nombre": nombre_partida.strip(),
        "temporada": "Oct 2026 - Sept 2027"  # La forzamos en el backend también
    }
    
    with st.spinner("Guardando los datos de la partida..."):
        respuesta_partida = insertar_registro("partidas", datos_partida)
        
    if respuesta_partida and len(respuesta_partida) > 0:
        # Extraemos el ID generado automáticamente por Postgres
        partida_id_generado = respuesta_partida[0]["id"]
        st.success(f"✓ Partida guardada con éxito (ID: {partida_id_generado})")
        
        # --- Paso 2: Insertar en la tabla 'resultados_partidas' ---
        registros_resultados = []
        
        # Recorremos el orden que ingresó el usuario
        for i in range(int(num_jugadores)):
            nombre_jugador = jugadores_seleccionados[i]
            jugador_id = dict_jugadores[nombre_jugador]
            puntos_jugador = puntuaciones[i]
            posicion_ranking = i + 1  # El primero tiene posición 1, el segundo 2...
            
            registros_resultados.append({
                "partida_id": partida_id_generado,
                "jugador_id": jugador_id,
                "posicion": posicion_ranking,
                "puntuacion": puntos_jugador
            })
            
        with st.spinner("Guardando los desgloses de puntuación..."):
            respuesta_resultados = insertar_registro("resultados_partidas", registros_resultados)
            
        if respuesta_resultados:
            st.success(f"✓ ¡Todos los {num_jugadores} resultados se han vinculado correctamente!")
            st.balloons()
    else:
        st.error("No se pudo obtener el ID de la partida creada. Los resultados no se guardaron.")
