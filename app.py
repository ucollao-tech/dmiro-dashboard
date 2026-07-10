import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.stats import norm
from datetime import datetime, timedelta
import json, io, base64

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="D'MIRO — Planificación de Producción",
    page_icon="🧀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS personalizado
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title {font-size:2rem; font-weight:700; color:#1a5276; margin-bottom:0;}
    .sub-title  {font-size:1rem; color:#5d6d7e; margin-top:0;}
    .metric-card {
        background:#f4f6f7; border-left:4px solid #2980b9;
        padding:12px 16px; border-radius:6px; margin-bottom:8px;
    }
    .metric-label {font-size:0.78rem; color:#5d6d7e; font-weight:600; text-transform:uppercase;}
    .metric-value {font-size:1.6rem; font-weight:700; color:#1a5276;}
    .metric-sub   {font-size:0.8rem; color:#7f8c8d;}
    .alert-box  {
        background:#fef9e7; border:1px solid #f39c12;
        padding:10px 14px; border-radius:6px; font-size:0.85rem;
    }
    .section-header {
        background:#2980b9; color:white;
        padding:6px 14px; border-radius:4px;
        font-weight:600; font-size:0.95rem; margin:12px 0 8px;
    }
    footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DATOS ESTADÍSTICOS PRECALCULADOS (desde Ventas_DMIRO.xlsx)
# Actualizados al correr el notebook de Colab; también se recalculan aquí
# ─────────────────────────────────────────────────────────────────────────────
STATS_BASE = {
    "Yogurt Frutado de Fresa":  {"mu": 18.65, "sigma": 6.44,  "color": "#2980b9", "emoji": "🥤"},
    "Queso Paria":               {"mu": 10.11, "sigma": 3.98,  "color": "#27ae60", "emoji": "🧀"},
    "Leche Fresca Entera":       {"mu": 14.44, "sigma": 5.34,  "color": "#8e44ad", "emoji": "🥛"},
    "Manjar Blanco Artesanal":   {"mu":  7.02, "sigma": 3.12,  "color": "#e67e22", "emoji": "🍯"},
    "Mantequilla Artesanal":     {"mu":  6.29, "sigma": 2.85,  "color": "#c0392b", "emoji": "🧈"},
}

VENTAS_DIA_SEMANA = {
    "Lunes":    12.3, "Martes":  11.5, "Miércoles": 11.4,
    "Jueves":   12.0, "Viernes": 15.2, "Sábado":    11.3, "Domingo": 5.3,
}
VENTAS_MES = {
    "Ene": 10.78, "Feb": 11.19, "Mar": 11.05,
    "Abr": 11.40, "May": 11.37, "Jun": 12.19,
}
TOTAL_PRODUCTO = {
    "Yogurt Frutado de Fresa":  3283,
    "Queso Paria":              1780,
    "Leche Fresca Entera":      2541,
    "Manjar Blanco Artesanal":  1236,
    "Mantequilla Artesanal":    1107,
}
FERIADOS_PERU_2026 = [
    "2026-01-01","2026-04-02","2026-04-03","2026-05-01",
    "2026-06-29","2026-07-28","2026-07-29","2026-08-30",
    "2026-10-08","2026-11-01","2026-12-08","2026-12-25",
]

# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────
def calc_stats(mu_dia, sigma_dia, horizonte, nivel_svc):
    """Calcula estadísticos del modelo probabilístico Normal."""
    mu_h    = mu_dia * horizonte
    sigma_h = sigma_dia * np.sqrt(horizonte)
    z       = norm.ppf(nivel_svc)
    ic_low  = norm.ppf(0.025, mu_h, sigma_h)
    ic_high = norm.ppf(0.975, mu_h, sigma_h)
    stock_seg   = z * sigma_h
    prod_rec    = mu_h + stock_seg
    return {
        "mu_h": mu_h, "sigma_h": sigma_h, "z": z,
        "ic_low": ic_low, "ic_high": ic_high,
        "stock_seg": stock_seg, "prod_rec": prod_rec,
    }

def factor_dia(nombre_dia):
    base = np.mean(list(VENTAS_DIA_SEMANA.values()))
    return VENTAS_DIA_SEMANA.get(nombre_dia, base) / base

def factor_feriado(fecha_str):
    return 0.65 if fecha_str in FERIADOS_PERU_2026 else 1.0

def ajustar_mu(mu_base, dia_semana, es_feriado, factor_promo):
    fd = factor_dia(dia_semana)
    ff = factor_feriado(es_feriado)
    return mu_base * fd * ff * factor_promo

def grafico_distribucion(mu, sigma, prod_rec, ic_low, ic_high, titulo, color):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = np.linspace(mu - 4*sigma, mu + 4*sigma, 400)
    y = norm.pdf(x, mu, sigma)

    ax.plot(x, y, color=color, lw=2)
    ax.fill_between(x, y, where=(x >= ic_low) & (x <= ic_high),
                    color=color, alpha=0.18, label=f"IC 95%")
    ax.fill_between(x, y, where=(x >= prod_rec),
                    color="#e74c3c", alpha=0.22, label=f"Zona riesgo")
    ax.axvline(mu,       color=color,    lw=1.5, ls="--", label=f"μ = {mu:.1f}")
    ax.axvline(ic_low,   color="#7f8c8d",lw=1,   ls=":")
    ax.axvline(ic_high,  color="#7f8c8d",lw=1,   ls=":")
    ax.axvline(prod_rec, color="#e74c3c",lw=2,   ls="-", label=f"Prod. rec. = {prod_rec:.0f}")

    ax.set_title(titulo, fontsize=9, pad=6)
    ax.set_xlabel("Unidades", fontsize=8)
    ax.set_ylabel("Densidad", fontsize=8)
    ax.legend(fontsize=7, loc="upper right")
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig

def grafico_barras_dias():
    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    dias   = list(VENTAS_DIA_SEMANA.keys())
    vals   = list(VENTAS_DIA_SEMANA.values())
    colores = ["#2980b9" if v == max(vals) else "#aed6f1" for v in vals]
    bars = ax.bar(dias, vals, color=colores, edgecolor="white", linewidth=0.5)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
                f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax.set_title("Promedio de ventas por día de semana", fontsize=9)
    ax.set_ylabel("Unidades promedio", fontsize=8)
    ax.tick_params(labelsize=7.5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig

def grafico_meses():
    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    meses = list(VENTAS_MES.keys())
    vals  = list(VENTAS_MES.values())
    ax.plot(meses, vals, "o-", color="#27ae60", lw=2, markersize=6)
    ax.fill_between(meses, vals, min(vals)*0.97, alpha=0.12, color="#27ae60")
    for i, (m, v) in enumerate(zip(meses, vals)):
        ax.text(i, v+0.05, f"{v:.2f}", ha="center", va="bottom", fontsize=7.5)
    ax.set_title("Ventas promedio por mes (ene–jun 2026)", fontsize=9)
    ax.set_ylabel("Unidades promedio", fontsize=8)
    ax.tick_params(labelsize=7.5)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig

def grafico_torta():
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    labels = [k.replace(" ", "\n") for k in TOTAL_PRODUCTO]
    sizes  = list(TOTAL_PRODUCTO.values())
    colores = ["#2980b9","#27ae60","#8e44ad","#e67e22","#c0392b"]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, colors=colores,
        autopct="%1.1f%%", startangle=140,
        wedgeprops=dict(edgecolor="white", linewidth=1.5),
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8)
    ax.legend(wedges, [k[:18] for k in TOTAL_PRODUCTO],
              loc="lower center", bbox_to_anchor=(0.5, -0.18),
              fontsize=7, ncol=2)
    ax.set_title("Participación de ventas por producto\nene–jun 2026", fontsize=9)
    fig.tight_layout()
    return fig

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    
    st.markdown("## 🧀 D'MIRO")
    st.markdown("**Planificación de Producción**")
    st.markdown("---")
    st.markdown("### ⚙️ Parámetros del modelo")

    producto_sel = st.selectbox(
        "Producto",
        list(STATS_BASE.keys()),
        format_func=lambda x: f"{STATS_BASE[x]['emoji']} {x}"
    )
    horizonte = st.slider("Horizonte de planificación (días)", 7, 90, 30, step=7)
    nivel_svc = st.slider("Nivel de servicio", 0.80, 0.99, 0.95, step=0.01,
                          format="%.0f%%",
                          help="Probabilidad de no quedar sin stock")

    st.markdown("---")
    st.markdown("### 📅 Ajustes contextuales")
    dia_semana  = st.selectbox("Día base de despacho", list(VENTAS_DIA_SEMANA.keys()), index=4)
    es_feriado  = st.date_input("¿Fecha próxima clave?", value=datetime.today())
    factor_promo = st.slider("Factor promoción", 0.8, 1.5, 1.0, step=0.05,
                             help="1.0 = sin promoción; 1.2 = +20% por campaña")

    st.markdown("---")
    st.caption("CU07 · Gestionar Inventario\nAnálisis y Diseño de Sistemas — PUCP 2026-1")

# ─────────────────────────────────────────────────────────────────────────────
# ENCABEZADO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🧀 D\'MIRO — Dashboard de Planificación de Producción</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Modelo probabilístico de demanda · Análisis y Diseño de Sistemas PUCP · Grupo 6 · 2026-1</p>', unsafe_allow_html=True)
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
p     = STATS_BASE[producto_sel]
mu_aj = ajustar_mu(
    p["mu"], dia_semana,
    es_feriado.strftime("%Y-%m-%d"),
    factor_promo
)
s     = calc_stats(mu_aj, p["sigma"], horizonte, nivel_svc)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 1 — KPIs
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-header">📊 Estadísticos del Modelo Probabilístico — {producto_sel}</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
kpis = [
    (c1, "μ diaria ajustada",  f"{mu_aj:.1f} u",   f"Base: {p['mu']:.1f} u/día"),
    (c2, "σ diaria",           f"{p['sigma']:.2f}", "Desviación estándar"),
    (c3, f"μ ({horizonte}d)",  f"{s['mu_h']:.0f} u", f"Demanda esperada"),
    (c4, "IC 95%",             f"[{s['ic_low']:.0f}, {s['ic_high']:.0f}]", "Intervalo de confianza"),
    (c5, "Producción rec.",    f"{s['prod_rec']:.0f} u", f"NSv {nivel_svc*100:.0f}% · Stock seg. {s['stock_seg']:.0f}"),
]
for col, lbl, val, sub in kpis:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{lbl}</div>
            <div class="metric-value">{val}</div>
            <div class="metric-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 2 — Distribución + tabla de todos los productos
# ─────────────────────────────────────────────────────────────────────────────
col_dist, col_tabla = st.columns([1.3, 1])

with col_dist:
    st.markdown(f'<div class="section-header">📈 Distribución Normal de Demanda — {horizonte} días</div>', unsafe_allow_html=True)
    fig_dist = grafico_distribucion(
        s["mu_h"], s["sigma_h"], s["prod_rec"],
        s["ic_low"], s["ic_high"],
        f"{producto_sel}\nμ={s['mu_h']:.0f}  σ={s['sigma_h']:.1f}  IC95%=[{s['ic_low']:.0f},{s['ic_high']:.0f}]",
        p["color"]
    )
    st.pyplot(fig_dist)
    plt.close(fig_dist)

with col_tabla:
    st.markdown('<div class="section-header">📋 Plan de Producción — Todos los Productos</div>', unsafe_allow_html=True)
    filas = []
    for prod, dat in STATS_BASE.items():
        mu_a = ajustar_mu(dat["mu"], dia_semana, es_feriado.strftime("%Y-%m-%d"), factor_promo)
        st_d = calc_stats(mu_a, dat["sigma"], horizonte, nivel_svc)
        filas.append({
            "Producto":  f"{dat['emoji']} {prod[:22]}",
            "μ/día":     f"{mu_a:.1f}",
            "σ/día":     f"{dat['sigma']:.2f}",
            f"Dem. {horizonte}d": f"{st_d['mu_h']:.0f}",
            "Stock seg.":f"{st_d['stock_seg']:.0f}",
            "Prod. Rec.":f"{st_d['prod_rec']:.0f}",
        })
    df_tabla = pd.DataFrame(filas)
    st.dataframe(df_tabla, hide_index=True, height=230)

    # Resumen total
    total_prod = sum(
        calc_stats(
            ajustar_mu(d["mu"], dia_semana, es_feriado.strftime("%Y-%m-%d"), factor_promo),
            d["sigma"], horizonte, nivel_svc
        )["prod_rec"]
        for d in STATS_BASE.values()
    )
    st.markdown(f"""
    <div class="metric-card" style="border-left-color:#27ae60; margin-top:8px;">
        <div class="metric-label">PRODUCCIÓN TOTAL ({horizonte} días)</div>
        <div class="metric-value" style="color:#1a8a4a;">{total_prod:.0f} unidades</div>
        <div class="metric-sub">Todos los productos · NSv {nivel_svc*100:.0f}%</div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 3 — Variables explicativas
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">📅 Variables Explicativas de la Demanda</div>', unsafe_allow_html=True)

cv1, cv2, cv3 = st.columns(3)
with cv1:
    st.pyplot(grafico_barras_dias())
    plt.close()
with cv2:
    st.pyplot(grafico_meses())
    plt.close()
with cv3:
    st.pyplot(grafico_torta())
    plt.close()

# ─────────────────────────────────────────────────────────────────────────────
# FILA 4 — Distribuciones de los 5 productos
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">🔬 Distribuciones Probabilísticas — Todos los Productos</div>', unsafe_allow_html=True)

cols5 = st.columns(5)
for col, (prod, dat) in zip(cols5, STATS_BASE.items()):
    with col:
        mu_a = ajustar_mu(dat["mu"], dia_semana, es_feriado.strftime("%Y-%m-%d"), factor_promo)
        st_d = calc_stats(mu_a, dat["sigma"], horizonte, nivel_svc)
        fig_p = grafico_distribucion(
            st_d["mu_h"], st_d["sigma_h"], st_d["prod_rec"],
            st_d["ic_low"], st_d["ic_high"],
            f"{dat['emoji']} {prod[:18]}\nμ={st_d['mu_h']:.0f} σ={st_d['sigma_h']:.1f}",
            dat["color"]
        )
        st.pyplot(fig_p)
        plt.close(fig_p)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 5 — Feriados y alertas
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
ca, cb = st.columns([1, 2])

with ca:
    st.markdown('<div class="section-header">📅 Feriados Perú 2026</div>', unsafe_allow_html=True)
    nombres_feriados = {
        "2026-01-01": "Año Nuevo", "2026-04-02": "Viernes Santo",
        "2026-04-03": "Sábado Santo", "2026-05-01": "Día del Trabajo",
        "2026-06-29": "San Pedro y San Pablo", "2026-07-28": "Fiestas Patrias",
        "2026-07-29": "Fiestas Patrias", "2026-08-30": "Santa Rosa",
        "2026-10-08": "Batalla de Angamos", "2026-11-01": "Todos los Santos",
        "2026-12-08": "Inmaculada Concepción", "2026-12-25": "Navidad",
    }
    df_fer = pd.DataFrame([
        {"Fecha": k, "Feriado": v, "Impacto": "−35% demanda"}
        for k, v in nombres_feriados.items()
    ])
    st.dataframe(df_fer, hide_index=True, height=280)

with cb:
    st.markdown('<div class="section-header">📊 Pronóstico Diario — Próximos 30 días</div>', unsafe_allow_html=True)
    fechas_fut = [datetime.today() + timedelta(days=i) for i in range(30)]
    mu_diario  = []
    for f in fechas_fut:
        dia_n = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"][f.weekday()]
        mu_a  = ajustar_mu(p["mu"], dia_n, f.strftime("%Y-%m-%d"), factor_promo)
        mu_diario.append(mu_a)

    mu_arr  = np.array(mu_diario)
    sig_arr = np.full(30, p["sigma"])
    ic_lo   = mu_arr - 1.96 * sig_arr
    ic_hi   = mu_arr + 1.96 * sig_arr

    fig_ts, ax_ts = plt.subplots(figsize=(8, 3))
    dias_x = list(range(1, 31))
    ax_ts.plot(dias_x, mu_arr, "o-", color=p["color"], lw=1.8, ms=4, label="μ ajustada")
    ax_ts.fill_between(dias_x, ic_lo, ic_hi, alpha=0.18, color=p["color"], label="IC 95%")
    # Marcar feriados
    for i, f in enumerate(fechas_fut):
        if f.strftime("%Y-%m-%d") in FERIADOS_PERU_2026:
            ax_ts.axvline(i+1, color="#e74c3c", lw=1, ls=":", alpha=0.7)
    ax_ts.set_xlabel("Día", fontsize=8)
    ax_ts.set_ylabel("Unidades", fontsize=8)
    ax_ts.set_title(f"Pronóstico diario — {producto_sel}", fontsize=9)
    ax_ts.legend(fontsize=8)
    ax_ts.grid(alpha=0.25)
    fig_ts.tight_layout()
    st.pyplot(fig_ts)
    plt.close(fig_ts)

# ─────────────────────────────────────────────────────────────────────────────
# DESCARGA CSV
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
rows_exp = []
for prod, dat in STATS_BASE.items():
    mu_a = ajustar_mu(dat["mu"], dia_semana, es_feriado.strftime("%Y-%m-%d"), factor_promo)
    st_d = calc_stats(mu_a, dat["sigma"], horizonte, nivel_svc)
    rows_exp.append({
        "Producto": prod, "mu_dia": round(mu_a,2), "sigma_dia": round(dat["sigma"],2),
        f"mu_{horizonte}d": round(st_d["mu_h"],0),
        f"sigma_{horizonte}d": round(st_d["sigma_h"],1),
        "IC95_inferior": round(st_d["ic_low"],0), "IC95_superior": round(st_d["ic_high"],0),
        "Stock_seguridad": round(st_d["stock_seg"],0),
        "Produccion_recomendada": round(st_d["prod_rec"],0),
        "Nivel_servicio": f"{nivel_svc*100:.0f}%",
        "Horizonte_dias": horizonte,
    })
df_exp = pd.DataFrame(rows_exp)
csv = df_exp.to_csv(index=False).encode("utf-8")

col_dl1, col_dl2, _ = st.columns([1,1,3])
with col_dl1:
    st.download_button(
        "⬇️ Descargar plan (CSV)",
        data=csv, file_name="plan_produccion_dmiro.csv", mime="text/csv",
    )
with col_dl2:
    st.markdown(f"*{len(rows_exp)} productos · horizonte {horizonte} días*")

st.caption("D'MIRO · Análisis y Diseño de Sistemas · PUCP 2026-1 · Grupo 6 | Modelo: Normal(μ, σ) con IC 95%")
