import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V16: ALL STARS (TODAS LAS LISTAS) ---
st.set_page_config(layout="wide", page_title="SCANNER V11.29 - TOP")
st.title("🌎 SCANNER GUSTY V11.29 - FINALE")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configuración")
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # CHECKER DE CREDITOS
    if API_KEY:
        if st.button("💰 Ver Saldo API"):
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}")
                if r.status_code == 200:
                    st.success(f"Te quedan: **{r.headers.get('x-requests-remaining')}**")
                else: st.error("Error de clave")
            except: pass

    # CARGA DEPORTES
    if 'sports_data' not in st.session_state:
        st.session_state['sports_data'] = {}

    if st.button("🔄 Cargar Deportes"):
        if API_KEY:
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}")
                data = r.json()
                if isinstance(data, list):
                    clean = {f"{x['group']} - {x['title']}": x['key'] for x in data if x['active']}
                    st.session_state['sports_data'] = clean
                    st.success("¡Listo!")
                else: st.error(f"Error: {data}")
            except Exception as e: st.error(f"Error: {e}")

    # SELECTOR DE LIGA
    sport_key = None
    if st.session_state['sports_data']:
        lista = sorted(st.session_state['sports_data'].keys())
        sel = st.selectbox("Liga:", lista)
        sport_key = st.session_state['sports_data'][sel]

    # --- 2. TUS CASAS (LISTA COMPLETA) ---
    st.header("2. Casas Activas")
    
    # Lista Unificada (Sin duplicados y con TODAS las que pediste)
    casas_maestras = [
        "Pinnacle",       # Base
        "BetOnline.ag",   # Cripto US
        "BetUS",          # Cripto US
        "MyBookie.ag",    # Cripto US
        "LowVig.ag",      # Cripto US
        "Betfair",        # Exchange
        "Matchbook",      # Exchange
        "Smarkets",       # Exchange
        "1xBet",          # Latam/EU
        "Bet365",         # Global
        "Betsson",        # Latam
        "Betway",         # Latam
        "Marathon Bet",   # High Odds
        "Coolbet",        # Latam
        "William Hill",   # UK/EU
        "888sport",       # UK/EU
        "LeoVegas",       # EU
        "DAZN Bet"        # Nueva
    ]
    
    # POR DEFECTO: ¡TODAS ACTIVADAS!
    # El usuario pidió quitar el filtro, así que seleccionamos todas de una.
    
    mis_casas = st.multiselect(
        "Filtrar Casas:", 
        options=casas_maestras, 
        default=casas_maestras # <--- Aquí está la magia: Todas seleccionadas por defecto
    )
    
    st.caption(f"Buscando en {len(mis_casas)} casas simultáneamente.")

    # --- 3. MERCADO ---
    st.header("3. Mercado")
    market_map = {
        "🏆 Ganador (H2H)": "h2h",
        "🏀/🏈 Hándicaps": "spreads",
        "🔢 Totales": "totals",
        "⚠️ Doble Oportunidad": "double_chance",
        "⚠️ Empate no Válido": "draw_no_bet"
    }
    m_label = st.selectbox("Tipo:", list(market_map.keys()))
    m_val = market_map[m_label]
    
    min_profit = st.slider("Ganancia Mínima %:", 0.0, 10.0, 0.0)
    btn_buscar = st.button("🚀 BUSCAR SUREBETS")
    # --- BLOQUE 2: MOTOR GLOBAL ---
if btn_buscar and API_KEY and sport_key:
    # Región GLOBAL OBLIGATORIA para ver casas US (BetOnline) y EU (Betfair) a la vez
    region_code = "us,uk,eu,au" 
    
    with st.spinner(f"Escaneando {sport_key} en {len(mis_casas)} casas..."):
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_code,
                'markets': m_val,
                'oddsFormat': 'decimal'
            }
            
            r = requests.get(url, params=params)
            data = r.json()
            
            # Validación API
            if isinstance(data, dict) and 'message' in data:
                if 'not supported' in data['message']:
                    st.error(f"🚫 El mercado '{m_label}' no está disponible.")
                    st.stop()
            
            # Procesamiento
            if isinstance(data, list):
                oportunidades = []
                
                for ev in data:
                    fecha = ev.get('commence_time','').replace('T',' ').replace('Z','')
                    evento = f"{ev['home_team']} vs {ev['away_team']}"
                    
                    grupos = {}
                    
                    for book in ev['bookmakers']:
                        casa_nombre = book['title']
                        
                        # FILTRO FLEXIBLE
                        # Verifica si la casa encontrada coincide parcialmente con alguna de TU lista
                        es_permitida = False
                        for permitido in mis_casas:
                            if permitido.lower() in casa_nombre.lower():
                                es_permitida = True
                                break
                        
                        if not es_permitida:
                            continue 
                            
                        for m in book['markets']:
                            if m['key'] == m_val:
                                for out in m['outcomes']:
                                    pt = out.get('point', 'Moneyline')
                                    if pt not in grupos: grupos[pt] = []
                                    grupos[pt].append({
                                        'bookie': casa_nombre,
                                        'name': out['name'],
                                        'price': out['price']
                                    })
                    
                    # CÁLCULO
                    for pt, cuotas in grupos.items():
                        mejor_opcion = {}
                        for c in cuotas:
                            sel = c['name']
                            if sel not in mejor_opcion or c['price'] > mejor_opcion[sel]['price']:
                                mejor_opcion[sel] = c
                        
                        if len(mejor_opcion) >= 2:
                            finales = list(mejor_opcion.values())
                            suma_inversa = sum(1/x['price'] for x in finales)
                            
                            if suma_inversa < 1.0:
                                ben = (1 - suma_inversa) / suma_inversa * 100
                                
                                if ben >= min_profit:
                                    # Validación Totales
                                    nombres = [x['name'] for x in finales]
                                    es_valido = True
                                    if m_val == 'totals' and nombres[0] == nombres[1]: es_valido = False
                                    
                                    if es_valido:
                                        detalles = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in finales])
                                        oportunidades.append({
                                            "Fecha": fecha,
                                            "Evento": evento,
                                            "Mercado/Sel": pt,
                                            "Beneficio": f"{ben:.2f}%",
                                            "Apuestas": detalles
                                        })
                
                if oportunidades:
                    st.success(f"¡{len(oportunidades)} Oportunidades!")
                    st.dataframe(pd.DataFrame(oportunidades), use_container_width=True)
                else:
                    st.warning("No hay oportunidades en este momento con estas casas.")
                    
                with st.expander("Ver Datos Crudos"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")
