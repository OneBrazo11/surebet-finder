import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(layout="wide", page_title="Sniper V10")
st.title("🎯 Sniper V10 - Back to Basics")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    
    # 1. API KEY
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # 2. CARGAR LIGAS
    if 'sports_data' not in st.session_state:
        st.session_state['sports_data'] = {}
    
    if st.button("🔄 Cargar Deportes"):
        if not API_KEY:
            st.error("Pon tu API Key primero.")
        else:
            try:
                # Url oficial
                url = "https://api.the-odds-api.com/v4/sports/"
                params = {'apiKey': API_KEY}
                r = requests.get(url, params=params)
                data = r.json()
                
                if isinstance(data, list):
                    # Limpiamos la lista
                    clean_dict = {}
                    for x in data:
                        if x['active']:
                            label = f"{x['group']} - {x['title']}"
                            clean_dict[label] = x['key']
                    
                    st.session_state['sports_data'] = clean_dict
                    st.success(f"¡{len(clean_dict)} Ligas Activas!")
                else:
                    st.error(f"Error: {data}")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

    # 3. FILTROS
    sport_key = None
    if st.session_state['sports_data']:
        sorted_list = sorted(st.session_state['sports_data'].keys())
        selection = st.selectbox("Liga / Deporte:", sorted_list)
        sport_key = st.session_state['sports_data'][selection]
    
    # Regiones (Mapeo manual para búsqueda global)
    reg_map = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Latam (AU)": "au"
    }
    region_label = st.selectbox("Región:", list(reg_map.keys()))
    region_val = reg_map[region_label]
    
    # Mercados solicitados
    markets_list = [
        "h2h",              # Ganador
        "spreads",          # Handicaps
        "totals",           # Altas/Bajas
        "draw_no_bet",      # Empate no valido
        "double_chance"     # Doble oportunidad
    ]
    market_val = st.selectbox("Mercado:", markets_list)
    
    min_profit = st.slider("Beneficio Min %:", 0.0, 10.0, 0.0)
    
    btn_run = st.button("🔎 BUSCAR AHORA")

# --- LÓGICA PURA (Back to Basics) ---
if btn_run and API_KEY and sport_key:
    with st.spinner("Escaneando mercado..."):
        try:
            # Construcción URL
            base = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_val,
                'markets': market_val,
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(base, params=params)
            odds_data = response.json()
            
            # Verificación básica
            if not isinstance(odds_data, list):
                st.error(f"API Error: {odds_data}")
            else:
                opportunities = []
                
                for event in odds_data:
                    # Datos del evento
                    ev_name = f"{event['home_team']} vs {event['away_team']}"
                    
                    # Fecha segura
                    raw_date = event.get('commence_time', '')
                    fecha = raw_date.replace('T', ' ').replace('Z', '')
                    
                    # Agrupar cuotas (Lógica Universal)
                    # Clave: Puede ser el nombre del equipo O el punto (para totales/handicaps)
                    grouped_odds = {}
                    
                    for book in event['bookmakers']:
                        for m in book['markets']:
                            if m['key'] == market_val:
                                for out in m['outcomes']:
                                    # Para spreads/totals usamos el 'point' como agrupador
                                    # Para h2h/dnb usamos el 'name' o una clave genérica
                                    
                                    # TRUCO: Si es totals/spreads, la clave es el PUNTO (ej: 2.5)
                                    # Si es H2H, la clave es 'Moneyline' (todos compiten contra todos)
                                    key_point = out.get('point', 'Moneyline')
                                    
                                    if key_point not in grouped_odds:
                                        grouped_odds[key_point] = []
                                    
                                    # Guardamos la cuota
                                    info = {
                                        'bookie': book['title'],
                                        'name': out['name'],
                                        'price': out['price']
                                    }
                                    grouped_odds[key_point].append(info)
                    
                    # Analizar cada grupo en busca de arbitraje
                    for g_key, options_list in grouped_odds.items():
                        
                        # Paso 1: Encontrar la MEJOR cuota para cada opción
                        best_in_market = {}
                        for opt in options_list:
                            sel_name = opt['name']
                            if sel_name not in best_in_market:
                                best_in_market[sel_name] = opt
                            else:
                                if opt['price'] > best_in_market[sel_name]['price']:
                                    best_in_market[sel_name] = opt
                        
                        # Paso 2: Verificar si hay suficientes lados para una apuesta
                        # (Mínimo 2 lados para comparar)
                        if len(best_in_market) >= 2:
                            final_odds = list(best_in_market.values())
                            
                            # Paso 3: Suma de inversas (Arbitraje Matemático)
                            arb_sum = sum(1 / item['price'] for item in final_odds)
                            
                            # Paso 4: ¿Es Surebet? (< 1.0)
                            if arb_sum < 1.0:
                                profit = (1 - arb_sum) / arb_sum * 100
                                
                                if profit >= min_profit:
                                    # Formatear salida
                                    bets_text = []
                                    for bo in final_odds:
                                        txt = f"{bo['name']} ({bo['bookie']}) @ {bo['price']}"
                                        bets_text.append(txt)
                                    
                                    full_bet_str = "  |  ".join(bets_text)
                                    
                                    opportunities.append({
                                        "Fecha": fecha,
                                        "Evento": ev_name,
                                        "Selección": g_key, # Muestra el punto (ej: Over 2.5)
                                        "Beneficio":
