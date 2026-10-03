import streamlit as st
import urllib.request
import urllib.error
import urllib.parse
import json
from datetime import datetime

# ==========================================
# CONEXIÓN IDÉNTICA A TU APP QUE FUNCIONA
# ==========================================
SUPABASE_URL = "https://supabase.co" 
SUPABASE_KEY = st.secrets["SUPABASE_KEY"] 

HEADERS_LECTURA = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

st.set_page_config(page_title="Introducir Partidas - Liga Mahjong Madrid", page_icon="🎴")
st.title("🀄 Introducir Nueva Partida")

# ==========================================
# FUNCIONES NATIVAS DE CONSULTA Y ENVÍO
# ==========================================
def obtener_datos(endpoint):
    """Lee datos de Supabase usando tu método exacto que va bien."""
    try:
        url = f"{SUPABASE_URL}/{endpoint}"
        req = urllib.request.Request(url, headers=HEADERS_LECTURA, method="GET")
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        st.error(f"Error al leer de Supabase ({endpoint}): {e}")
        return []

def insertar_datos(endpoint, payload, usar_retorno=False):
    """Envía los datos a Supabase adaptando las cabeceras según el caso."""
    try:
        url = f"{SUPABASE_URL}/{endpoint}"
        data_json = json.dumps(payload).encode("utf-8")
        
        cabeceras = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        # Solo pedimos el retorno del ID para la cabecera de la partida
        if usar_retorno:
            cabeceras["Prefer"] = "return=representation"
            
        req = urllib.request.Request(url, data=data_json, headers=cabeceras, method="POST")
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode()
            return json.loads(res_body) if res_body else True
    except urllib.error.HTTPError as e:
        # Controlamos códigos de éxito HTTP estándar de Postgres (200, 201, 204)
        if e.code in (200, 201, 204):
            res_body = e.read().decode()
            return json.loads(res_body) if res_body else True
        else:
            res_err = e.read().decode()
            st.error(f"Error HTTP {e.code} en '{endpoint}': {res_err}")
            return None
    except Exception as e:
        st.error(f"Error inesperado al insertar en '{endpoint}': {e}")
        return None

# ==========================================
# CARGA DE DATOS Y CONCATENACIÓN DE NOMBRES
# ==========================================
# Traemos jugadores usando tu conexión nativa
lista_jugadores = obtener_datos("jugadores?select=id,nombre,nombre_real&order=nombre.asc")

if not lista_jugadores:
    st.warning("No se pudieron recuperar los jugadores. Revisa las credenciales de tu archivo Secrets.")
    st.stop()

dict_jugadores = {}
nombres_para_combo = []

for j in lista_jugadores:
    nombre = j.get("nombre") or ""
    nombre_real = j.get("nombre_real") or ""
    
    # Concatenamos siempre que exista un nombre real válido
    if nombre_real and nombre_real.strip() != "":
        nombre_mostrar = f"{nombre} ({nombre_real})"
    else:
        nombre_mostrar = nombre
        
    dict_jugadores[nombre_mostrar] = j["id"]
    nombres_para_combo.append(nombre_mostrar)

