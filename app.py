
import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient
from streamlit_autorefresh import st_autorefresh

# ==========================================
# CONFIGURACIÓN DE INFLUXDB
# ==========================================
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "PEGA_AQUI_TU_TOKEN_VIGENTE"
org = "miguelcmo"
bucket = "iot_telemetry_data"

# ==========================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ==========================================
st.set_page_config(
    page_title="Mi espacio | IoT",
    page_icon="🌷",
    layout="wide"
)

st.title("🌷 El clima de tu espacio")
st.markdown(
    "Descubre cómo cambian la temperatura y la humedad "
    "de tu entorno."
)
