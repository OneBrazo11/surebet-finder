import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Pixel Trader Sniper V8.2", 
    layout="wide"
)
st.title("🚀 Pixel Trader Sniper - Estación de Trabajo")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    API_KEY = st.text_input("Tu API Key", type="password")
    
    # --- CALCULADORA 1: STAKES ---
    with st.expander("🧮 Calculadora de Stakes", expanded=True):
        st.caption("Calcula cuánto apostar.")
        
        opciones = ["2 Opciones (Tenis/DNB)", "3 Opciones (1X2 Fútbol)"]
        calc_mode = st.radio("Tipo:", opciones)
        
        total_bank = st.number_input("Inversión Total ($)", value=100.0, step=10.0)
        
        if calc_mode == opciones[0]: # 2 Opciones
            c1 = st.number_input("Cuota A", value=2.00, step=0.01)
            c2 = st.number_input("Cuota B", value=2.00, step=0.01)
            
            if c1 > 0 and c2 > 0:
                arb_perc = (1/c1 + 1/c2) * 100
                profit = (total_bank / (arb_perc/100)) - total_bank
                
                # Formateo seguro de texto
                txt_ganancia = f"${profit:.2f}"
                st.markdown(f"**Beneficio:** :green[{txt_ganancia}]")
                
                s1 = (total_bank * (1/c1)) / (arb_perc/100)
                s2 = (total_bank * (1/c2)) / (arb_perc/100)
                
                st.write("---")
                k1, k2 = st.columns(2)
                k1.metric("Apuesta A", f"${s1:.2f}")
                k2.metric("Apuesta B", f"${s2:.2f}")
                
                st.info(f"💡 Redondea a: ${int(s1)} y ${int(s2)}")

        else: # 3 Opciones
            c1 = st.number_input("Cuota 1 (Local)", value=2.50)
            c2 = st.number_input("Cuota X (Empate)", value=3.20)
            c3 = st.number_input("Cuota 2 (Visita)", value=3.00)
            
            if c1 > 0 and c2 > 0 and c3 > 0:
                arb_perc = (1/c1 + 1/c2 + 1/c3) * 100
                profit = (total_bank / (arb_perc/100)) - total_bank
                
                txt_ganancia = f"${profit:.2f}"
                st.markdown(f"**Beneficio:** :green[{txt_ganancia}]")
                
                s1 = (total_bank * (1/c1)) / (arb_perc/100)
                s2 = (total_bank * (1/c2)) / (arb_perc/100)
                s3 = (total_bank * (1/c3)) / (arb_perc/100)
                
                st.write("---")
                ka, kb, kc = st.columns(3)
                ka.metric("Local", f"${s1:.2f}")
                kb.metric("Empate", f"${s2:.2f}")
                kc.metric("Visita", f"${s3:.2f}")

    # --- CALCULADORA 2: INTERÉS COMPUESTO ---
    with st.expander("📈 Proyección", expanded=False):
        st.caption("Interés compuesto diario.")
        
        ini_cap = st.number_input("Inicio ($)", value=50.0)
        yield_d = st.number_input("Rentabilidad Diaria (%)", value=1.5)
        dias = st.slider("Días", 30, 365, 30)
        
        fin_cap = ini_cap * ((1 + yield_d/100) ** dias)
        ganancia_neta = fin_cap - ini_cap
        
        # Formateo seguro para evitar cortes
        txt_final = f"${fin_cap:,.2f}"
        txt_neto = f"${ganancia_neta:,.2f}"
        delta_perc = f"{((fin_cap/ini_cap)-1)*100:.0f}%"
        
        st.metric("Capital Final", txt_final)
        st.metric("Ganancia Neta", txt_neto, delta=delta_perc)
        
        # Gráfico
        datos_grafico = {
            'Día': range(dias + 1),
            'Capital': [ini_cap * ((1 + yield_d/100) ** d) for d in range(dias + 1)]
        }
        st.line_chart(pd.DataFrame(datos_grafico), x='Día', y='Capital')

    # --- ACTUALIZAR LIGAS ---
    st.header("2. Escáner")
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    if API_KEY:
        if st.button("🔄 Actualizar Ligas"):
            try:
                base = "https://api.the-odds-api.com/v4/sports/"
                r = requests.get(f"{base}?api_key={API_KEY}")
                r.raise_for_status()
                data = r.json()
                
                if isinstance(data, list):
                    st.session_state['sports_list'] = {
                        f"{x['group']} - {x['title']}": x['key'] 
                        for x in data if x['active']
                    }
                    st.success("¡Ligas cargadas!")
                else:
                    st.error(f"Error API: {data}")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- FILTROS DE BÚSQUEDA ---
    if st.session_state['sports_list']:
        lista_ordenada = sorted(st.session_state['sports_list'].keys())
        sel_label = st.selectbox("Liga:", lista_ordenada)
        sport_key = st.session_state['sports_list'][sel_label]
    else:
        sport_key = None

    reg_opts = ["Global (Todas)", "Europa (EU)", "USA (US)", "Latam (AU)"]
    region_mode = st.selectbox("Región", reg_opts)
    
    # Mapa de regiones
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
    market_type = st.selectbox("Mercado", mercados)
    
    min_profit = st.slider("Min. Beneficio (%)", 0.0, 10.0, 0.0) 
    
    run_analysis = st.button("🔎 Buscar Surebets")

# --- MOTOR DE BÚSQUEDA ---
def procesar_evento(bookmakers, m_name):
    # Agrupar cuotas
    grouped = {}
    for book in bookmakers:
        for market in book['markets']:
            if market['key'] == m_name:
                for outcome in market['outcomes']:
                    name = outcome['name']
                    price = outcome['price']
                    # Usamos point o Moneyline
                    point = outcome.get('point', 'Moneyline')
                    
                    if point not in grouped: 
                        grouped[point] = []
                    
                    item = {
                        'bookie': book['title'], 
                        'name': name, 
                        'price': price
                    }
                    grouped[point].append(item)
    
    oportunidades = []
    
    for point, options in grouped.items():
        # Buscar mejor cuota por opción
        best = {}
        for opt in options:
            n = opt['name']
            if n not in best or opt['price'] > best[n]['price']:
                best[n] = opt
        
        # Validar arbitraje
        if len(best) >= 2:
            sides = list(best.values())
            arb_sum = sum(1/s['price'] for s in sides)
            
            es_valido = False
            if arb_sum < 1.0:
                # Reglas de validación
                cond1 = (m_name == 'h2h' and len(best) == 3)
                cond2 = (m_name == 'double_chance' and len(best) >= 3)
                cond3 = (m_name in ['spreads', 'totals', 'draw_no_bet'])
                cond4 = (m_name == 'h2h' and len(best) == 2)
                
                if cond1 or cond2 or cond3 or cond4:
                    es_valido = True
            
            if es_valido:
                profit = (1 - arb_sum) / arb_sum * 100
                if profit >= min_profit:
                    # Crear string de apuestas
                    detalles = []
                    for s in sides:
                        detalles.append(f"{s['name']}: {s['bookie']} @ {s['price']}")
                    
                    oportunidades.append({
                        "Mercado": m_name,
                        "Selección": point,
                        "Beneficio %": round(profit, 2),
                        "Apuestas": " | ".join(detalles)
                    })
    return oportunidades

# --- EJECUCIÓN ---
if run_analysis and API_KEY and sport_key:
    with st.spinner(f'Analizando {sport_key}...'):
        try:
            base_url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
