import streamlit as st
from streamlit_autorefresh import st_autorefresh
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# CONFIGURACIÓN DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Mi clima IoT",
    page_icon="🌤️",
    layout="wide"
)

# =========================================================
# ESTILO VISUAL
# =========================================================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #F7FBFF 0%, #FFFDF7 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            color: #214761;
        }
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #DCEAF3;
            border-radius: 18px;
            padding: 16px;
            box-shadow: 0 4px 14px rgba(33, 71, 97, 0.08);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 1rem;
            color: #4D6B7C;
        }
        div[data-testid="stMetricValue"] {
            color: #173B4F;
        }
        .info-card {
            background: #FFFFFF;
            border: 1px solid #DCEAF3;
            border-radius: 18px;
            padding: 16px 18px;
            margin-bottom: 12px;
            box-shadow: 0 4px 14px rgba(33, 71, 97, 0.06);
        }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# CREDENCIALES DE INFLUXDB (Manejo seguro de errores)
# =========================================================
try:
    url = st.secrets["INFLUXDB_URL"]
    token = st.secrets["INFLUXDB_TOKEN"]
    org = st.secrets["INFLUXDB_ORG"]
    bucket = st.secrets["INFLUXDB_BUCKET"]
except Exception:
    st.error("⚠️ Faltan configurar los secretos (`INFLUXDB_URL`, etc.) en Streamlit Secrets o en el archivo `.streamlit/secrets.toml`.")
    st.stop()

# =========================================================
# TÍTULO
# =========================================================
st.title("🌤️ Mi clima IoT")
st.markdown(
    """
    <div class="info-card">
        <b>¿Qué estamos viendo?</b><br>
        Este tablero muestra la <b>temperatura</b> y la <b>humedad</b> que registra el sensor.
        Los colores y los íconos ayudan a entender rápidamente si el ambiente está más frío, más caliente, más seco o más húmedo.
    </div>
    """,
    unsafe_allow_html=True
)

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("⚙️ Configuración")

range_options = {
    "Última hora": "-1h",
    "Últimas 6 horas": "-6h",
    "Últimas 12 horas": "-12h",
    "Últimas 24 horas": "-24h",
    "Últimos 7 días": "-7d"
}

range_label = st.sidebar.selectbox(
    "🕒 ¿Cuánto tiempo quieres ver?",
    list(range_options.keys()),
    index=3
)
time_range = range_options[range_label]

refresh = st.sidebar.slider(
    "🔄 Actualizar cada...",
    min_value=0,
    max_value=60,
    value=10,
    step=5,
    help="Pon 0 para desactivar la actualización automática."
)

st.sidebar.caption("Los rangos de color son una guía visual.")

# =========================================================
# AUTO REFRESH
# =========================================================
if refresh > 0:
    st_autorefresh(interval=refresh * 1000, key="iot_refresh")

# =========================================================
# CARGAR DATOS DESDE INFLUXDB
# =========================================================
@st.cache_data(ttl=10)
def load_data(time_range):
    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        query_api = client.query_api()
        query = f'''
        from(bucket: "{bucket}")
          |> range(start: {time_range})
          |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "humidity")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time", "temperature", "humidity"])
        '''
        result = query_api.query_data_frame(query)

        if isinstance(result, list):
            frames = [frame for frame in result if not frame.empty]
            if not frames:
                return pd.DataFrame()
            df = pd.concat(frames, ignore_index=True)
        else:
            df = result.copy()

        if df.empty:
            return df

        df["_time"] = pd.to_datetime(df["_time"], utc=True).dt.tz_convert("America/Bogota")
        df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
        df["humidity"] = pd.to_numeric(df["humidity"], errors="coerce")

        df = (
            df.dropna(subset=["_time"])
            .sort_values("_time")
            .drop_duplicates(subset=["_time"])
        )
        return df
    finally:
        client.close()

# =========================================================
# FUNCIONES DE ESTADO Y MEDIDORES
# =========================================================
def temperature_status(value):
    if value < 18:
        return ("🥶 Frío", "Hace fresco.")
    elif value <= 26:
        return ("😊 Agradable", "La temperatura está en una zona cómoda.")
    else:
        return ("🥵 Caliente", "Hace bastante calor.")

def humidity_status(value):
    if value < 30:
        return ("🏜️ Seco", "El aire tiene poca humedad.")
    elif value <= 60:
        return ("💧 Bien", "La humedad está en un rango moderado.")
    else:
        return ("🌧️ Húmedo", "El aire tiene bastante humedad.")

def temperature_gauge(value):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": " °C", "font": {"size": 42}},
        title={"text": "🌡️ Temperatura ahora"},
        gauge={
            "axis": {"range": [0, 50], "tickwidth": 1},
            "bar": {"color": "#FF8A65"},
            "steps": [
                {"range": [0, 18], "color": "#B3E5FC"},
                {"range": [18, 26], "color": "#C8E6C9"},
                {"range": [26, 50], "color": "#FFCCBC"}
            ],
            "threshold": {"line": {"color": "#37474F", "width": 4}, "thickness": 0.8, "value": value}
        }
    ))
    fig.update_layout(height=320, margin=dict(l=30, r=30, t=70, b=20), paper_bgcolor="rgba(0,0,0,0)", font={"color": "#214761"})
    return fig

