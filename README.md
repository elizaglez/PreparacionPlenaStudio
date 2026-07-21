# Preparación Plena Studio

## Entrega 7 — Motor de contexto y trazabilidad

Esta versión mejora la calidad de cada respuesta y registra cómo fue generada.

### Funciones nuevas

- Motor de contexto por pregunta.
- Inclusión automática de:
  - título;
  - introducción;
  - subtítulo;
  - párrafos asociados;
  - referencias bíblicas;
  - fragmentos bíblicos disponibles;
  - pregunta anterior;
  - pregunta siguiente.
- El contexto vecino se usa solo para continuidad.
- Registro individual de cada generación y regeneración.
- Historial con:
  - fecha y hora;
  - modelo utilizado;
  - prompt;
  - contexto enviado;
  - salida recibida;
  - duración;
  - operación realizada.
- Historial guardado en:

```text
trabajo/historial_generacion/
```

### Flujo actualizado

```text
articulo.json + citas_extraidas.txt
              ↓
       Motor de contexto
              ↓
         Prompt final
              ↓
            OpenAI
              ↓
    master.json + historial
```

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
