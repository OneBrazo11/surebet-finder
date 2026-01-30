import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACION V9.1 ---
st.set_page_config(layout="wide", page_title="Sniper V9.1 Global")
st.title("⚡ Sniper V9.1 - GLOBAL")

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Configuración")
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""

    # Calculadora
    with st.expander("🧮 Calculadora Rápida"):
        modo = st.radio("Tipo:", ["2 Vías (Tenis/DNB)", "3 Vías (Fútbol)"])
        bank = st.number_input("Banco ($)", value=100.0)
        
        if "2" in modo:
            cA = st.number_input("Cuota A", 2.0)
            cB = st.number_input("Cuota B", 2.0)
            if cA and cB:
                inv = 1/cA + 1/cB
                st.write(f"Beneficio: :green[${(bank/inv)-bank:.2f}]")
                st.write(f"Apostar: A=${(bank/cA)/inv:.0f} | B=${(bank/cB)/inv:.0f}")
        else:
            c1 = st.number_input("Local", 2.5)
            cX = st.number_input("Empate", 3.2)
            c2 = st.number_input("Visita", 3.0)
            if c1 and cX and c2:
                inv = 1/c1 + 1/cX + 1/c2
                st.write(f"Beneficio: :green[${(bank/inv)-bank:.2f}]")
                st.write(f"L=${(bank/c1)/inv:.0f} | E=${(bank/cX)/inv:.0f} | V=${(bank/c2)/inv:.0f}")

    # Cargar Ligas
    st.header("2. Ligas")
    if 'sports' not in st.session_state: st.session_state['sports'] = {}
    
    if st.button("🔄 Cargar Ligas"):
        if not API_KEY:
            st.error("¡Falta la API Key!")
        else:
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}")
                data = r.json()
                if isinstance(data, list):
                    st.session_state['sports'] = {f"{x['group']} - {x['title']}": x['key'] for x in data if x['active']}
                    st.success(f"¡{len(data)} Ligas Cargadas!")
                else:
                    st.error(f"Error API: {data}")
            except Exception as e:
                st.error(f"Error Conexión: {e}")

    # Filtros
    sport_key = None
    if st.session_state['sports']:
        lista = sorted(st.session_state['sports'].keys())
        sel = st.selectbox("Liga:", lista)
        sport_key = st.session_state['sports'][sel]

    # Selector Regiones
    mapa_regiones = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Reino Unido (UK)": "uk",
        "Latam/Aus (AU)": "au"
    }
    region_label = st.selectbox("Región", list(mapa_regiones.keys()))
    region_code = mapa_regiones[region_label]
    
    # Selector Mercados (Aquí se te cortaba antes)
    lista_mercados = ["h2h", "spreads", "totals", "draw_no_bet", "double_chance"]
    mercado = st.selectbox("Mercado", lista_mercados)
    
    min_pct = st.slider("Min %", 0.0, 10.0, 0.0)
    btn_buscar = st.button("🔎 BUSCAR AHORA")
    # --- MOTOR PRINCIPAL ---
if btn_buscar and API_KEY and sport_key:
    with st.spinner(f"Escaneando en {region_label}..."):
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_code,
                'markets': mercado,
                'oddsFormat': 'decimal'
            }
            r = requests.get(url, params=params)
            data = r.json()

            if not isinstance(data, list):
                st.error(f"La API rechazó la búsqueda: {data}")
            else:
                resultados = []
                for ev in data:
                    # Fecha
                    fecha = ev.get('commence_time', '').replace('T', ' ').replace('Z', '')
                    evento = f"{ev['home_team']} vs {ev['away_team']}"
                    
                    # Agrupar cuotas
                    cuotas = {}
                    for book in ev['bookmakers']:
                        for m in book['markets']:
                            if m['key'] == mercado:
                                for out in m['outcomes']:
                                    sel = out.get('point', out['name'])
                                    if sel not in cuotas: cuotas[sel] = []
                                    item = {'bookie': book['title'], 'price': out['price'], 'name': out['name']}
                                    cuotas[sel].append(item)
                    
                    # Calcular Arbitraje
                    for sel, opciones in cuotas.items():
                        best = {}
                        for op in opciones:
                            if op['name'] not in best or op['price'] > best[op['name']]['price']:
                                best[op['name']] = op
                        
                        if len(best) >= 2:
                            lados = list(best.values())
                            suma = sum(1/x['price'] for x in lados)
                            
                            es_valido = False
                            if suma < 1.0:
                                if mercado == 'h2h' and len(best) >= 2: es_valido = True
                                elif mercado == 'double_chance' and len(best) >= 3: es_valido = True
                                elif mercado in ['spreads', 'totals', 'draw_no_bet'] and len(best) >= 2: es_valido = True
                            
                            if es_valido:
                                ben = (1 - suma) / suma * 100
                                if ben >= min_pct:
                                    txt = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in lados])
                                    resultados.append({
                                        "Fecha": fecha,
                                        "Evento": evento,
                                        "Mdo": mercado,
                                        "Beneficio": f"{ben:.2f}%",
                                        "Apuesta": txt
                                    })

                if resultados:
                    st.success(f"¡{len(resultados)} Oportunidades!")
                    st.dataframe(pd.DataFrame(resultados), use_container_width=True)
                else:
                    st.warning("No hay oportunidades con estos filtros.")
                
                with st.expander("Ver Datos Crudos (API)"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error Crítico: {e}")
