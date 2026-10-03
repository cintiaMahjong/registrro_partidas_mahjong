import streamlit as st
import pandas as pd
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import html
from datetime import datetime

# ==========================================
# CONFIGURACIÓN COMPLETA DE TU APP VÁLIDA
# ==========================================
RUTA_LOGO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "logo_mahjong_madrid.png"
)
st.set_page_config(
    page_title="Liga Mahjong Madrid",
    page_icon=RUTA_LOGO if os.path.exists(RUTA_LOGO) else "🀄",
    layout="centered"
)
SUPABASE_URL = "https://supabase.co" 
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Cabeceras estándar usando tu clave secreta de las Secrets
HEADERS_BASE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

st.markdown(""" 
<style> 
/* ========================================================= 
   MAHJONG MADRID - DISEÑO LIMPIO Y RESPONSIVE 
   Escritorio y móvil se diseñan por separado mediante media queries. 
========================================================= */ 
* { box-sizing: border-box; } 
 
[data-testid="stSidebar"], 
[data-testid="stSidebarCollapsedControl"] { 
    display: none !important; 
} 
 
.stApp { background: #ffffff; } 
 
.block-container { 
    width: 100% !important; 
    max-width: 1100px !important; 
    margin: 0 auto !important; 
    padding: 1.25rem 1.25rem 2.5rem !important; 
} 
 
[data-testid="stAppViewContainer"] .main, 
[data-testid="stAppViewContainer"] .block-container { 
    overflow-x: hidden !important; 
} 
 
h1, h2, h3 { color: #151515 !important; } 
h1 { font-size: 2rem !important; font-weight: 800 !important; line-height: 1.1 !important; } 
h2 { font-size: 1.4rem !important; } 
h3 { font-size: 1.1rem !important; } 
 
/* Botones normales: compactos en escritorio */ 
.stButton > button { 
    width: 100% !important; 
    min-height: 40px !important; 
    height: auto !important; 
    padding: 6px 9px !important; 
    border-radius: 8px !important; 
    border: 1px solid #d6d6d6 !important; 
    background: #ffffff !important; 
    color: #151515 !important; 
    font-size: .90rem !important; 
    font-weight: 600 !important; 
    line-height: 1.1 !important; 
    box-shadow: none !important; 
} 
.stButton > button:hover { 
    border-color: #b40000 !important; 
    color: #b40000 !important; 
} 
</style> 
""", unsafe_allow_html=True)

st.title("🀄 Registrar Nueva Partida")

# ==========================================
# 1. LEER JUGADORES (Con tu método exacto que va bien)
# ==========================================
lista_jugadores = []
try:
    url_j = f"{SUPABASE_URL}/jugadores?select=id,nombre,nombre_real&order=nombre.asc"
    req_j = urllib.request.Request(url_j, headers=HEADERS_BASE, method="GET")
    with urllib.request.urlopen(req_j) as resp_j:
        lista_jugadores = json.loads(resp_j.read().decode())
except Exception as e:
    st.error(f"Error al cargar jugadores: {e}")

# ==========================================
# 2. CALCULAR MAX ID DE RESULTADOS (Para solucionar el error 409 de Postgres)
# ==========================================
max_id_resultados = 0
try:
    url_m = f"{SUPABASE_URL}/resultados_partidas?select=id&order=id.desc&limit=1"
    req_m = urllib.request.Request(url_m, headers=HEADERS_BASE, method="GET")
    with urllib.request.urlopen(req_m) as resp_m:
        res_m = json.loads(resp_m.read().decode())
        if res_m and len(res_m) > 0:
            max_id_resultados = int(res_m[0]["id"])
except Exception:
    max_id_resultados = 0

# Procesa la lista de jugadores y fuerza el Concat Nombre (Nombre Real)
if not lista_jugadores:
    st.warning("No se pudieron recuperar los jugadores de la base de datos.")
    st.stop()

dict_jugadores = {}
nombres_para_combo = []
for j in lista_jugadores:
    n = j.get("nombre") or ""
    nr = j.get("nombre_real") or ""
    nombre_mostrar = f"{n} ({nr})" if nr else n
    dict_jugadores[nombre_mostrar] = j["id"]
    nombres_para_combo.append(nombre_mostrar)


# ==========================================
# GESTIÓN DE ESTADO PARA REFRESCADO INMEDIATO
# ==========================================
if "tipo_juego_guardado" not in st.session_state:
    st.session_state["tipo_juego_guardado"] = "RIICHI"

tipo_juego = st.radio(
    "Tipo de Juego:", 
    ["RIICHI", "MCR"], 
    index=0 if st.session_state["tipo_juego_guardado"] == "RIICHI" else 1,
    horizontal=True,
    key="selector_modalidad"
)

