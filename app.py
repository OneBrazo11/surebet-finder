import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Pixel Trader Sniper V8 🚀", layout="wide")
st.title("🚀 Pixel Trader Sniper - Estación de Trabajo")

# --- BARRA LATERAL (CONFIGURACIÓN + CALCULADORAS) ---
with st.sidebar:
    st.header("1. Credenciales")
    API_KEY = st.text_input("Tu API Key", type="password")
    
    # --- CALCULADORA 1: STAKES (SUREBETS) ---
    with st.expander("🧮 Calculadora de Stakes", expanded=True):
        st.caption("Calcula cuánto apostar para ganar seguro.")
        
        calc_mode = st.radio("Tipo de Apuesta", ["2 Opciones (Tenis/DNB/Totales)", "3 Opciones (1X2 Fútbol)"])
        total_bank = st.number_input("Inversión Total ($)", value=100, step=10)
        
        if calc_mode == "2 Opciones (Tenis/DNB/Totales)":
            c1 = st.number_input("Cuota A", value=2.00, step=0.01)
            c2 = st.number_input("Cuota B", value=2.00, step=0.01)
            
            if c1 > 0 and c2 > 0:
                arb_perc = (1/c1 + 1/c2) * 100
                profit = (total_bank / (arb_perc/100)) - total_bank
                
                st.markdown(f"**Beneficio:** :green[${profit:.2f}]")
                
                # Cálculo de Stakes
                s1 = (total_bank * (1/c1)) / (arb_perc/100)
                s2 = (total_bank * (1/c2)) / (arb_perc/100)
                
                st.write("---")
                col1, col2 = st.columns(2)
                col1.metric("Apuesta A", f"${s1:.2f}")
                col2.metric("Apuesta B", f"${s2:.2f}")
                
                st.info(f"💡 **Anti-Limita:** Apuesta **${int(s1)}** y **${int(s2)}**.")

        else: # 3 Opciones
            c1 = st.number_input("Cuota 1 (Local)", value=2.50)
            c2 = st.number_input("Cuota X (Empate)", value=3.20)
            c3 = st.number_input("Cuota 2 (Visita)", value=3.00)
            
            if c1 > 0 and c2 > 0 and c3 > 0:
                arb_perc = (1/c1 + 1/c2 + 1/c3) * 100
                profit = (total_bank / (arb_perc/100)) - total_bank
                
                st.markdown(f"**Beneficio:** :green[${profit:.2f}]")
                
                s1 = (total_bank * (1/c1)) / (arb_perc/100)
                s2 = (total_bank * (1/c2)) / (arb_perc/100)
                s3 = (total_bank * (1/c3)) / (arb_perc/100)
                
                st.write("---")
                c_a, c_b, c_c = st.columns(3)
                c_a.metric("Local", f"${s1:.2f}")
                c_b.metric("Empate", f"${s2:.2f}")
                c_c.metric("Visita", f"${s3:.2f}")

    # --- CALCULADORA 2: PROYECCIÓN (INTERÉS COMPUESTO) ---
    with st.expander("📈 Proyección de Crecimiento", expanded=False):
        st.caption("El poder del interés compuesto diario.")
        
        initial_cap = st.number_input("Capital Inicial ($)", value=50.0)
        daily_yield = st.number_input("Rentabilidad Diaria (%)", value=1.5, step=0.1)
        days = st.slider("Días a proyectar", 30, 365, 30)
        
        final_cap = initial_cap * ((1 + daily_yield/100) ** days)
        profit_total = final_cap - initial_cap
        
        st.metric("Capital Final", f"${final_cap:,.2f}")
        st.metric("Ganancia Neta", f"${profit_total:,.2f}", delta=f"{((final_cap/initial_cap)-1)*100:.0f}%")
        
        # Gráfico simple
        chart_data = pd.DataFrame({
            'Día': range(days + 1),
            'Capital': [initial_cap * ((1 + daily_yield/100) ** d) for d in range(days + 1)]
        })
        st.line_chart(chart_data, x='Día', y='Capital')

    # --- CARGA DE DEPORTES ---
    st.header("2. Escáner de Mercado")
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    if API_KEY:
        if st.button("🔄 Actualizar Ligas"):
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}")
                r.raise_for_status()
                data = r.json()
                st.session_state['sports_list'] = {f"{x['group']} - {x['title']}": x['key'] for x in data if x['active']}
                st.success("¡Ligas cargadas!")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state['sports_list']:
        sorted_labels = sorted(st.session_state['sports_list'].keys())
        sel_label = st.selectbox("Liga:", sorted_labels)
        sport_key = st.session_state['sports_list'][sel_label]
    else:
        sport_key = None

    region_mode = st.selectbox("Región", ["Global (Todas)", "Europa (EU)", "USA (US)", "Latam/Aus (AU)"])
    reg_map = {"Global (Todas)": "us,uk,eu,au", "Europa (EU)": "eu", "USA (US)": "us", "Latam/Aus (AU)": "au"}
    
    market_type = st.selectbox("Mercado", [
        "h2h",              # Ganador (1X2 o 1-2)
        "spreads",          # Hándicaps
        "totals",           # Altas/Bajas
        "draw_no_bet",      # Empate no válido
        "double_chance"     # Doble Oportunidad
    ])
    
    min_profit = st.slider("Beneficio Mínimo (%)", 0.0, 10.0, 0.0) 
    
    if st.button("🔎 Buscar Surebets"):
        run_analysis = True
    else:
        run_analysis = False

