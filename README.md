# Preparación Plena Studio

## Entrega 2 — Motor de lectura de fuentes

Esta versión incluye:

- Interfaz de escritorio con navegación lateral.
- Creación y apertura de proyectos.
- Selección y copia de PDF, MP3 y citas bíblicas.
- Historial local y configuración.
- Metodología PPA persistente.
- Lectura real de PDF mediante PyMuPDF.
- Detección preliminar de preguntas y referencias bíblicas.
- Lectura de citas desde TXT, DOCX o PDF.
- Validación y registro del audio MP3, WAV o M4A.
- Procesamiento en segundo plano con barra de progreso.
- Generación de archivos de diagnóstico en `trabajo/`.

## Ejecutar en Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Resultado del procesamiento

Al pulsar **PROCESAR FUENTES**, se crean:

```text
trabajo/
├── pdf_extraido.txt
├── citas_extraidas.txt
└── fuentes_resumen.json
```

La transcripción del audio y la generación del MASTER se añadirán en las siguientes entregas.

## Importante

Los PDF escaneados que no tengan texto seleccionable todavía no pueden procesarse. La aplicación los detecta y muestra un aviso claro.
