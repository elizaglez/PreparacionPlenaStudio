# Arquitectura de proveedores de IA

## 1. Situación actual

Preparación Plena y Algo Más utiliza actualmente OpenAI como proveedor de inteligencia artificial. Esta integración es la implementación activa y debe mantenerse sin cambios mientras se diseña y valida la evolución hacia múltiples proveedores.

La arquitectura descrita en este documento representa una dirección futura. No requiere reemplazar, adaptar ni interrumpir la implementación actual.

## 2. Objetivo futuro

El objetivo es incorporar una capa abstracta de proveedor de IA que separe los casos de uso de los servicios concretos utilizados para ejecutar cada tarea.

```text
Usuario
   ↓
Caso de uso
   ↓
AI Provider Interface
   ↓
Proveedor concreto
```

La interfaz común definirá las capacidades que necesita la aplicación, mientras cada proveedor será responsable de traducirlas a su propia API o entorno de ejecución.

Entre los proveedores posibles se encuentran:

- OpenAI;
- Qwen;
- modelos locales;
- otros servicios compatibles que se incorporen en el futuro.

Los casos de uso no deben depender de nombres de modelos, clientes HTTP, credenciales ni formatos particulares de un proveedor. Deben solicitar una capacidad y recibir una respuesta mediante un contrato estable.

## 3. Distribución recomendada de tareas

No todas las operaciones requieren el mismo nivel de razonamiento, costo o tiempo de respuesta. La selección del proveedor y del modelo debe corresponder a la complejidad de la tarea.

### Modelos rápidos

Son apropiados para operaciones frecuentes, estructuradas y verificables, como:

- clasificación de contenido;
- extracción de datos;
- detección de secciones;
- normalización de estructuras;
- tareas repetitivas.

Estas operaciones deben favorecer baja latencia, costo controlado y resultados consistentes.

### Modelos avanzados

Son apropiados para tareas que requieren mayor comprensión, redacción y criterio editorial, como:

- preparación de respuestas;
- explicación de textos y conceptos;
- aplicaciones prácticas;
- elaboración de guiones para HeyGen;
- desarrollo de estructuras narrativas y audiovisuales.

La distribución debe ser configurable. Una tarea no debe quedar vinculada permanentemente a un proveedor o modelo concreto.

## 4. Configuración futura

La configuración podrá asignar un proveedor diferente según la función de la aplicación. Por ejemplo:

```json
{
  "classification_provider": "...",
  "study_provider": "...",
  "script_provider": "..."
}
```

Una evolución posterior podría separar también el proveedor del modelo seleccionado:

```json
{
  "classification": {
    "provider": "...",
    "model": "..."
  },
  "study": {
    "provider": "...",
    "model": "..."
  },
  "script": {
    "provider": "...",
    "model": "..."
  }
}
```

Esta configuración es únicamente una referencia para el diseño futuro. No sustituye ni modifica la configuración actual.

## 5. Contrato conceptual

La interfaz de proveedor debe expresar las necesidades de la aplicación sin exponer detalles del servicio concreto. Conceptualmente podría ofrecer operaciones como:

```text
generate_text(request) → response
generate_structured(request, schema) → structured_response
```

Cada solicitud debería contener, como mínimo:

- instrucciones;
- contenido de entrada;
- propósito o tipo de tarea;
- formato de salida esperado;
- parámetros permitidos por la política de la aplicación.

Cada respuesta debería ofrecer una representación normalizada del contenido, metadatos básicos de ejecución y errores comprensibles para los casos de uso.

Los adaptadores concretos asumirían las diferencias entre OpenAI, Qwen y los modelos locales.

## 6. Principios de arquitectura

### Independencia de la lógica de negocio

Cambiar de proveedor no debe exigir modificaciones en la lógica de preparación, estudio, validación o producción audiovisual.

### Contratos estables

Los casos de uso deben depender de una interfaz común y de estructuras de entrada y salida normalizadas, no de respuestas específicas de una API.

### Pruebas independientes

Las pruebas de negocio deben utilizar proveedores simulados o dobles de prueba. No deben depender de conexión a internet, credenciales ni llamadas reales.

Cada adaptador concreto tendrá pruebas separadas para validar la transformación entre el contrato común y el formato del proveedor.

### Sustitución sin reescritura

Debe ser posible cambiar el proveedor asignado a una tarea mediante configuración e inyección de dependencias, sin reescribir módulos completos.

### Selección según la tarea

La plataforma podrá combinar proveedores y modelos: uno rápido para clasificación, otro más avanzado para material de estudio y otro especializado para guiones.

### Conservación de calidad y seguridad

Todos los proveedores deberán respetar las mismas reglas editoriales, formatos de salida, límites de fuentes y validaciones de calidad definidos por Preparación Plena y Algo Más.

## 7. Resultado esperado

La capa de proveedores permitirá que Preparación Plena y Algo Más evolucione sin quedar ligada a una sola plataforma de IA. OpenAI podrá continuar como proveedor activo, mientras la aplicación gana la capacidad futura de incorporar Qwen, modelos locales u otras alternativas con cambios limitados a sus adaptadores y a la configuración correspondiente.