# --- LÓGICA DE ESCANEO ---
def get_arbitrage(outcomes, market_name):
    grouped = {}
    for book in outcomes:
        for market in book['markets']:
            if market['key'] == market_name:
                for outcome in market['outcomes']:
                    name = outcome['name']
                    price = outcome['price']
                    point = outcome.get('point', 'Moneyline')
                    
                    if point not in grouped: grouped[point] = []
                    grouped[point].append({'bookie': book['title'], 'name': name, 'price': price})

    opps = []
    for point, options in grouped.items():
        best = {}
        for opt in options:
            if opt['name'] not in best or opt['price'] > best[opt['name']]['price']:
                best[opt['name']] = opt
        
        # Filtro de seguridad para mercados
        if len(best) >= 2: 
            sides = list(best.values())
            arb_sum = sum(1/s['price'] for s in sides)
            
            valid_arb = False
            if arb_sum < 1.0:
                is_3way_market = (market_name == 'h2h' and len(best) == 3) or (market_name == 'double_chance' and len(best) >= 3)
                is_2way_market = (market_name in ['spreads', 'totals', 'draw_no_bet']) or (market_name == 'h2h' and len(best) == 2)
                valid_arb = True 

            if valid_arb and arb_sum < 1.0:
                profit = (1 - arb_sum) / arb_sum * 100
                if profit >= min_profit:
                    bets_str = " | ".join([f"{s['name']}: {s['bookie']} @ {s['price']}" for s in sides])
                    opps.append({
                        "Mercado": market_name,
                        "Selección": point,
                        "Beneficio %": round(profit, 2),
                        "Apuestas a realizar": bets_str
                    })
    return opps

if run_analysis and API_KEY and sport_key:
    with st.spinner(f'Analizando {market_type} en {sport_key}...'):
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
            params = {'api_key': API_KEY, 'regions': reg_map[region_mode], 'markets': market_type, 'oddsFormat': 'decimal'}
            
            data = requests.get(url, params=params).json()
            all_opps = []
            
            for event in data:
                opps = get_arbitrage(event['bookmakers'], market_type)
                try:
                    dt = datetime.strptime(event['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
                except: dt = event['commence_time']

                for op in opps:
                    op['Evento'] = f"{event['home_team']} vs {event['away_team']}"
                    op['Fecha'] = dt
                    all_opps.append(op)
            
            if all_opps:
                st.success(f"¡{len(all_opps)} Oportunidades!")
                df = pd.DataFrame(all_opps)
                # AQUÍ ESTABA TU ERROR ANTES, AHORA ESTÁ CORREGIDO:
                cols = ['Fecha', 'Evento', 'Mercado', 'Beneficio %', 'Apuestas a realizar']
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.warning("No se encontraron Gaps rentables con estos filtros.")
            
            with st.expander("Ver Datos Crudos (Debug)"):
                st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")
