import streamlit as st
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------
# CONFIGURACIÓN Y ESTILO PASTELES
# ---------------------------
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
org = "miguelcmo"
bucket = "iot_telemetry_data"

# CORREGIDO: Se usa 'layout' en lugar de 'page_layout'
st.set_page_config(page_title="Monitoreo IoT", layout="wide")

# Inyección de Estilos CSS para diseño en tonos pasteles, tarjetas y tipografía suave
st.markdown("""
    <style>
    /* Fondo general suave pastel */
    .stApp {
        background-color: #F8F9FA;
        color: #4A4A4A;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sidebar en tono pastel cálido */
    [data-testid="stSidebar"] {
        background-color: #F0F2F5;
        border-right: 1px solid #E2E8F0;
    }

    /* Tarjetas de métricas personalizadas */
    div.metric-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
        text-align: center;
    }

    /* Encabezados limpios */
    h1, h2, h3 {
        color: #2D3748;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌱 Monitoreo Ambiental IoT")
st.markdown("Visualización intuitiva en tiempo real de temperatura y humedad.")

# Sidebar
st.sidebar.header("⚙️ Configuración")

time_range = st.sidebar.selectbox(
    "Rango de tiempo",
    ["-1h", "-6h", "-12h", "-24h", "-7d"],
    index=3
)

refresh = st.sidebar.slider("Auto-actualización (segundos)", 0, 60, 10)

# ---------------------------
# FUNCIÓN DE DATOS
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

# ---------------------------
# CARGAR DATOS
# ---------------------------
df = load_data(time_range)

# ---------------------------
# MÉTRICAS PRINCIPALES
# ---------------------------
if not df.empty:
    col1, col2, col3, col4 = st.columns(4)

    # Asegurar tipos numéricos para cálculos seguros
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")

    with col1:
        st.metric(label="🌡️ Temperatura Actual", value=f"{df['temperature'].iloc[-1]:.1f} °C")
    with col2:
        st.metric(label="💧 Humedad Actual", value=f"{df['humidity'].iloc[-1]:.1f} %")
    with col3:
        st.metric(label="📊 Promedio Temperatura", value=f"{df['temperature'].mean():.1f} °C")
    with col4:
        st.metric(label="📊 Promedio Humedad", value=f"{df['humidity'].mean():.1f} %")

    st.markdown("---")

# ---------------------------
# GRÁFICAS INTUITIVAS (TONOS PASTELES)
# ---------------------------
if not df.empty:
    
    # 1. Gráfica de Serie de Tiempo Principal (Separada y limpia)
    st.subheader("📈 Comportamiento en el Tiempo")
    st.markdown("Evolución detallada de las variables ambientales de forma independiente para facilitar su lectura.")

    fig = go.Figure()
    
    # Temperatura - Color Coral Pastel suave
    fig.add_trace(go.Scatter(
        x=df["_time"], y=df["temperature"],
        name="Temperatura (°C)",
        line=dict(color="#FF8B8B", width=3),
        mode='lines'
    ))
    
    # Humedad - Color Celeste Pastel suave
    fig.add_trace(go.Scatter(
        x=df["_time"], y=df["humidity"],
        name="Humedad (%)",
        line=dict(color="#73C2FB", width=3),
        mode='lines'
    ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=30, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------
    # RESAMPLING (Tendencia suavizada)
    # ---------------------------
    st.subheader("⏱️ Tendencia Suavizada (Promedio cada 10 min)")
    st.markdown("Vista general simplificada para comprender los cambios estables a lo largo del periodo.")

    df["_time"] = pd.to_datetime(df["_time"])
    df_resampled = (
        df.set_index("_time")[["temperature", "humidity"]]
        .resample("10min")
        .mean()
        .dropna()
    )

    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=df_resampled.index, y=df_resampled["temperature"],
        name="Temp. Promedio",
        line=dict(color="#E27396", width=3),
        fill='tozeroy',
        fillcolor='rgba(226, 115, 150, 0.1)'
    ))
    
    fig2.add_trace(go.Scatter(
        x=df_resampled.index, y=df_resampled["humidity"],
        name="Humedad Promedio",
        line=dict(color="#84A98C", width=3), # Verde menta pastel
        fill='tozeroy',
        fillcolor='rgba(132, 169, 140, 0.1)'
    ))

    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=30, b=20)
    )

    st.plotly_chart(fig2, use_container_width=True)

    # ---------------------------
    # DATOS CRUDOS (Diseño colapsable)
    # ---------------------------
    with st.expander("📋 Ver registros detallados en tabla"):
        st.dataframe(df.tail(50), use_container_width=True)

else:
    st.warning("⚠️ No hay datos disponibles en este rango de tiempo para mostrar.")

# ---------------------------
# AUTO REFRESH
# ---------------------------
if refresh > 0:
    st.rerun()
