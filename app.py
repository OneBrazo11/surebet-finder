import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Pixel Trader Sniper V8.1 🚀", layout="wide")
st.title("🚀 Pixel Trader Sniper - Estación de Trabajo")

# --- BARRA LATERAL (CONFIGURACIÓN + CALCULADORAS) ---
with st.sidebar:
    st.header("1. Credenciales")
    API_KEY = st.text_input("Tu API Key", type="password")
    
    # --- CALCULADORA 1: STAKES (SUREBETS) ---
    with st.expander("🧮 Calculadora de Stakes", expanded=True):
        st.caption("Calcula cuánto apostar para ganar seguro.")
        
        calc_mode = st.radio("Tipo de Apuesta", ["2 Opciones (Tenis/DNB/Totales)", "3 Opciones (1X2 Fútbol)"])
        total_bank = st.number_input("Inversión Total ($)", value=100.0, step=10.0)
        
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
        
        st.metric("Capital Final", f"${
