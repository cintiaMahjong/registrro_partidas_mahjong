import streamlit as st
import pandas as pd
import urllib.request
import urllib.parse
import json
import os
import html
from datetime import datetime

# ==========================================
# CONFIGURACIÓN Y ESTILOS ORIGINALES
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

HEADERS_BASE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

# Inyección de tu CSS original
st.markdown(""" 
<style> 
* { box-sizing: border-box; } 
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; } 
.stApp { background: #ffffff; } 
.block-container { width: 100% !important; max-width: 1100px !important; margin: 0 auto !important; padding: 1.25rem 1.25rem 2.5rem !important; } 
h1, h2, h3 { color: #151515 !important; } 
h1 { font-size: 2rem !important; font-weight: 800 !important; line-height: 1.1 !important; } 
.stButton > button { width: 100% !important; min-height: 40px !important; padding: 6px 9px !important; border-radius: 8px !important; border: 1px solid #d6d6d6 !important; background: #ffffff !important; color: #151515 !important; font-size: .90rem !important; font-weight: 600 !important; } 
.stButton > button:hover { border-color: #b40000 !important; color: #b40000 !important; } 
.stTabs [data-baseweb="tab-list"] { width: 100% !important; gap: 4px !important; } 
.stTabs [data-baseweb="tab"] { flex: 1 1 0 !important; min-width: 0 !important; justify-content: center !important; min-height: 46px !important; padding: 6px 8px !important; font-size: .95rem !important; font-weight: 700 !important; } 
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: #14532d !important; } 
.stTabs [data-baseweb="tab-highlight"] { background-color: #14532d !important; } 
</style> 
""", unsafe_allow_html=True)

# ==========================================
# PESTAÑAS PRINCIPALES
# ==========================================
tab_ver, tab_insertar = st.tabs(["📊 Ver Clasificaciones", "📝 Introducir Partida"])

with tab_ver:
    st.title("🏆 Clasificación Actual")
    st.write("Aquí se muestra tu tabla de ranking habitual leyendo desde Supabase de forma nativa...")
    # Tu código original de lectura del ranking va aquí sin tocar nada

