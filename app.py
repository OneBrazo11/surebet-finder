import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V15: ECUADOR PRO (USDT/SKRILL) ---
st.set_page_config(layout="wide", page_title="Sniper V11.29 - Pro")
st.title("🇪🇨 SCANNER V11.29 - Ecuador Pro (USDT/Skrill)")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configuración")
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # CHECKER DE CREDITOS (Tu herramienta Pro)
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

    # --- 2. TUS CASAS (ARSENAL V15) ---
    st.header("2. Casas Activas")
    
    # Lista Maestra (Solo las que sirven en Ecuador/Latam + Cripto)
    casas_posibles = [
        "Pinnacle",       # El Rey (Cuotas base)
        "BetOnline.ag",   # El Rey del USDT (Alta liquidez)
        "Betfair",        # Exchange (Skrill/Neteller)
        "1xBet",          # Clásica Latam
        "Bet365",         # La más popular
        "Betsson",        # Muy sólida en Ecuador
        "Betway",         # Confiable
        "Marathon Bet",   # Cuotas altas
        "Coolbet",        # Buena interfaz
        "William Hill",   # Clásica seria (Skrill)
        "888sport",       # Buena para empezar
        "Matchbook",      # Exchange alternativo
        "LeoVegas",       # Nueva en Latam
        "LowVig.ag",      # Comisiones bajas (USDT)
        "MyBookie.ag",    # Bonos cripto
        "DAZN Bet"        # Competitiva
    ]
    
    # SELECCIÓN AUTOMÁTICA (Las "Titulares")
    default_ecuador = [
        "Pinnacle", "BetOnline.ag", "1xBet", "Bet365", 
        "Betsson", "Betway", "Marathon Bet", "Betfair"
    ]
    
    mis_casas = st.multiselect(
        "Filtrar Casas:", 
        options=casas_posibles, 
        default=default_ecuador
    )
    
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
    # --- BLOQUE 2: MOTOR LÓGICO Y CÁLCULO ---
if btn_buscar and API_KEY and sport_key:
    # Usamos región GLOBAL para traer Pinnacle (EU) y BetOnline (US) a la vez
    region_code = "us,uk,eu,au" 
    
    with st.spinner(f"Escaneando {sport_key}..."):
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
            
            # 1. Validación de Error de API (Mercados bloqueados)
            if isinstance(data, dict) and 'message' in data:
                if 'not supported' in data['message']:
                    st.error(f"🚫 ERROR: El mercado '{m_label}' no está disponible.")
                    st.info("💡 Intenta con 'Ganador (H2H)' o 'Hándicaps'.")
                    st.stop()
            
            # 2. Procesamiento Matemático
            if isinstance(data, list):
                oportunidades = []
                
                for ev in data:
                    fecha = ev.get('commence_time','').replace('T',' ').replace('Z','')
                    evento = f"{ev['home_team']} vs {ev['away_team']}"
                    
                    # --- FASE A: AGRUPAMIENTO + FILTRADO ---
                    grupos = {}
                    
                    for book in ev['bookmakers']:
                        casa_nombre = book['title']
                        
                        # === EL FILTRO DE TUS CASAS ===
                        es_permitida = False
                        for permitido in mis_casas:
                            # Coincidencia flexible (ej: "Unibet" acepta "Unibet (UK)")
                            if permitido.lower() in casa_nombre.lower():
                                es_permitida = True
                                break
                        
                        if not es_permitida:
                            continue # Si no es de tus casas, la ignoramos
                            
                        # Extraer cuotas
                        for m in book['markets']:
                            if m['key'] == m_val:
                                for out in m['outcomes']:
                                    # Agrupar por Punto (para Totales/Handicaps) o 'Moneyline'
                                    pt = out.get('point', 'Moneyline')
                                    
                                    if pt not in grupos: grupos[pt] = []
                                    
                                    grupos[pt].append({
                                        'bookie': casa_nombre,
                                        'name': out['name'],
                                        'price': out['price']
                                    })
                    
                    # --- FASE B: CÁLCULO DE SUREBETS ---
                    for pt, cuotas in grupos.items():
                        # Buscar la MEJOR cuota para cada opción
                        mejor_opcion = {}
                        for c in cuotas:
                            sel = c['name']
                            if sel not in mejor_opcion or c['price'] > mejor_opcion[sel]['price']:
                                mejor_opcion[sel] = c
                        
                        # Verificar si hay suficientes lados (mínimo 2)
                        if len(mejor_opcion) >= 2:
                            finales = list(mejor_opcion.values())
                            suma_inversa = sum(1/x['price'] for x in finales)
                            
                            # Fórmula de Arbitraje
                            if suma_inversa < 1.0:
                                ben = (1 - suma_inversa) / suma_inversa * 100
                                
                                if ben >= min_profit:
                                    # Validación extra: Evitar "Over vs Over"
                                    nombres = [x['name'] for x in finales]
                                    es_valido = True
                                    if m_val == 'totals' and nombres[0] == nombres[1]: 
                                        es_valido = False
                                    
                                    if es_valido:
                                        # Formato visual
                                        detalles = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in finales])
                                        
                                        oportunidades.append({
                                            "Fecha": fecha,
                                            "Evento": evento,
                                            "Mercado/Sel": pt,
                                            "Beneficio": f"{ben:.2f}%",
                                            "Apuestas": detalles
                                        })
                
                # --- RESULTADOS ---
                if oportunidades:
                    st.success(f"¡{len(oportunidades)} Oportunidades Encontradas!")
                    st.dataframe(pd.DataFrame(oportunidades), use_container_width=True)
                else:
                    st.warning("No se encontraron oportunidades en las casas seleccionadas.")
                    
                with st.expander("Ver Datos Crudos (API)"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error Crítico: {e}")
