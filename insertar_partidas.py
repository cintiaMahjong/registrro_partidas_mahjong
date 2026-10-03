import streamlit as st
import urllib.request
import urllib.error
import urllib.parse
import json
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = "https://supabase.co" 
SUPABASE_KEY = st.secrets["SUPABASE_KEY"] 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"  # Devuelve el objeto creado con su ID autogenerado
}

st.set_page_config(page_title="Introducir Partidas - Liga Mahjong Madrid", page_icon="🎴")
st.title("🀄 Introducir Nueva Partida")

# ==========================================
# FUNCIONES DE CONEXIÓN CORREGIDAS
# ==========================================
@st.cache_data(ttl=60)
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
    """Inserta datos en Supabase y maneja de forma segura las respuestas de urllib."""
    try:
        url = f"{SUPABASE_URL}/{tabla}"
        data_json = json.dumps(datos).encode("utf-8")
        req = urllib.request.Request(url, data=data_json, headers=HEADERS, method="POST")
        
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode()
            return json.loads(res_body)
    except urllib.error.HTTPError as e:
        # CORRECCIÓN DE SINTAXIS SEGURA SIN CORCHETES
        if e.code == 200 or e.code == 201:
            res_body = e.read().decode()
            return json.loads(res_body)
        else:
            st.error(f"Error HTTP ({e.code}) en tabla '{tabla}': {e.reason}")
            return None
    except Exception as e:
        st.error(f"Error inesperado al insertar en '{tabla}': {e}")
        return None

# ==========================================
# CARGA DE DATOS INICIALES
# ==========================================
lista_jugadores = obtener_jugadores()

if not lista_jugadores:
    st.warning("No se pudieron recuperar los jugadores. Verifica tus Secrets en Streamlit.")
    st.stop()

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
        temporada = st.text_input("Temporada:", value="Oct 2026 - Sept 2027", disabled=True)
        
    fecha = st.date_input("Fecha de la partida:", datetime.today())
    
    # Automatización del nombre para evitar errores tipográficos
    col_aux1, col_aux2 = st.columns(2)
    with col_aux1:
        n_mesa = st.number_input("Número de Mesa:", min_value=1, max_value=20, value=1, step=1)
    
    # Genera el string con la estructura visual exacta de tus capturas
    fecha_str = fecha.strftime("%Y%m%d")
    nombre_partida_auto = f"{tipo_juego}-{fecha_str}-Mesa {n_mesa}"
    
    with col_aux2:
        st.write("") # Espaciador
        st.write("") 
        st.caption(f"Identificador: **{nombre_partida_auto}**")

    st.markdown("---")
    st.subheader("2. Resultados de los Jugadores")
    
    num_jugadores = 4 if tipo_juego == "RIICHI" else st.number_input("Número de jugadores para MCR:", min_value=4, max_value=5, value=4, step=1)
    
    st.info("Introduce los jugadores siguiendo rigurosamente su orden final: el 1º arriba hasta el último abajo.")
    
    jugadores_seleccionados = []
    puntuaciones = []
    
    for i in range(int(num_jugadores)):
        st.markdown(f"**Posición {i+1}**")
        c1, c2 = st.columns(2)
        
        with c1:
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

    enviar = st.form_submit_button("Guardar Partida y Resultados en Supabase")

# ==========================================
# PROCESAMIENTO Y ENVÍO A SUPABASE
# ==========================================
if enviar:
    if len(jugadores_seleccionados) != len(set(jugadores_seleccionados)):
        st.error("Error: No puedes seleccionar al mismo jugador en múltiples posiciones.")
        st.stop()
        
    datos_partida = {
        "fecha": str(fecha),
        "tipo_juego": tipo_juego,
        "nombre": nombre_partida_auto,
        "temporada": "Oct 2026 - Sept 2027"
    }
    
    with st.spinner("Guardando los datos de la partida..."):
        respuesta_partida = insertar_registro("partidas", datos_partida)
        
    if respuesta_partida:
        # Si Supabase nos devuelve una lista con el objeto, extraemos el primer elemento
        if isinstance(respuesta_partida, list) and len(respuesta_partida) > 0:
            registro_partida = respuesta_partida[0]
        else:
            registro_partida = respuesta_partida
            
        partida_id_generado = registro_partida.get("id")
        
        if partida_id_generado:
            st.success(f"✓ Partida guardada con éxito (ID: {partida_id_generado})")
            
            registros_resultados = []
            for i in range(int(num_jugadores)):
                nombre_jugador = jugadores_seleccionados[i]
                jugador_id = dict_jugadores[nombre_jugador]
                puntos_jugador = puntos = puntuaciones[i]
                posicion_ranking = i + 1
                
                registros_resultados.append({
                    "partida_id": partida_id_generado,
                    "jugador_id": jugador_id,
                    "posicion": posicion_ranking,
                    "puntuacion": puntos_jugador
                })
                
            with st.spinner("Guardando los desgloses de puntuación..."):
                respuesta_resultados = insertar_registro("resultados_partidas", registros_resultados)
                
            if respuesta_resultados:
                st.success(f"✓ ¡Todos los {num_jugadores} resultados se han guardado correctamente!")
                st.balloons()
        else:
            st.error("La respuesta de Supabase no contenía un ID válido.")
    else:
        st.error("No se pudo obtener una respuesta correcta de Supabase al crear la partida.")
