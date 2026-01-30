import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACION ---
st.set_page_config(layout="wide", page_title="Sniper V8.7")
st.title("🚀 Sniper V8.7 - Final")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # --- CALCULADORA ---
    with st.expander("🧮 Calculadora", expanded=True):
        modos = ["2 Opciones (Tenis)", "3 Opciones (Futbol)"]
        modo = st.radio("Modo:", modos)
        bank = st.number_input("Bank ($)", value=100.0)
        
        if modo == modos[0]:
            c1 = st.number_input("Cuota A", value=2.0)
            c2 = st.number_input("Cuota B", value=2.0)
            if c1 > 0 and c2 > 0:
                inv = (1/c1 + 1/c2)
                gan = (bank / inv) - bank
                st.write(f"Ganancia: :green[${gan:.2f}]")
                s1 = (bank/c1)/inv
                s2 = (bank/c2)/inv
                c_a, c_b = st.columns(2)
                c_a.metric("A", f"${s1:.0f}")
                c_b.metric("B", f"${s2:.0f}")
        else:
            c1 = st.number_input("Local", value=2.5)
            c2 = st.number_input("Empate", value=3.2)
            c3 = st.number_input("Visita", value=3.0)
            if c1 > 0 and c2 > 0 and c3 > 0:
                inv = (1/c1 + 1/c2 + 1/c3)
                gan = (bank / inv) - bank
                st.write(f"Ganancia: :green[${gan:.2f}]")
                s1 = (bank/c1)/inv
                s2 = (bank/c2)/inv
                s3 = (bank/c3)/inv
                k1, k2, k3 = st.columns(3)
                k1.metric("L", f"${s1:.0f}")
                k2.metric("E", f"${s2:.0f}")
                k3.metric("V", f"${s3:.0f}")

    # --- CARGAR LIGAS ---
    st.header("2. Escaner")
    if 'sports' not in st.session_state:
        st.session_state['sports'] = {}

    if API_KEY:
        if st.button("🔄 Cargar Ligas"):
            try:
                url = "https://api.the-odds-api.com/v4/sports/"
                # AQUI ESTA LA CORRECCION DEL ERROR 'APIKEY':
                p = {'apiKey': API_KEY}
                r = requests.get(url, params=p)
                data = r.json()
                
                if isinstance(data, list):
                    temp = {}
                    for x in data:
                        if x['active']:
                            label = f"{x['group']} - {x['title']}"
                            temp[label] = x['key']
                    st.session_state['sports'] = temp
                    st.success("¡Cargado!")
                else:
                    st.error(f"Error: {data}")
            except Exception as e:
                st.error(f"Fallo: {e}")

    # --- FILTROS ---
    sport_key = None
    if st.session_state['sports']:
        lista = sorted(st.session_state['sports'].keys())
        sel = st.selectbox("Liga:", lista)
        sport_key = st.session_state['sports'][sel]

    regs = ["Global (Todas)", "Europa (EU)", "USA (US)", "Latam (AU)"]
    r_sel = st.selectbox("Region", regs)
    mapa = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Latam (AU)": "au"
    }

    # AQUI ESTAN TUS MERCADOS FALTANTES:
    mis_mercados = [
        "h2h", 
        "spreads", 
        "totals", 
        "draw_no_bet", 
        "double_chance"
    ]
    m_tipo = st.selectbox("Mercado", mis_mercados)
    
    min_p = st.slider("Min %", 0.0, 10.0, 0.0)
    btn = st.button("🔎 Buscar")# --- LOGICA DEL ESCANER ---
def escanear(bookmakers, m_target):
    grupo = {}
    for book in bookmakers:
        for m in book['markets']:
            if m['key'] == m_target:
                for out in m['outcomes']:
                    nom = out['name']
                    pr = out['price']
                    # Usamos point para spreads/totals, o 'ML'
                    pt = out.get('point', 'ML')
                    
                    if pt not in grupo: grupo[pt] = []
                    
                    item = {'bookie': book['title'], 'name': nom, 'price': pr}
                    grupo[pt].append(item)
    
    filas = []
    for punto, opciones in grupo.items():
        mejor = {}
        for op in opciones:
            n = op['name']
            if n not in mejor or op['price'] > mejor[n]['price']:
                mejor[n] = op
        
        count = len(mejor)
        if count >= 2:
            lados = list(mejor.values())
            suma = sum(1/x['price'] for x in lados)
            
            valido = False
            if suma < 1.0:
                # Reglas de validacion
                if m_target == 'h2h':
                    valido = True if count >= 2 else False
                elif m_target == 'double_chance':
                    valido = True if count >= 3 else False
                else:
                    # Spreads, Totals, DNB
                    valido = True if count >= 2 else False
            
            if valido and suma < 1.0:
                margen = (1 - suma) / suma * 100
                if margen >= min_p:
                    txts = []
                    for b in lados:
                        t = f"{b['name']}: {b['bookie']} @ {b['price']}"
                        txts.append(t)
                    
                    filas.append({
                        "Mercado": m_target,
                        "Sel": punto,
                        "Beneficio %": round(margen, 2),
                        "Apuestas": " | ".join(txts)
                    })
    return filas

# --- EJECUCION ---
if btn and API_KEY and sport_key:
    with st.spinner("Escaneando..."):
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': mapa[r_sel],
                'markets': m_tipo,
                'oddsFormat': 'decimal'
            }
            r = requests.get(url, params=params)
            data = r.json()
            
            if not isinstance(data, list):
                st.error(f"Error API: {data}")
            else:
                todo = []
                for ev in data:
                    tit = f"{ev['home_team']} vs {ev['away_team']}"
                    raw_d = ev.get('commence_time', '')
                    try:
                        dt = datetime.strptime(raw_d, "%Y-%m-%dT%H:%M:%SZ")
                        fecha = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        fecha = raw_d
                    
                    gaps = escanear(ev['bookmakers'], m_tipo)
                    for g in gaps:
                        g['Evento'] = tit
                        g['Fecha'] = fecha
                        todo.append(g)
                
                if todo:
                    st.success(f"¡{len(todo)} Oportunidades!")
                    df = pd.DataFrame(todo)
                    cols = ['Fecha', 'Evento', 'Mercado', 'Beneficio %', 'Apuestas']
                    st.dataframe(df[cols], use_container_width=True)
                else:
                    st.warning("Sin oportunidades.")
                
                with st.expander("Debug"):
                    st.json(data)
        except Exception as e:
            st.error(f"Error critico: {e}")
