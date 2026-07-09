# D'MIRO — Dashboard de Planificación de Producción

Sistema de pronóstico probabilístico de demanda para D'MIRO.  
CU07 · Gestionar Inventario · ADS PUCP 2026-1 · Grupo 6

## Cómo publicar la página web GRATIS (paso a paso)

### Paso 1 — Correr el notebook en Colab

1. Ve a [colab.research.google.com](https://colab.research.google.com)
2. Sube `dmiro_modelo_probabilistico_nn_v2.ipynb`
3. Ejecuta todas las celdas en orden
4. En la celda 12 descarga los archivos → guarda `resultados_dmiro.json`

### Paso 2 — Subir a GitHub

1. Ve a [github.com](https://github.com) y crea un repo nuevo llamado `dmiro-dashboard`
2. Sube estos 4 archivos al repositorio:
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `resultados_dmiro.json` (el que descargaste de Colab)

### Paso 3 — Publicar en Streamlit Cloud (GRATIS)

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Inicia sesión con tu cuenta de GitHub
3. Clic en **"New app"**
4. Selecciona:
   - Repository: `dmiro-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
5. Clic en **"Deploy!"**

En ~2 minutos tendrás una URL pública tipo:  
`https://dmiro-dashboard.streamlit.app`

## Estructura de archivos

```
dmiro_app/
├── app.py                              ← Dashboard Streamlit
├── requirements.txt                    ← Dependencias Python
├── README.md                           ← Este archivo
└── resultados_dmiro.json               ← Generado por Colab (opcional)
```

## Variables del modelo probabilístico

| Variable | Descripción |
|----------|-------------|
| μ (mu) | Media de demanda diaria por producto |
| σ (sigma) | Desviación estándar de la demanda |
| IC 95% | Intervalo [μ−1.96σ, μ+1.96σ] |
| Stock de seguridad | z·σ·√horizonte (z=1.645 para NSv=95%) |
| Producción recomendada | μ·horizonte + stock de seguridad |

## Variables explicativas incluidas

- Día de semana (lunes–domingo)
- Día del mes, semana del año, mes, trimestre
- Feriados peruanos 2026 (12 fechas)
- Ciclicidad: seno/coseno de semana y mes
- Rezagos: lag-1, lag-2, lag-3, lag-7, lag-14
- Media móvil 7 y 14 días
- Desviación estándar móvil 7 días
- Promociones (variable binaria)
