import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Pixel Trader V8.4", 
    layout="wide"
)
st.title("🚀 Pixel Trader Sniper - Estación de Trabajo")

# --- 2. BARRA LATERAL ---
with st.sidebar:
    st.header("Credenciales")
    # Limpiamos espacios en blanco por si acaso
    raw_key = st.text_input("Tu API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # --- CALCULADORA DE STAKES ---
    with st.expander("🧮 Calculadora Stakes", expanded=True):
        radio_opts = [
            "2 Opciones (Tenis/DNB)", 
            "3 Opciones (1X2 Fútbol)"
        ]
        calc_mode = st.radio("Modo:", radio_opts)
        
        bank = st.number_input("Banco Total ($)", value=100.0)
        
        if calc_mode == radio_opts[0]:
            # MODO 2 OPCIONES
            c1 = st.number_input("Cuota A", value=2.0)
            c2 = st.number_input("Cuota B", value=2.0)
            
            if c1 > 0 and c2 > 0:
                inversa = (1/c1 + 1/c2)
                arb_perc = inversa * 100
                profit = (bank / inversa) - bank
                
                txt_prof = f"${profit:.2f}"
                st.markdown(f"**Ganancia:** :green[{txt_prof}]")
                
                s1 = (bank * (1/c1)) / inversa
                s2 = (bank * (1/c2)) / inversa
                
                cA, cB = st.columns(2)
                cA.metric("Apuesta A", f"${s1:.2f}")
                cB.metric("Apuesta B", f"${s2:.2f}")

        else:
            # MODO 3 OPCIONES
            c1 = st.number_input("Local", value=2.5)
            c2 = st.number_input("Empate", value=3.2)
            c3 = st.number_input("Visita", value=3.0)
            
            if c1 > 0 and c2 > 0 and c3 > 0:
                inversa = (1/c1 + 1/c2 + 1/c3)
                arb_perc = inversa * 100
                profit = (bank / inversa) - bank
                
                txt_prof = f"${profit:.2f}"
                st.markdown(f"**Ganancia:** :green[{txt_prof}]")
                
                s1 = (bank * (1/c1)) / inversa
                s2 = (bank * (1/c2)) / inversa
                s3 = (bank * (1/c3)) / inversa
                
                cA, cB, cC = st.columns(3)
                cA.metric("L", f"${s1:.2f}")
                cB.metric("E", f"${s2:.2f}")
                cC.metric("V", f"${s3:.2f}")

    # --- PROYECCIÓN INTERÉS COMPUESTO ---
    with st.expander("📈 Proyección", expanded=False):
        ini = st.number_input("Inicio", value=50.0)
        yield_d = st.number_input("Rentabilidad %", value=1.5)
        dias = st.slider("Días", 30, 365, 30)
        
        # Cálculos seguros
        factor = (1 + yield_d/100)
        final = ini * (factor ** dias)
        neto = final - ini
        
        txt_fin = f"${final:,.2f}"
        txt_net = f"${neto:,.2f}"
        
        st.metric("Final", txt_fin)
        st.metric("Ganancia", txt_net)

    # --- BOTÓN ACTUALIZAR LIGAS ---
    st.header("Escáner")
    
    # Inicializar estado
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    if API_KEY:
        if st.button("🔄 Actualizar Ligas"):
            try:
                # URL Base
                url_base = "https://api.the-odds-api.com/v4/sports/"
                
                # Parametros seguros
                p = {'apiKey': API_KEY}
                
                res = requests.get(url_base, params=p)
                data = res.json()
                
                if isinstance(data, list):
                    # Diccionario vertical
                    new_list = {
                        f"{x['group']} - {x['title']}": x['key']
                        for x in data 
                        if x['active']
                    }
                    st.session_state['sports_list'] = new_list
                    st.success("¡Conexión Exitosa!")
                else:
                    st.error(f"Error API: {data}")
            except Exception as e:
                st.error(f"Error de Conexión: {e}")

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
    region_mode = st.selectbox("Región", regiones)
    
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
    
    btn_scan = st.button("🔎 Buscar")

# --- 3. LÓGICA DEL ESCÁNER ---
def procesar(bookmakers, mercado):
    agrupado = {}
    
    for book in bookmakers:
        for m in book['markets']:
            if m['key'] == mercado:
                for out in m['outcomes']:
                    nombre = out['name']
                    precio = out['price']
                    punto = out.get('point', 'Moneyline')
                    
                    if punto not in agrupado:
                        agrupado[punto] = []
                    
                    item = {
                        'bookie': book['title'],
                        'name': nombre,
                        'price': precio
                    }
                    agrupado[punto].append(item)
    
    resultados = []
    
    for pt, opciones in agrupado.items():
        mejor = {}
        for op in opciones:
            nom = op['name']
            curr_p = op['price']
            
            if nom not in mejor or curr_p > mejor[nom]['price']:
                mejor[nom] = op
        
        if len(mejor) >= 2:
            lados = list(mejor.values())
            suma_arb = sum(1/x['price'] for x in lados)
            
            valido = False
            if suma_arb < 1.0:
                # Condiciones verticales
                c1 = (mercado == 'h2h' and len(mejor) == 3)
                c2 = (mercado == 'double_chance' and len(mejor) >= 3)
                c3 = (mercado in ['spreads', 'totals', 'draw_no_bet'])
                c4 = (mercado == 'h2h' and len(mejor) == 2)
                
                if c1 or c2 or c3 or c4:
                    valido = True
            
            if valido:
                margen = (1 - suma_arb) / suma_arb * 100
                if margen >= min_p:
