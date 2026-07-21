# Preparación Plena Studio

## Entrega 4 — Primer generador del MASTER

Esta versión conecta el artículo estructurado con OpenAI y crea un primer
borrador completo del MASTER siguiendo la metodología PPA.

### Funciones nuevas

- Generación pregunta por pregunta.
- Conservación literal de cada pregunta.
- Respuestas estructuradas en `trabajo/master.json`.
- Campos separados para respuesta, explicación bíblica, comparación,
  aplicación y nota de imagen.
- Advertencia de costos antes de llamar a la API.
- Clave API guardada localmente en `.env`, excluida de Git.
- Modelo configurable.
- Exportación de `master.json` a `salidas/MASTER.docx`.
- Procesamiento en segundo plano para mantener activa la interfaz.

### Flujo

```text
PDF
  ↓
trabajo/articulo.json
  ↓
OpenAI + metodología PPA
  ↓
trabajo/master.json
  ↓
salidas/MASTER.docx
```

### Configuración inicial

1. Abre **Configuración**.
2. Escribe tu clave de OpenAI.
3. Deja `gpt-5-mini` o escribe otro modelo disponible para tu cuenta.
4. Guarda la configuración.
5. Abre un proyecto, analiza el artículo y pulsa **Generar MASTER**.

La aplicación usa la API oficial de OpenAI. El uso de la API puede generar
cargos independientes de una suscripción de ChatGPT.

### Ejecutar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Pruebas

```bash
python -m unittest discover -s tests
```

Esta entrega no transcribe todavía el MP3. El audio se conserva como fuente
del proyecto, pero no se envía ni se interpreta durante la generación.
