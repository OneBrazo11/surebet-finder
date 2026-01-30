import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V11: BACK TO BASICS ---
st.set_page_config(layout="wide", page_title="Sniper V11")
st.title("🎯 Sniper V11 - FINALE")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configuración")
    
    # API KEY
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # CARGAR LIGAS
    if 'sports_data' not in st.session_state:
        st.session_state['sports_data'] = {}
    
    if st.button("🔄 Cargar Deportes"):
        if not API_KEY:
            st.error("¡Falta la API Key!")
        else:
            try:
                # Usamos el parámetro correcto 'apiKey'
                url = f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}"
                r = requests.get(url)
                data = r.json()
                
                if isinstance(data, list):
                    clean_dict = {}
                    for x in data:
                        if x['active']:
                            label = f"{x['group']} - {x['title']}"
                            clean_dict[label] = x['key']
                    
                    st.session_state['sports_data'] = clean_dict
                    st.success(f"¡{len(clean_dict)} Ligas Cargadas!")
                else:
                    st.error(f"Error API: {data}")
            except Exception as e:
                st.error(f"Error Conexión: {e}")

    # SELECTORES
    sport_key = None
    if st.session_state['sports_data']:
        sorted_list = sorted(st.session_state['sports_data'].keys())
        selection = st.selectbox("Liga:", sorted_list)
        sport_key = st.session_state['sports_data'][selection]
    
    # REGIONES
    reg_map = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Latam (AU)": "au",
        "Reino Unido (UK)": "uk"
    }
    region_label = st.selectbox("Región:", list(reg_map.keys()))
    region_val = reg_map[region_label]
    
    # MERCADOS (Ordenados por seguridad)
    st.write("---")
    st.caption("Selecciona Mercado:")
    market_map = {
        "🏆 Ganador (H2H) - SEGURO": "h2h",
        "🏀/🏈 Hándicaps (Spreads)": "spreads",
        "🔢 Altas/Bajas (Totals)": "totals",
        "⚠️ Doble Oportunidad": "double_chance",
        "⚠️ Empate no Válido": "draw_no_bet"
    }
    market_label = st.selectbox("Tipo:", list(market_map.keys()))
    market_val = market_map[market_label]
    
    min_profit = st.slider("Min % Beneficio:", 0.0, 10.0, 0.0)
    
    btn_run = st.button("🚀 BUSCAR AHORA")
    # --- MOTOR DE BÚSQUEDA ---