with tab_insertar:
    st.title("🀄 Introducir Nueva Partida")

    # 1. LEER JUGADORES (Usando tu lógica nativa exacta de urllib que sí funciona)
    lista_jugadores = []
    try:
        url_j = f"{SUPABASE_URL}/jugadores?select=id,nombre,nombre_real&order=nombre.asc"
        req_j = urllib.request.Request(url_j, headers=HEADERS_BASE, method="GET")
        with urllib.request.urlopen(req_j) as resp_j:
            lista_jugadores = json.loads(resp_j.read().decode())
    except Exception as e:
        st.error(f"Error al leer jugadores: {e}")

    if lista_jugadores:
        # Generar el diccionario y el Concat Nombre (Nombre Real) obligatorio
        dict_jugadores = {}
        nombres_combo = []
        for j in lista_jugadores:
            n = j.get("nombre") or ""
            nr = j.get("nombre_real") or ""
            nombre_final = f"{n} ({nr})" if nr else n
            dict_jugadores[nombre_final] = j["id"]
            nombres_combo.append(nombre_final)

        # 2. CALCULAR EL MÁXIMO ID ACTUAL DE RESULTADOS PARA EL PARCHEO 409
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

        # FORMULARIO VISUAL
        with st.form("formulario_alta_partidas"):
            col1, col2 = st.columns(2)
            with col1:
                tipo_juego = st.radio("Tipo de Juego:", ["RIICHI", "MCR"], horizontal=True)
            with col2:
                temporada = st.text_input("Temporada:", value="Oct 2026 - Sept 2027", disabled=True)
                
            fecha = st.date_input("Fecha de la partida:", datetime.today())
            n_mesa = st.number_input("Número de Mesa:", min_value=1, max_value=20, value=1, step=1)
            
            # Generación automática de identificador
            fecha_str = fecha.strftime("%Y%m%d")
            nombre_partida_auto = f"{tipo_juego}-{fecha_str}-Mesa {n_mesa}"
            st.caption(f"Identificador de partida generado: **{nombre_partida_auto}**")
            
            st.markdown("---")
            st.subheader("Clasificación de la Mesa")
            
            num_jugadores = 4 if tipo_juego == "RIICHI" else st.number_input("Número de jugadores (MCR):", min_value=4, max_value=5, value=4)
            
            jugadores_seleccionados = []
            puntuaciones = []
            
            for i in range(int(num_jugadores)):
                st.markdown(f"**Posición {i+1}**")
                c1, c2 = st.columns(2)
                with c1:
                    j_sel = st.selectbox(f"Jugador {i+1}:", nombres_combo, index=min(i, len(nombres_combo)-1), key=f"sel_{i}")
                    jugadores_seleccionados.append(j_sel)
                with c2:
                    p_sel = st.number_input(f"Puntuación {i+1}:", value=0, step=100 if tipo_juego == "RIICHI" else 1, key=f"pts_{i}")
                    puntuaciones.append(p_sel)
                    
            enviar = st.form_submit_button("Guardar Todo en Supabase")

        # 3. PROCESAMIENTO E INSERCIÓN DEFINITIVA
        if enviar:
            if len(jugadores_seleccionados) != len(set(jugadores_seleccionados)):
                st.error("Error: Hay jugadores duplicados en la mesa.")
            else:
                # PASO A: Crear la partida
                partida_guardada = False
                partida_id = None
                
                payload_partida = {
                    "fecha": str(fecha),
                    "tipo_juego": tipo_juego,
                    "nombre": nombre_partida_auto,
                    "temporada": "Oct 2026 - Sept 2027"
                }
                
                try:
                    url_p = f"{SUPABASE_URL}/partidas"
                    req_p = urllib.request.Request(url_p, data=json.dumps(payload_partida).encode("utf-8"), headers={**HEADERS_BASE, "Content-Type": "application/json", "Prefer": "return=representation"}, method="POST")
                    with urllib.request.urlopen(req_p) as resp_p:
                        res_p = json.loads(resp_p.read().decode())
                        # Extraer id robusto de lista o diccionario
                        item_partida = res_p[0] if isinstance(res_p, list) else res_p
                        partida_id = item_partida.get("id")
                        partida_guardada = True
                except Exception as e:
                    st.error(f"Error al guardar la cabecera de la partida: {e}")

                # PASO B: Si la partida existe, meter los resultados asignando manualmente el ID correlativo
                if partida_guardada and partida_id:
                    st.success(f"✓ Partida creada correctamente (ID: {partida_id})")
                    
                    error_en_jugador = False
                    for i in range(int(num_jugadores)):
                        nombre_visual = jugadores_seleccionados[i]
                        id_del_jugador = dict_jugadores[nombre_visual] # ID real extraído del combo
                        
                        payload_resultado = {
                            "id": max_id_resultados + 1 + i, # Evita el error 409 usando el máximo real calculado
                            "partida_id": partida_id,
                            "jugador_id": id_del_jugador,
                            "posicion": i + 1,
                            "puntuacion": puntuaciones[i]
                        }
                        
                        try:
                            url_r = f"{SUPABASE_URL}/resultados_partidas"
                            req_r = urllib.request.Request(url_r, data=json.dumps(payload_resultado).encode("utf-8"), headers={**HEADERS_BASE, "Content-Type": "application/json"}, method="POST")
                            with urllib.request.urlopen(req_r) as resp_r:
                                pass # Inserción individual exitosa
                        except Exception as e:
                            error_en_jugador = True
                            st.error(f"Error guardando el jugador {nombre_visual}: {e}")
                    
                    if not error_en_jugador:
                        st.success("✓ ¡Todos los jugadores y puntuaciones añadidos con éxito al histórico!")
                        st.balloons()