if tipo_juego != st.session_state["tipo_juego_guardado"]:
    st.session_state["tipo_juego_guardado"] = tipo_juego
    st.rerun()

if tipo_juego == "RIICHI":
    num_jugadores = 4
else:
    num_jugadores = st.number_input("Número de jugadores para MCR:", min_value=4, max_value=5, value=4, step=1)


# ==========================================
# FORMULARIO VISUAL DE INTRODUCCIÓN
# ==========================================
with st.form("formulario_alta_partidas", clear_on_submit=False):
    st.subheader("1. Datos Generales de la Partida")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Modalidad activa: **{tipo_juego}**")
        st.write(f"Participantes en mesa: **{int(num_jugadores)}**")
    with col2:
        temporada = st.text_input("Temporada:", value="Oct 2026 - Sept 2027", disabled=True)
        
    fecha = st.date_input("Fecha de la partida:", datetime.today())
    n_mesa = st.number_input("Número de Mesa:", min_value=1, max_value=20, value=1, step=1)
    
    fecha_str = fecha.strftime("%Y%m%d")
    nombre_partida_auto = f"{tipo_juego}-{fecha_str}-Mesa {n_mesa}"
    st.caption(f"Identificador automático: **{nombre_partida_auto}**")
    
    st.markdown("---")
    st.subheader("2. Resultados de los Jugadores")
    st.info("Introduce los jugadores por orden estricto de clasificación: del 1º arriba hasta el último abajo.")
    
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

    enviar = st.form_submit_button("Guardar Partida y Resultados")

# ==========================================
# 3. PROCESAMIENTO Y ENVÍO A SUPABASE
# ==========================================
if enviar:
    if len(jugadores_seleccionados) != len(set(jugadores_seleccionados)):
        st.error("Error: No puedes duplicar al mismo jugador en varias posiciones.")
        st.stop()
        
    # PASO A: Crear la partida en la tabla 'partidas'
    datos_partida = {
        "fecha": str(fecha),
        "tipo_juego": tipo_juego,
        "nombre": nombre_partida_auto,
        "temporada": "Oct 2026 - Sept 2027"
    }
    
    partida_guardada = False
    partida_id_generado = None
    
    try:
        url_p = f"{SUPABASE_URL}/partidas"
        headers_p = {**HEADERS_BASE, "Content-Type": "application/json", "Prefer": "return=representation"}
        req_p = urllib.request.Request(url_p, data=json.dumps(datos_partida).encode("utf-8"), headers=headers_p, method="POST")
        with urllib.request.urlopen(req_p) as resp_p:
            res_p = json.loads(resp_p.read().decode())
            registro_partida = res_p[0] if isinstance(res_p, list) and len(res_p) > 0 else res_p
            partida_id_generado = registro_partida.get("id")
            partida_guardada = True
    except Exception as e:
        st.error(f"Error al guardar la cabecera de la partida: {e}")

    # PASO B: Guardar los resultados en 'resultados_partidas' usando el ID correlativo manual
    if partida_guardada and partida_id_generado:
        st.success(f"✓ Partida guardada con éxito (ID: {partida_id_generado})")
        
        exito_jugadores = True
        with st.spinner("Guardando las puntuaciones individuales..."):
            for i in range(int(num_jugadores)):
                nombre_visual = jugadores_seleccionados[i]
                id_jugador_real = dict_jugadores[nombre_visual]
                puntos_jugador = puntuaciones[i]
                posicion_ranking = i + 1
                
                nuevo_id_resultado = max_id_resultados + 1 + i
                
                datos_resultado = {
                    "id": nuevo_id_resultado,
                    "partida_id": partida_id_generado,
                    "jugador_id": id_jugador_real,
                    "posicion": posicion_ranking,
                    "puntuacion": puntos_jugador
                }
                
                try:
                    url_r = f"{SUPABASE_URL}/resultados_partidas"
                    headers_r = {**HEADERS_BASE, "Content-Type": "application/json"}
                    req_r = urllib.request.Request(url_r, data=json.dumps(datos_resultado).encode("utf-8"), headers=headers_r, method="POST")
                    with urllib.request.urlopen(req_r) as resp_r:
                        pass
                except Exception as e:
                    exito_jugadores = False
                    st.error(f"Error guardando el resultado del jugador {nombre_visual}: {e}")
                    
        if exito_jugadores:
            st.success(f"✓ ¡Todos los {int(num_jugadores)} resultados se han enlazado y guardado correctamente!")
            st.balloons()
