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

HEADERS_BASE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

st.set_page_config(page_title="Introducir Partidas - Liga Mahjong Madrid", page_icon="🎴")
st.title("🀄 Introducir Nueva Partida")

# ==========================================
# FUNCIONES DE CONEXIÓN A LA BASE DE DATOS
# ==========================================
def obtener_jugadores():
    """Trae la lista de jugadores directamente de la tabla jugadores."""
    try:
        url = f"{SUPABASE_URL}/jugadores?select=id,nombre,nombre_real&order=nombre.asc"
        req = urllib.request.Request(url, headers=HEADERS_BASE, method="GET")
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        st.error(f"Error al cargar jugadores de la base de datos: {e}")
        return []

def obtener_max_id_resultados():
    """Busca cuál es el ID más alto actualmente en la tabla resultados_partidas."""
    try:
        url = f"{SUPABASE_URL}/resultados_partidas?select=id&order=id.desc&limit=1"
        req = urllib.request.Request(url, headers=HEADERS_BASE, method="GET")
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res and len(res) > 0:
                return int(res[0]["id"])
            return 0
    except Exception:
        # Si la tabla está completamente vacía, empezamos desde 0
        return 0

def insertar_registro(tabla, datos, usar_prefer=True):
    """Inserta datos en la tabla correspondiente y captura la respuesta nativa."""
    try:
        url = f"{SUPABASE_URL}/{tabla}"
        data_json = json.dumps(datos).encode("utf-8")
        
        cabeceras_post = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        if usar_prefer:
            cabeceras_post["Prefer"] = "return=representation"
            
        req = urllib.request.Request(url, data=data_json, headers=cabeceras_post, method="POST")
        
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode()
            return json.loads(res_body) if res_body else True
    except urllib.error.HTTPError as e:
        if e.code in (200, 201, 204):
            res_body = e.read().decode()
            return json.loads(res_body) if res_body else True
        else:
            res_err = e.read().decode()
            st.error(f"Error en la tabla '{tabla}' (Código {e.code}): {res_err}")
            return None
    except Exception as e:
        st.error(f"Error inesperado al insertar en '{tabla}': {e}")
        return None

# ==========================================
# CARGA DE DATOS E IMPLEMENTACIÓN DEL CONCAT
# ==========================================
lista_jugadores = obtener_jugadores()

if not lista_jugadores:
    st.warning("Cargando base de datos... Si el error persiste, comprueba la clave 'SUPABASE_KEY' en tus Secrets de Streamlit.")
    st.stop()

dict_jugadores = {}
nombres_para_combo = []

for j in lista_jugadores:
    nombre = j.get("nombre") or ""
    nombre_real = j.get("nombre_real") or ""
    
    # CORREGIDO: Forzamos el concat siempre para que veas 'Nombre (Nombre Real)' obligatoriamente
    if nombre_real:
        nombre_mostrar = f"{nombre} ({nombre_real})"
    else:
        nombre_mostrar = nombre
        
    dict_jugadores[nombre_mostrar] = j["id"]
    nombres_para_combo.append(nombre_mostrar)

# ==========================================
# FORMULARIO DE ENTRADA VISUAL
# ==========================================
with st.form("formulario_partida", clear_on_submit=False):
    st.subheader("1. Datos Generales de la Partida")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_juego = st.radio("Tipo de Juego:", ["RIICHI", "MCR"], horizontal=True)
    with col2:
        temporada = st.text_input("Temporada:", value="Oct 2026 - Sept 2027", disabled=True)
        
    fecha = st.date_input("Fecha de la partida:", datetime.today())
    
    col_aux1, col_aux2 = st.columns(2)
    with col_aux1:
        n_mesa = st.number_input("Número de Mesa:", min_value=1, max_value=20, value=1, step=1)
    
    fecha_str = fecha.strftime("%Y%m%d")
    nombre_partida_auto = f"{tipo_juego}-{fecha_str}-Mesa {n_mesa}"
    
    with col_aux2:
        st.write("") 
        st.write("") 
        st.caption(f"Identificador de partida: **{nombre_partida_auto}**")

    st.markdown("---")
    st.subheader("2. Resultados de los Jugadores")
    
    num_jugadores = 4 if tipo_juego == "RIICHI" else st.number_input("Número de jugadores para MCR:", min_value=4, max_value=5, value=4, step=1)
    
    st.info("Introduce los jugadores en orden de clasificación: el 1º arriba hasta el último abajo.", icon="ℹ️")
    
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
        respuesta_partida = insertar_registro("partidas", datos_partida, usar_prefer=True)
        
    if respuesta_partida:
        registro_partida = respuesta_partida if isinstance(respuesta_partida, list) and len(respuesta_partida) > 0 else respuesta_partida
        partida_id_generado = registro_partida.get("id") if isinstance(registro_partida, dict) else None
        
        if partida_id_generado:
            st.success(f"✓ Partida guardada con éxito (ID: {partida_id_generado})")
            
            # NUEVO: Consultamos en tiempo real el ID máximo actual de resultados_partidas
            max_id_actual = obtener_max_id_resultados()
            
            exito_jugadores = True
            with st.spinner("Guardando las puntuaciones de cada jugador..."):
                for i in range(int(num_jugadores)):
                    nombre_visual = jugadores_seleccionados[i]
                    jugador_id = dict_jugadores[nombre_visual] # Recupera el ID correcto del combo
                    puntos_jugador = puntuaciones[i]
                    posicion_ranking = i + 1
                    
                    # Asignamos de forma explícita el id incrementado secuencialmente
                    nuevo_id_resultado = max_id_actual + 1 + i
                    
                    datos_resultado = {
                        "id": nuevo_id_resultado, # Enviado explícitamente para evitar el error 409
                        "partida_id": partida_id_generado,
                        "jugador_id": jugador_id,
                        "posicion": posicion_ranking,
                        "puntuacion": puntos_jugador
                    }
                    
                    res_indiv = insertar_registro("resultados_partidas", datos_resultado, usar_prefer=False)
                    if not res_indiv:
                        exito_jugadores = False
                        
            if exito_jugadores:
                st.success(f"✓ ¡Todos los {num_jugadores} resultados se han guardado correctamente sin colisiones!")
                st.balloons()
        else:
            st.error("La respuesta de la partida no devolvió un ID válido.")
    else:
        st.error("No se pudo insertar la partida inicial.")