# ==========================================
# FORMULARIO DE INTRODUCCIÓN DE DATOS
# ==========================================
with st.form("formulario_alta_partida", clear_on_submit=False):
    st.subheader("1. Datos de la Mesa")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_juego = st.radio("Tipo de Juego:", ["RIICHI", "MCR"], horizontal=True)
    with col2:
        temporada = st.text_input("Temporada:", value="Oct 2026 - Sept 2027", disabled=True)
        
    fecha = st.date_input("Fecha de la partida:", datetime.today())
    n_mesa = st.number_input("Número de Mesa:", min_value=1, max_value=25, value=1, step=1)
    
    # Identificador automatizado según tus requerimientos
    fecha_str = fecha.strftime("%Y%m%d")
    nombre_partida_auto = f"{tipo_juego}-{fecha_str}-Mesa {n_mesa}"
    st.caption(f"Identificador autogenerado: **{nombre_partida_auto}**")
    
    st.markdown("---")
    st.subheader("2. Posiciones y Puntuaciones")
    
    num_jugadores = 4 if tipo_juego == "RIICHI" else st.number_input("Número de jugadores para MCR:", min_value=4, max_value=5, value=4, step=1)
    st.info("Introduce los resultados por orden estricto de clasificación (del 1º al último).")
    
    jugadores_seleccionados = []
    puntuaciones = []
    
    for i in range(int(num_jugadores)):
        st.markdown(f"**Clasificado {i+1}º**")
        c1, c2 = st.columns(2)
        
        with c1:
            idx_defecto = min(i, len(nombres_para_combo) - 1)
            jugador = st.selectbox(
                f"Selecciona al jugador para el puesto {i+1}:", 
                nombres_para_combo, 
                index=idx_defecto, 
                key=f"combo_jugador_{i}"
            )
            jugadores_seleccionados.append(jugador)
            
        with c2:
            puntos = st.number_input(
                f"Puntuación del puesto {i+1}:", 
                value=0, 
                step=100 if tipo_juego == "RIICHI" else 1, 
                key=f"puntos_jugador_{i}"
            )
            puntuaciones.append(puntos)

    enviar = st.form_submit_button("Guardar Partida y Resultados Completo")

# ==========================================
# PROCESAMIENTO Y ENVÍO CRUZADO
# ==========================================
if enviar:
    if len(jugadores_seleccionados) != len(set(jugadores_seleccionados)):
        st.error("Error: No puedes seleccionar al mismo jugador en varias posiciones de la misma mesa.")
        st.stop()
        
    # PASO A: Creamos el registro en la tabla 'partidas'
    datos_partida = {
        "fecha": str(fecha),
        "tipo_juego": tipo_juego,
        "nombre": nombre_partida_auto,
        "temporada": "Oct 2026 - Sept 2027"
    }
    
    with st.spinner("Registrando cabecera de la partida..."):
        res_partida = insertar_datos("partidas", datos_partida, usar_retorno=True)
        
    if res_partida:
        # Extraemos el ID autogenerado de la partida de forma segura
        item_partida = res_partida if isinstance(res_partida, list) and len(res_partida) > 0 else [res_partida]
        partida_id_generado = item_partida[0].get("id") if isinstance(item_partida[0], dict) else None
        
        if partida_id_generado:
            st.success(f"✓ Cabecera de partida guardada (ID: {partida_id_generado})")
            
            # PASO B: Buscamos el ID máximo actual de resultados_partidas para prevenir el error 409
            max_id_data = obtener_datos("resultados_partidas?select=id&order=id.desc&limit=1")
            max_id_actual = int(max_id_data[0]["id"]) if max_id_data and len(max_id_data) > 0 else 0
            
            # PASO C: Insertar desgloses de los jugadores uno a uno de manera limpia
            exito_total = True
            with st.spinner("Guardando puntuaciones individuales..."):
                for i in range(int(num_jugadores)):
                    nombre_visual = jugadores_seleccionados[i]
                    id_jugador_real = dict_jugadores[nombre_visual]
                    
                    datos_resultado = {
                        "id": max_id_actual + 1 + i,  # Secuenciación manual garantizada sin saltos
                        "partida_id": partida_id_generado,
                        "jugador_id": id_jugador_real,
                        "posicion": i + 1,
                        "puntuacion": puntuaciones[i]
                    }
                    
                    res_jugador = insertar_datos("resultados_partidas", datos_resultado, usar_prefer=False)
                    if not res_jugador:
                        exito_total = False
                        
            if exito_total:
                st.success(f"✓ ¡Mesa guardada por completo! Partida e historial vinculados con éxito.")
                st.balloons()
        else:
            st.error("No se pudo obtener el ID de la partida generada por Supabase.")
    else:
        st.error("Error al registrar la partida en la base de datos.")
