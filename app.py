import streamlit as st
from streamlit_autorefresh import st_autorefresh
from influxdb_client import InfluxDBClient
import pandas as pd
import plotly.graph_objects as go


# =========================================================
# CONFIGURACIÓN DE INFLUXDB
# =========================================================

url = "https://us-east-1-1.aws.cloud2.influxdata.com"
token = "5FESPQw5t4qA4GgZmyeZ9mu7u1sbtauo4Hh8tjRi1E8sdrIgzXAX5ESk4n5MmcpAjJWEGgEKklFX0LNasnUmng=="
org = "miguelcmo"
bucket = "iot_telemetry_data"


# =========================================================
# CONFIGURACIÓN DE STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Monitoreo Ambiental IoT",
    page_icon="🌱",
    layout="wide"
)


# =========================================================
# ESTILO VISUAL
# =========================================================

st.markdown("""
<style>

/* ---------------------------------------------------------
   FONDO GENERAL
--------------------------------------------------------- */

.stApp {
    background-color: #F7FAFC;
}


/* ---------------------------------------------------------
   TEXTO GENERAL
--------------------------------------------------------- */

.stApp,
.stApp p,
.stApp span,
.stApp label {
    color: #2D3748;
}


/* ---------------------------------------------------------
   ENCABEZADOS
--------------------------------------------------------- */

h1, h2, h3 {
    color: #234E52 !important;
    font-weight: 700;
}


/* ---------------------------------------------------------
   SIDEBAR
--------------------------------------------------------- */

[data-testid="stSidebar"] {
    background-color: #EDF6F5;
    border-right: 1px solid #D8E7E5;
}

[data-testid="stSidebar"] * {
    color: #2D3748 !important;
}


/* ---------------------------------------------------------
   MÉTRICAS
--------------------------------------------------------- */

[data-testid="stMetric"] {

    background-color: #FFFFFF;

    border: 1px solid #E2E8F0;

    border-radius: 16px;

    padding: 18px;

    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.04);
}


[data-testid="stMetricLabel"] p {

    color: #5F6C7B !important;

    font-size: 16px !important;

    font-weight: 600;
}


[data-testid="stMetricValue"] {

    color: #234E52 !important;

    font-weight: 700;
}


/* ---------------------------------------------------------
   SELECTBOX Y SLIDER
--------------------------------------------------------- */

[data-baseweb="select"] > div {

    background-color: white !important;

    color: #2D3748 !important;
}


[data-testid="stSlider"] * {

    color: #2D3748 !important;
}


/* ---------------------------------------------------------
   EXPANDER
--------------------------------------------------------- */

[data-testid="stExpander"] {

    background-color: #FFFFFF;

    border-radius: 12px;

    border: 1px solid #E2E8F0;
}


/* ---------------------------------------------------------
   TARJETAS EXPLICATIVAS
--------------------------------------------------------- */

.info-card {

    background-color: #FFFFFF;

    border-radius: 15px;

    border: 1px solid #E2E8F0;

    padding: 18px;

    margin-bottom: 12px;

    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.03);

    color: #2D3748 !important;
}


/* ---------------------------------------------------------
   LÍNEAS DIVISORIAS
--------------------------------------------------------- */

hr {

    border-color: #DDE8EA;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# TÍTULO
# =========================================================

st.title("🌱 Monitoreo Ambiental IoT")

st.markdown("""
<div class="info-card">

<b>¿Qué muestra este tablero?</b><br><br>

Aquí puedes ver de manera sencilla la
<b>temperatura 🌡️</b> y la
<b>humedad 💧</b> registradas por el sensor.

Las gráficas permiten observar cómo cambian
estos valores con el paso del tiempo.

</div>
""", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Configuración")


time_options = {

    "Última hora": "-1h",

    "Últimas 6 horas": "-6h",

    "Últimas 12 horas": "-12h",

    "Últimas 24 horas": "-24h",

    "Últimos 7 días": "-7d"

}


selected_time = st.sidebar.selectbox(

    "🕒 ¿Cuánto tiempo quieres ver?",

    list(time_options.keys()),

    index=3
)


time_range = time_options[selected_time]


refresh = st.sidebar.slider(

    "🔄 Actualizar cada",

    min_value=0,

    max_value=60,

    value=10,

    step=5,

    help="Selecciona 0 para desactivar la actualización automática."
)


# =========================================================
# AUTO REFRESH
# =========================================================

if refresh > 0:

    st_autorefresh(

        interval=refresh * 1000,

        key="iot_refresh"
    )


# =========================================================
# CARGAR DATOS
# =========================================================

@st.cache_data(ttl=10)
def load_data(time_range):

    client = InfluxDBClient(

        url=url,

        token=token,

        org=org
    )


    query_api = client.query_api()


    query = f'''

    from(bucket: "{bucket}")

      |> range(start: {time_range})

      |> filter(
          fn: (r) =>
          r["_field"] == "temperature"
          or
          r["_field"] == "humidity"
      )

      |> pivot(
          rowKey: ["_time"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )

      |> keep(
          columns: [
              "_time",
              "temperature",
              "humidity"
          ]
      )

    '''


    result = query_api.query_data_frame(query)


    client.close()


    if isinstance(result, list):

        frames = [

            frame

            for frame in result

            if not frame.empty
        ]


        if len(frames) == 0:

            return pd.DataFrame()


        df = pd.concat(

            frames,

            ignore_index=True
        )


    else:

        df = result


    if df.empty:

        return df


    # Convertir datos
    df["_time"] = pd.to_datetime(

        df["_time"]
    )


    df["temperature"] = pd.to_numeric(

        df["temperature"],

        errors="coerce"
    )


    df["humidity"] = pd.to_numeric(

        df["humidity"],

        errors="coerce"
    )


    # Ordenar
    df = df.sort_values("_time")


    return df


# =========================================================
# DATOS
# =========================================================

df = load_data(time_range)


# =========================================================
# SI NO HAY DATOS
# =========================================================

if df.empty:

    st.warning(

        "⚠️ No hay datos disponibles en este rango de tiempo."
    )

    st.stop()


# =========================================================
# VALORES ACTUALES
# =========================================================

temp_actual = df["temperature"].dropna().iloc[-1]

hum_actual = df["humidity"].dropna().iloc[-1]


temp_promedio = df["temperature"].mean()

hum_promedio = df["humidity"].mean()


# =========================================================
# MÉTRICAS
# =========================================================

st.subheader("👀 Estado actual")


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(

        "🌡️ Temperatura actual",

        f"{temp_actual:.1f} °C"
    )


with col2:

    st.metric(

        "💧 Humedad actual",

        f"{hum_actual:.1f} %"
    )


with col3:

    st.metric(

        "🌡️ Temperatura promedio",

        f"{temp_promedio:.1f} °C"
    )


with col4:

    st.metric(

        "💧 Humedad promedio",

        f"{hum_promedio:.1f} %"
    )


st.markdown("---")


# =========================================================
# INDICADORES VISUALES
# =========================================================

st.subheader("🎯 ¿Cómo está el ambiente?")


gauge1, gauge2 = st.columns(2)


# ---------------------------------------------------------
# GAUGE TEMPERATURA
# ---------------------------------------------------------

with gauge1:

    temp_gauge = go.Figure(

        go.Indicator(

            mode="gauge+number",

            value=temp_actual,

            number={

                "suffix": " °C",

                "font": {

                    "size": 42,

                    "color": "#2D3748"
                }
            },

            title={

                "text": "🌡️ Temperatura",

                "font": {

                    "color": "#2D3748",

                    "size": 21
                }
            },

            gauge={

                "axis": {

                    "range": [0, 50],

                    "tickcolor": "#4A5568",

                    "tickfont": {

                        "color": "#4A5568"
                    }
                },

                "bar": {

                    "color": "#FF8B8B"
                },

                "steps": [

                    {

                        "range": [0, 18],

                        "color": "#D6EEFF"
                    },

                    {

                        "range": [18, 26],

                        "color": "#D8F3DC"
                    },

                    {

                        "range": [26, 50],

                        "color": "#FFD6D6"
                    }
                ]
            }
        )
    )


    temp_gauge.update_layout(

        height=300,

        paper_bgcolor="#FFFFFF",

        font=dict(

            color="#2D3748"
        ),

        margin=dict(

            l=30,

            r=30,

            t=60,

            b=20
        )
    )


    st.plotly_chart(

        temp_gauge,

        use_container_width=True
    )


# ---------------------------------------------------------
# GAUGE HUMEDAD
# ---------------------------------------------------------

with gauge2:

    hum_gauge = go.Figure(

        go.Indicator(

            mode="gauge+number",

            value=hum_actual,

            number={

                "suffix": " %",

                "font": {

                    "size": 42,

                    "color": "#2D3748"
                }
            },

            title={

                "text": "💧 Humedad",

                "font": {

                    "color": "#2D3748",

                    "size": 21
                }
            },

            gauge={

                "axis": {

                    "range": [0, 100],

                    "tickcolor": "#4A5568",

                    "tickfont": {

                        "color": "#4A5568"
                    }
                },

                "bar": {

                    "color": "#73C2FB"
                },

                "steps": [

                    {

                        "range": [0, 30],

                        "color": "#FFE5B4"
                    },

                    {

                        "range": [30, 60],

                        "color": "#D8F3DC"
                    },

                    {

                        "range": [60, 100],

                        "color": "#D6EEFF"
                    }
                ]
            }
        )
    )


    hum_gauge.update_layout(

        height=300,

        paper_bgcolor="#FFFFFF",

        font=dict(

            color="#2D3748"
        ),

        margin=dict(

            l=30,

            r=30,

            t=60,

            b=20
        )
    )


    st.plotly_chart(

        hum_gauge,

        use_container_width=True
    )


st.caption(

    "🟦 Azul = valores bajos · "

    "🟩 Verde = valores intermedios · "

    "🟥 Rosado = valores altos"
)


st.markdown("---")


# =========================================================
# GRÁFICAS PRINCIPALES
# =========================================================

st.subheader("📈 ¿Cómo cambian los datos con el tiempo?")


st.write(

    "Si la línea sube, el valor está aumentando. "

    "Si la línea baja, está disminuyendo."
)


graf1, graf2 = st.columns(2)


# ---------------------------------------------------------
# TEMPERATURA
# ---------------------------------------------------------

with graf1:

    fig_temp = go.Figure()


    fig_temp.add_trace(

        go.Scatter(

            x=df["_time"],

            y=df["temperature"],

            mode="lines+markers",

            name="Temperatura",

            line=dict(

                color="#FF8B8B",

                width=4
            ),

            marker=dict(

                color="#FF8B8B",

                size=7
            )
        )
    )


    fig_temp.update_layout(

        title="🌡️ Temperatura",

        xaxis_title="Hora",

        yaxis_title="Grados Celsius (°C)",

        template="plotly_white",

        paper_bgcolor="#FFFFFF",

        plot_bgcolor="#FFFFFF",

        font=dict(

            color="#2D3748",

            size=14
        ),

        title_font=dict(

            color="#2D3748",

            size=20
        ),

        xaxis=dict(

            gridcolor="#E2E8F0",

            tickfont=dict(

                color="#4A5568"
            ),

            title_font=dict(

                color="#4A5568"
            )
        ),

        yaxis=dict(

            gridcolor="#E2E8F0",

            tickfont=dict(

                color="#4A5568"
            ),

            title_font=dict(

                color="#4A5568"
            )
        ),

        hoverlabel=dict(

            bgcolor="#FFFFFF",

            font_color="#2D3748"
        ),

        showlegend=False,

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20
        )
    )


    st.plotly_chart(

        fig_temp,

        use_container_width=True
    )


# ---------------------------------------------------------
# HUMEDAD
# ---------------------------------------------------------

with graf2:

    fig_hum = go.Figure()


    fig_hum.add_trace(

        go.Scatter(

            x=df["_time"],

            y=df["humidity"],

            mode="lines+markers",

            name="Humedad",

            line=dict(

                color="#73C2FB",

                width=4
            ),

            marker=dict(

                color="#73C2FB",

                size=7
            )
        )
    )


    fig_hum.update_layout(

        title="💧 Humedad",

        xaxis_title="Hora",

        yaxis_title="Humedad (%)",

        template="plotly_white",

        paper_bgcolor="#FFFFFF",

        plot_bgcolor="#FFFFFF",

        font=dict(

            color="#2D3748",

            size=14
        ),

        title_font=dict(

            color="#2D3748",

            size=20
        ),

        xaxis=dict(

            gridcolor="#E2E8F0",

            tickfont=dict(

                color="#4A5568"
            ),

            title_font=dict(

                color="#4A5568"
            )
        ),

        yaxis=dict(

            range=[0, 100],

            gridcolor="#E2E8F0",

            tickfont=dict(

                color="#4A5568"
            ),

            title_font=dict(

                color="#4A5568"
            )
        ),

        hoverlabel=dict(

            bgcolor="#FFFFFF",

            font_color="#2D3748"
        ),

        showlegend=False,

        margin=dict(

            l=20,

            r=20,

            t=60,

            b=20
        )
    )


    st.plotly_chart(

        fig_hum,

        use_container_width=True
    )


# =========================================================
# PROMEDIO CADA 10 MINUTOS
# =========================================================

st.subheader(

    "⏱️ Tendencia general"
)


st.write(

    "Aquí agrupamos las mediciones cada 10 minutos "

    "para que los cambios sean más fáciles de observar."
)


df_resampled = (

    df

    .set_index("_time")[

        ["temperature", "humidity"]

    ]

    .resample("10min")

    .mean()

    .dropna()
)


res1, res2 = st.columns(2)


# ---------------------------------------------------------
# TEMPERATURA PROMEDIO
# ---------------------------------------------------------

with res1:

    fig_temp_avg = go.Figure()


    fig_temp_avg.add_trace(

        go.Scatter(

            x=df_resampled.index,

            y=df_resampled["temperature"],

            mode="lines+markers",

            line=dict(

                color="#E27396",

                width=4
            ),

            marker=dict(

                color="#E27396",

                size=7
            ),

            fill="tozeroy",

            fillcolor="rgba(226,115,150,0.12)"
        )
    )


    fig_temp_avg.update_layout(

        title="🌡️ Promedio de temperatura",

        xaxis_title="Hora",

        yaxis_title="°C",

        template="plotly_white",

        paper_bgcolor="#FFFFFF",

        plot_bgcolor="#FFFFFF",

        font=dict(

            color="#2D3748"
        ),

        xaxis=dict(

            gridcolor="#E2E8F0"
        ),

        yaxis=dict(

            gridcolor="#E2E8F0"
        ),

        showlegend=False
    )


    st.plotly_chart(

        fig_temp_avg,

        use_container_width=True
    )


# ---------------------------------------------------------
# HUMEDAD PROMEDIO
# ---------------------------------------------------------

with res2:

    fig_hum_avg = go.Figure()


    fig_hum_avg.add_trace(

        go.Scatter(

            x=df_resampled.index,

            y=df_resampled["humidity"],

            mode="lines+markers",

            line=dict(

                color="#84A98C",

                width=4
            ),

            marker=dict(

                color="#84A98C",

                size=7
            ),

            fill="tozeroy",

            fillcolor="rgba(132,169,140,0.15)"
        )
    )


    fig_hum_avg.update_layout(

        title="💧 Promedio de humedad",

        xaxis_title="Hora",

        yaxis_title="%",

        template="plotly_white",

        paper_bgcolor="#FFFFFF",

        plot_bgcolor="#FFFFFF",

        font=dict(

            color="#2D3748"
        ),

        xaxis=dict(

            gridcolor="#E2E8F0"
        ),

        yaxis=dict(

            range=[0, 100],

            gridcolor="#E2E8F0"
        ),

        showlegend=False
    )


    st.plotly_chart(

        fig_hum_avg,

        use_container_width=True
    )


# =========================================================
# EXPLICACIÓN FÁCIL
# =========================================================

with st.expander(

    "🧠 ¿Cómo entender las gráficas?"
):

    st.markdown("""

### 🌡️ Temperatura

La temperatura indica qué tan frío o caliente está el ambiente.

- Una línea que **sube** significa que está haciendo más calor.
- Una línea que **baja** significa que está haciendo más frío.


### 💧 Humedad

La humedad indica cuánta agua hay en el aire.

- Un porcentaje alto significa que el aire está más húmedo.
- Un porcentaje bajo significa que el aire está más seco.


### ⏱️ Promedios

Las gráficas de promedio eliminan pequeños cambios y permiten
ver más fácilmente la tendencia general.

""")


# =========================================================
# DATOS CRUDOS
# =========================================================

with st.expander(

    "📋 Ver registros detallados"
):

    tabla = df[
        [
            "_time",
            "temperature",
            "humidity"
        ]
    ].copy()


    tabla.columns = [

        "Hora",

        "Temperatura (°C)",

        "Humedad (%)"
    ]


    st.dataframe(

        tabla.tail(50),

        use_container_width=True,

        hide_index=True
    )
