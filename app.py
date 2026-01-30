import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Sniper V8.5", 
    layout="wide"
)
st.title("🚀 Sniper - Estación de Trabajo")

# --- 2. BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    # Limpiamos espacios al pegar
    raw_key = st.text_input("Tu API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # --- CALCULADORA DE STAKES ---
    with st.expander("🧮 Calculadora Apuestas", expanded=True):
        modos = [
            "2 Opciones (Tenis/DNB)", 
            "3 Opciones (1X2 Fútbol)"
        ]
        modo = st.radio("Modo:", modos)
        
        bank = st.number_input("Inversión ($)", value=100.0)
        
        if modo == modos[0]:
            # MODO 2 VÍAS
            c1 = st.number_input("Cuota A", value=2.0)
            c2 = st.number_input("Cuota B", value=2.0)
            
            if c1 > 0 and c2 > 0:
                inv = (1/c1 + 1/c2)
                ganancia = (bank / inv) - bank
                
                txt = f"${ganancia:.2f}"
                st.markdown(f"**Ganancia:** :green[{txt}]")
                
                s1 = (bank * (1/c1)) / inv
                s2 = (bank * (1/c2)) / inv
                
                kA, kB = st.columns(2)
                kA.metric("Apuesta A", f"${s1:.0f}")
                kB.metric("Apuesta B", f"${s2:.0f}")

        else:
            # MODO 3 VÍAS
            c1 = st.number_input("Local", value=2.5)
            c2 = st.number_input("Empate", value=3.2)
            c3 = st.number_input("Visita", value=3.0)
            
            if c1 > 0 and c2 > 0 and c3 > 0:
                inv = (1/c1 + 1/c2 + 1/c3)
                ganancia = (bank / inv) - bank
                
                txt = f"${ganancia:.2f}"
                st.markdown(f"**Ganancia:** :green[{txt}]")
                
                s1 = (bank * (1/c1)) / inv
                s2 = (bank * (1/c2)) / inv
                s3 = (bank * (1/c3)) / inv
                
                kA, kB, kC = st.columns(3)
                kA.metric("L", f"${s1:.0f}")
                kB.metric("E", f"${s2:.0f}")
                kC.metric("V", f"${s3:.0f}")

    # --- CARGAR LIGAS ---
    st.header("2. Escáner")
    
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    if API_KEY:
        if st.button("🔄 Cargar Ligas"):
            try:
                base = "https://api.the-odds-api.com"
                ruta = "/v4/sports/"
                url = f"{base}{ruta}"
                
                # Usamos apiKey explícitamente
                p = {'apiKey': API_KEY}
                
                r = requests.get(url, params=p)
                data = r.json()
                
                if isinstance(data, list):
                    # Diccionario limpio
                    lista = {}
                    for x in data:
                        if x['active']:
                            k = x['key']
                            t = x['title']
                            g = x['group']
                            label = f"{g} - {t}"
                            lista[label] = k
                            
                    st.session_state['sports_list'] = lista
                    st.success("¡Ligas OK!")
                else:
                    st.error(f"Error API: {data}")
            except Exception as e:
                st.error(f"Error Conexión: {e}")

    # --- FILTROS ---
    if st.session_state['sports_list']:
        keys = sorted(st.session_state['sports_list'].keys())
        sel = st.selectbox("Liga:", keys)
        sport_key = st.session_state['sports_list'][sel]
    else:
        sport_key = None

    regiones = [
        "Global (Todas)", 
        "Europa (EU)", 
        "USA (US)", 
        "Latam (AU)"
    ]
    region_sel = st.selectbox("Región", regiones)
    
    mapa_reg = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Latam (AU)": "au"
    }
    
    mercados = [
        "h2h", 
        "spreads", 
        "totals", 
        "draw_no_bet", 
        "double_chance"
    ]
    m_type = st.selectbox("Mercado", mercados)
    
    min_p = st.slider("Min %", 0.0, 10.0, 0.0) 
    
    btn_buscar = st.button("🔎 Buscar")

# --- 3. LÓGICA DE ESCANEO ---
def procesar(bookmakers, mercado):
    agrupado = {}
    
    for book in bookmakers:
        for m in book['markets']:
            if m['key
