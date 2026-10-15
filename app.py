import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ---------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------
st.set_page_config(
    page_title="IoT Telemetry Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# ESTILOS CSS PERSONALIZADOS (DARK MODE FUTURISTA)
# ---------------------------
st.markdown("""
    <style>
        /* Fondo general de la app */
        .stApp {
            background-color: #0b0f19;
            color: #f3f4f6;
        }
        
        /* Tarjetas de métricas personalizadas */
        .metric-container {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
            text-align: center;
        }
        
        /* Estilos de títulos */
        h1, h2, h3 {
            color: #ffffff !important;
            font-family: 'Inter', sans-serif;
        }
        
        /* Sidebar estilizada */
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid #1e293b;
        }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# CREDENCIALES INFLUXDB
# ---------------------------
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
org = "miguelcmo"
bucket = "iot_telemetry_data"

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar:
    st.markdown("### 🎛️ Panel de Control")
    st.markdown("---")
    
    time_range = st.selectbox(
        "⏱️ Rango de tiempo",
        ["-1h", "-6h", "-12h", "-24h", "-7d"],
        index=3
    )

    refresh = st.slider("🔄 Auto-refresh (segundos)", 0, 60, 10)
    
    st.markdown("---")
    st.markdown("### 📡 Estado de Red")
    st.success("Conectado a InfluxDB Cloud")

# ---------------------------
# TÍTULO PRINCIPAL
# ---------------------------
st.title("🌟 Centro de Monitoreo IoT")
st.markdown("Visualización en tiempo real del clima ambiente de forma clara y dinámica.")
st.markdown("---")

# ---------------------------
# CARGA DE DATOS
# ---------------------------
@st.cache_data(ttl=10)
def load_data(time_range):
    client = InfluxDBClient(url=url, token=token, org=org)
    query_api = client.query_api()

    query = f'''
    from(bucket: "{bucket}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "humidity")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "temperature", "humidity"])
    '''

    result = query_api.query_data_frame(query)

    if isinstance(result, list):
        df = pd.concat(result)
    else:
        df = result

    if df.empty:
        return df

    df["_time"] = pd.to_datetime(df["_time"])
    df = df.sort_values("_time")

    return df

df = load_data(time_range)

# ---------------------------
# VISUALIZACIÓN
# ---------------------------
if not df.empty:
    
    # Asegurar tipos numéricos
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")

    # ---------------------------
    # TARJETAS DE MÉTRICAS LLAMATIVAS
    # ---------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="🔥 Temperatura Actual", value=f"{df['temperature'].iloc[-1]:.1f} °C")
    with col2:
        st.metric(label="💧 Humedad Actual", value=f"{df['humidity'].iloc[-1]:.1f} %")
    with col3:
        st.metric(label="📈 Temp. Promedio", value=f"{df['temperature'].mean():.1f} °C")
    with col4:
        st.metric(label="📊 Humedad Promedio", value=f"{df['humidity'].mean():.1f} %")

    st.markdown("---")

    # ---------------------------
    # GRÁFICOS SEPARADOS (FÁCILES DE ENTENDER)
    # ---------------------------
    
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("🌡️ Comportamiento de la Temperatura")
        fig_temp = px.area(
            df, 
            x="_time", 
            y="temperature",
            template="plotly_dark",
            color_discrete_sequence=["#ff5722"] # Naranja vibrante fuego
        )
        fig_temp.update_traces(line=dict(width=3), fill='tozeroy')
        fig_temp.update_layout(
            xaxis_title="", 
            yaxis_title="Grados Celsius (°C)",
            hovermode="x unified",
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with col_g2:
        st.subheader("💧 Comportamiento de la Humedad")
        fig_hum = px.area(
            df, 
            x="_time", 
            y="humidity",
            template="plotly_dark",
            color_discrete_sequence=["#00bcd4"] # Azul cian agua
        )
        fig_hum.update_traces(line=dict(width=3), fill='tozeroy')
        fig_hum.update_layout(
            xaxis_title="", 
            yaxis_title="Porcentaje (%)",
            hovermode="x unified",
            margin=dict(l=10, r=10, t=20, b=10)
        )
        st.plotly_chart(fig_hum, use_container_width=True)

    st.markdown("---")

    # ---------------------------
    # TENDENCIA SUAVIZADA (CADA 10 MIN)
    # ---------------------------
    st.subheader("⏱️ Resumen por Intervalos (Promedio cada 10 min)")
    
    df_resampled = (
        df.set_index("_time")[["temperature", "humidity"]]
        .resample("10min")
        .mean()
        .dropna()
        .reset_index()
    )

    fig_res = px.line(
        df_resampled,
        x="_time",
        y=["temperature", "humidity"],
        template="plotly_dark",
        color_discrete_map={"temperature": "#ff9800", "humidity": "#2196f3"}
    )
    fig_res.update_traces(line=dict(width=3))
    fig_res.update_layout(
        xaxis_title="",
        yaxis_title="Valor",
        legend_title="Variables",
        hovermode="x unified"
    )
    st.plotly_chart(fig_res, use_container_width=True)

    # ---------------------------
    # DATOS CRUDOS
    # ---------------------------
    with st.expander("📂 Ver tabla completa de registros crudos"):
        st.dataframe(df.tail(50), use_container_width=True)

else:
    st.warning("⚠️ No hay datos disponibles en este rango de tiempo.")

# ---------------------------
# AUTO REFRESH
# ---------------------------
if refresh > 0:
    st.rerun()