def humidity_gauge(value):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": " %", "font": {"size": 42}},
        title={"text": "💧 Humedad ahora"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": "#42A5F5"},
            "steps": [
                {"range": [0, 30], "color": "#FFE0B2"},
                {"range": [30, 60], "color": "#C8E6C9"},
                {"range": [60, 100], "color": "#BBDEFB"}
            ],
            "threshold": {"line": {"color": "#37474F", "width": 4}, "thickness": 0.8, "value": value}
        }
    ))
    fig.update_layout(height=320, margin=dict(l=30, r=30, t=70, b=20), paper_bgcolor="rgba(0,0,0,0)", font={"color": "#214761"})
    return fig

# =========================================================
# PROCESAMIENTO Y RENDERIZADO
# =========================================================
df = load_data(time_range)

if df.empty:
    st.warning("😕 No hay datos disponibles en este rango de tiempo.")
    st.stop()

latest = df.dropna(subset=["temperature", "humidity"]).tail(1)

if latest.empty:
    st.warning("😕 Hay datos, pero faltan lecturas válidas de temperatura o humedad.")
    st.stop()

temp_now = float(latest["temperature"].iloc[0])
hum_now = float(latest["humidity"].iloc[0])

temp_status, temp_text = temperature_status(temp_now)
hum_status, hum_text = humidity_status(hum_now)

# Métricas
st.subheader("👀 ¿Cómo está el ambiente ahora?")
col1, col2, col3, col4 = st.columns(4)
col1.metric("🌡️ Temperatura", f"{temp_now:.1f} °C")
col2.metric("💧 Humedad", f"{hum_now:.1f} %")
col3.metric("📊 Temp. promedio", f"{df['temperature'].mean():.1f} °C")
col4.metric("📊 Humedad promedio", f"{df['humidity'].mean():.1f} %")

# Tarjetas de estado
status_col1, status_col2 = st.columns(2)
with status_col1:
    st.markdown(f'<div class="info-card"><b>{temp_status}</b><br>{temp_text}</div>', unsafe_allow_html=True)
with status_col2:
    st.markdown(f'<div class="info-card"><b>{hum_status}</b><br>{hum_text}</div>', unsafe_allow_html=True)

# Medidores
g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(temperature_gauge(temp_now), use_container_width=True)
with g2:
    st.plotly_chart(humidity_gauge(hum_now), use_container_width=True)

st.caption("🟦 azul = más frío o seco · 🟩 verde = zona media · 🟧 naranja = más caliente o húmedo")

# Gráficas principales
st.subheader("📈 ¿Cómo han cambiado los datos?")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    temp_fig = px.line(df, x="_time", y="temperature", markers=True, labels={"_time": "Hora", "temperature": "Temperatura (°C)"}, title="🌡️ Temperatura con el tiempo")
    temp_fig.update_traces(line=dict(width=4, color="#FF7043"), marker=dict(size=7, color="#FF7043"))
    temp_fig.update_layout(height=390, hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", showlegend=False)
    temp_fig.update_yaxes(showgrid=True, gridcolor="#E6EEF3")
    temp_fig.update_xaxes(showgrid=False)
    st.plotly_chart(temp_fig, use_container_width=True)

with chart_col2:
    hum_fig = px.line(df, x="_time", y="humidity", markers=True, labels={"_time": "Hora", "humidity": "Humedad (%)"}, title="💧 Humedad con el tiempo")
    hum_fig.update_traces(line=dict(width=4, color="#42A5F5"), marker=dict(size=7, color="#42A5F5"))
    hum_fig.update_layout(height=390, hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", showlegend=False)
    hum_fig.update_yaxes(range=[0, 100], showgrid=True, gridcolor="#E6EEF3")
    hum_fig.update_xaxes(showgrid=False)
    st.plotly_chart(hum_fig, use_container_width=True)

# Tendencia suavizada
st.subheader("🧩 Tendencia más fácil de ver")
st.write("Aquí juntamos las lecturas en grupos de **10 minutos** para ver la tendencia general.")

df_resampled = df.set_index("_time")[["temperature", "humidity"]].resample("10min").mean().dropna(how="all")
smooth_col1, smooth_col2 = st.columns(2)

with smooth_col1:
    fig_temp_smooth = px.area(df_resampled, x=df_resampled.index, y="temperature", markers=True, title="🌡️ Temperatura promedio (10 min)")
    fig_temp_smooth.update_traces(line=dict(width=4, color="#FF8A65"), fillcolor="rgba(255, 138, 101, 0.20)")
    fig_temp_smooth.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", showlegend=False)
    st.plotly_chart(fig_temp_smooth, use_container_width=True)

with smooth_col2:
    fig_hum_smooth = px.area(df_resampled, x=df_resampled.index, y="humidity", markers=True, title="💧 Humedad promedio (10 min)")
    fig_hum_smooth.update_traces(line=dict(width=4, color="#64B5F6"), fillcolor="rgba(100, 181, 246, 0.20)")
    fig_hum_smooth.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", showlegend=False)
    fig_hum_smooth.update_yaxes(range=[0, 100])
    st.plotly_chart(fig_hum_smooth, use_container_width=True)

# Expanders
with st.expander("🧠 ¿Cómo leo estas gráficas?"):
    st.markdown("""
        - **Si la línea sube**, el valor aumenta.
        - **Si la línea baja**, el valor disminuye.
        - 🌡️ Temperatura en °C / 💧 Humedad en %.
    """)

with st.expander("📋 Ver datos crudos"):
    raw = df[["_time", "temperature", "humidity"]].copy()
    raw.columns = ["Hora", "Temperatura (°C)", "Humedad (%)"]
    st.dataframe(raw.tail(50), use_container_width=True, hide_index=True)