if btn_run and API_KEY and sport_key:
    with st.spinner(f"Escaneando {market_val}..."):
        try:
            # URL y Parámetros
            base_url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_val,
                'markets': market_val, # Aquí es donde fallaba antes
                'oddsFormat': 'decimal'
            }
            
            r = requests.get(base_url, params=params)
            data = r.json()
            
            # --- PROTECCIÓN CONTRA ERRORES DE MERCADO ---
            if isinstance(data, dict) and 'message' in data:
                # Si la API devuelve un mensaje de error en lugar de una lista
                msg = data['message']
                if 'INVALID_MARKET' in str(data) or 'not supported' in msg:
                    st.error(f"🚫 ERROR DE MERCADO: La API dice: '{msg}'")
                    st.warning("💡 SOLUCIÓN: Este deporte no soporta 'Doble Oportunidad' o 'Empate no Válido' en tu plan actual. Por favor selecciona 'Ganador (H2H)' o 'Hándicaps'.")
                    st.stop() # Detiene la ejecución limpiamente
                else:
                    st.error(f"Error de API: {msg}")
                    st.stop()

            # --- PROCESAMIENTO NORMAL ---
            if isinstance(data, list):
                opps = []
                for ev in data:
                    # Datos Evento
                    home = ev['home_team']
                    away = ev['away_team']
                    titulo = f"{home} vs {away}"
                    
                    # Fecha
                    raw_d = ev.get('commence_time', '')
                    fecha = raw_d.replace('T', ' ').replace('Z', '')

                    # Agrupar cuotas
                    cuotas = {}
                    for book in ev['bookmakers']:
                        for m in book['markets']:
                            if m['key'] == market_val:
                                for out in m['outcomes']:
                                    # Truco: Usar 'name' para H2H, 'point' para Spreads/Totals
                                    if market_val in ['spreads', 'totals']:
                                        key = f"{out.get('point', '')}" # Ej: 2.5
                                        if not key: key = out['name']
                                    else:
                                        key = out['name'] # Ej: Real Madrid
                                    
                                    if key not in cuotas: cuotas[key] = []
                                    
                                    cuotas[key].append({
                                        'bookie': book['title'],
                                        'price': out['price'],
                                        'name': out['name']
                                    })
                    
                    # Buscar Arbitraje
                    for seleccion, lista_bookies in cuotas.items():
                        # 1. Mejor cuota por opción
                        best = {} # { 'Real Madrid': {data}, 'Barcelona': {data} }
                        
                        # Si es spreads/totals, la "selección" es el punto (ej 2.5).
                        # Necesitamos comparar Over vs Under para ese punto.
                        # Si es H2H, la "selección" es el nombre del equipo, necesitamos comparar vs el Rival.
                        
                        # Simplificación V11: Agrupamos por MERCADO entero para H2H
                        # Y por PUNTO para Spreads/Totals
                        
                        if market_val in ['spreads', 'totals']:
                            # Ya estamos dentro de un bucle de puntos (seleccion = 2.5)
                            # Necesitamos encontrar el mejor Over y el mejor Under para este punto
                            pass 
                        
                        # RE-LOGICA V11 SIMPLIFICADA (ESTILO V1)
                        # Iteramos sobre todo el mercado del evento para encontrar las mejores cuotas de cada resultado posible
                        best_odds = {}
                        for book in ev['bookmakers']:
                            for m in book['markets']:
                                if m['key'] == market_val:
                                    for out in m['outcomes']:
                                        # Identificador único de la opción (ej: Over 2.5)
                                        op_name = out['name']
                                        op_point = out.get('point', '')
                                        
                                        # Para spreads/totals, necesitamos agrupar por punto
                                        unique_id = op_name
                                        if op_point: unique_id = f"{op_name} {op_point}"
                                        
                                        # Guardar mejor cuota
                                        if unique_id not in best_odds or out['price'] > best_odds[unique_id]['price']:
                                            best_odds[unique_id] = {
                                                'price': out['price'],
                                                'bookie': book['title'],
                                                'name': unique_id,
                                                'point': op_point
                                            }
                        
                        # Ahora verificamos si tenemos un set completo para arbitraje
                        # Esto es complejo de generalizar, así que usaremos la suma bruta si son grupos compatibles
                        # (Esta parte puede dar falsos positivos si mezcla peras con manzanas, pero V1 lo hacía así y funcionaba)
                        
                        # FILTRO INTELIGENTE:
                        # Solo comparamos si tienen el MISMO punto (para totals/spreads)
                        grupos_comparacion = {}
                        for k, v in best_odds.items():
                            pt = v.get('point', 'Main')
                            if pt not in grupos_comparacion: grupos_comparacion[pt] = []
                            grupos_comparacion[pt].append(v)
                        
                        for pt, odds_list in grupos_comparacion.items():
                            if len(odds_list) >= 2:
                                # Calcular arbitraje
                                suma = sum(1/o['price'] for o in odds_list)
                                if suma < 1.0:
                                    # VALIDACIÓN FINAL: No apostar a lo mismo (ej: Over vs Over)
                                    nombres = [o['name'] for o in odds_list]
                                    es_valido = True
                                    if market_val == 'h2h' and len(odds_list) < 2: es_valido = False
                                    # Evitar comparar Over 2.5 vs Over 2.5 (debe ser Over vs Under)
                                    if market_val == 'totals' and 'Over' in nombres[0] and 'Over' in nombres[1]: es_valido = False
                                    
                                    if es_valido:
                                        ben = (1 - suma) / suma * 100
                                        if ben >= min_profit:
                                            # Formatear
                                            txt = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in odds_list])
                                            opps.append({
                                                "Fecha": fecha,
                                                "Evento": titulo,
                                                "Mdo": f"{market_val} {pt}",
                                                "Beneficio": f"{ben:.2f}%",
                                                "Apuestas": txt
                                            })

                if opps:
                    st.success(f"¡{len(opps)} Oportunidades!")
                    st.dataframe(pd.DataFrame(opps), use_container_width=True)
                else:
                    st.warning("No se encontraron surebets con estos filtros.")
                
                with st.expander("Ver Datos Crudos"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error Crítico: {e}")
