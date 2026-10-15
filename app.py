import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px

# ---------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------
st.set_page_config(
    page_title="IoT Telemetry Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# ESTILOS CSS PERSONALIZADOS
# ---------------------------
st.markdown("""
    <style>
        /* Estilo general del fondo y tipografía */
        .main {
            background-color: #f8f9fa;
        }
        /* Contenedores de métricas personalizados */
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e3e6f0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
        }
        /* Títulos de sección */
        h3 {
            color: #2c3e50;
            font-weight: 600;
            padding-top: 10px;
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
    st.image("https://img.icons8.com/color/96/control-panel.png", width=60)
    st.header("⚙️ Configuración")
    
    time_range = st.selectbox(
        "Rango de tiempo",
        ["-1h", "-6h", "-12h", "-24h", "-7d"],
        index=3
    )

    refresh = st.slider("Auto-refresh (segundos)", 0, 60, 10)
    
    st.markdown("---")
    st.markdown("### ℹ️ Info del Sistema")
    st.info(f"**Bucket:** {bucket}\n\n**Organización:** {org}")

# ---------------------------
# TÍTULO PRINCIPAL
# ---------------------------
st.title("🌡️ IoT Telemetry Dashboard")
st.markdown("Monitoreo en tiempo real de variables ambientales con análisis avanzado.")
st.markdown("---")

# ---------------------------
# FUNCIÓN DE CARGA DE DATOS
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

# Cargar datos
df = load_data(time_range)

# ---------------------------
# VISUALIZACIÓN DE DATOS
# ---------------------------
if not df.empty:
    # ---------------------------
    # MÉTRICAS PRINCIPALES
    # ---------------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="🌡️ Temp Actual", value=f"{df['temperature'].iloc[-1]:.2f} °C", delta=f"{df['temperature'].iloc[-1] - df['temperature'].iloc[-2]:.2f} °C" if len(df) > 1 else None)
    with col2:
        st.metric(label="💧 Humedad Actual", value=f"{df['humidity'].iloc[-1]:.2f} %", delta=f"{df['humidity'].iloc[-1] - df['humidity'].iloc[-2]:.2f} %" if len(df) > 1 else None)
    with col3:
        st.metric(label="📊 Temp Promedio", value=f"{df['temperature'].mean():.2f} °C")
    with col4:
        st.metric(label="📊 Humedad Promedio", value=f"{df['humidity'].mean():.2f} %")

    st.markdown("---")

    # ---------------------------
    # GRÁFICO 1: SERIE DE TIEMPO PRINCIPAL
    # ---------------------------
    st.subheader("📈 Comportamiento en Tiempo Real")
    
    # Renombrar columnas temporalmente para la leyenda del gráfico
    df_melted = df.melt(id_vars=["_time"], value_vars=["temperature", "humidity"], 
                        var_name="Variable", value_name="Valor")
    df_melted["Variable"] = df_melted["Variable"].map({"temperature": "Temperatura (°C)", "humidity": "Humedad (%)"})

    fig = px.line(
        df_melted,
        x="_time",
        y="Valor",
        color="Variable",
        template="plotly_white",
        color_discrete_map={"Temperatura (°C)": "#ff4b4b", "Humedad (%)": "#0068c9"}
    )
    
    fig.update_traces(mode="lines+markers", marker=dict(size=3))
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="",
        yaxis_title=""
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # RESAMPLING Y SEGUNDO GRÁFICO
    # ---------------------------
    st.subheader("⏱️ Tendencia Suavizada (Promedio cada 10 min)")

    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")
    
    df_resampled = (
        df.set_index("_time")[["temperature", "humidity"]]
        .resample("10min")
        .mean()
        .dropna()
        .reset_index()
    )

    df_resampled_melted = df_resampled.melt(id_vars=["_time"], value_vars=["temperature", "humidity"], 
                                            var_name="Variable", value_name="Valor")
    df_resampled_melted["Variable"] = df_resampled_melted["Variable"].map({"temperature": "Temp Promedio (°C)", "humidity": "Humedad Promedio (%)"})

    fig2 = px.area(
        df_resampled_melted,
        x="_time",
        y="Valor",
        color="Variable",
        template="plotly_white",
        color_discrete_map={"Temp Promedio (°C)": "#ffa15a", "Humedad Promedio (%)": "#ab63fa"}
    )
    
    fig2.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="",
        yaxis_title=""
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ---------------------------
    # DATOS CRUDOS EN TABLA EXPANDIBLE
    # ---------------------------
    with st.expander("📋 Ver registros crudos (últimos 50 datos)"):
        st.dataframe(df.tail(50), use_container_width=True)

else:
    st.warning("⚠️ No hay datos disponibles en este rango de tiempo. Verifica la conexión con tu dispositivo IoT o el bucket de InfluxDB.")

# ---------------------------
# AUTO REFRESH
# ---------------------------
if refresh > 0:
    st.rerun()
