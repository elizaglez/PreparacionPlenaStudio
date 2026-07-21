# Preparación Plena Studio

## Entrega 3 — Article Parser

Esta versión añade el primer módulo inteligente específico del proyecto.

### Funciones nuevas

- Convierte el texto extraído del PDF en `trabajo/articulo.json`.
- Detecta título, preguntas, párrafos numerados y subtítulos.
- Asocia preguntas con sus párrafos.
- Normaliza referencias bíblicas abreviadas.
- Detecta párrafos sin asignar.
- Muestra advertencias cuando la estructura del PDF no es suficientemente clara.
- Mantiene el procesamiento en segundo plano para no congelar la interfaz.

### Archivos generados

```text
trabajo/
├── pdf_extraido.txt
├── citas_extraidas.txt
├── articulo.json
└── fuentes_resumen.json
```

### Ejecutar en Windows

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

El parser utiliza reglas conservadoras. Cuando no puede demostrar una asociación entre pregunta y párrafo, registra una advertencia en vez de inventarla.
