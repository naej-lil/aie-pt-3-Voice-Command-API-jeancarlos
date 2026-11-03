# Instrucciones del proyecto: Voice Command API

Construye el backend de una lista de tareas controlada por voz. El frontend está proporcionado y no se debe modificar. Sigue la arquitectura y convenciones que ya existen en el repositorio.

## Configuración

- Usa el entorno virtual del proyecto e instala las dependencias necesarias para FastAPI, Uvicorn y el SDK Python de Groq. Actualiza la configuración de dependencias existente en `pyproject.toml` y el lockfile correspondiente si hace falta; no crees un sistema de dependencias paralelo.
- Lee la API key desde `GROQ_API_KEY` en `.env`; nunca la escribas en el código ni la incluyas en respuestas o logs.
- Mantén `.env` excluido por `.gitignore`. Si documentas variables necesarias, usa `.env.example` sin secretos.
- Configura CORS para permitir que el frontend incluido se comunique con la API, usando la configuración de orígenes existente.

## Punto de entrada

- Implementa `POST /instruction` para recibir JSON con `transcription` (texto no vacío) y consultar la API de Groq.
- Usa un modelo Groq disponible compatible con salida estructurada, como `llama3-8b-8192` o su sucesor disponible.
- El prompt del sistema debe pedir al modelo que devuelva únicamente un objeto JSON válido, sin markdown, explicaciones ni texto adicional, con esta estructura:

  ```json
  {
    "endpoint": "/tasks",
    "method": "POST",
    "params": { "title": "Comprar leche" }
  }
  ```

- La respuesta debe contener `endpoint`, `method` y `params`, con argumentos que coincidan con los esquemas de tareas. Parsea y valida la salida del modelo antes de devolverla.
- Todas las decisiones de intención y enrutamiento deben provenir del LLM. No implementes detección manual basada en palabras o frases de la transcripción.
- `POST /instruction` devuelve el descriptor de enrutamiento; no inventes una intención alternativa si Groq falla o devuelve una respuesta inválida. Devuelve un error HTTP apropiado sin filtrar secretos.

## Endpoints de tareas

Implementa los cinco endpoints y devuelve JSON serializado con códigos de estado HTTP apropiados:

- `GET /tasks`: devuelve todas las tareas.
- `POST /tasks`: recibe `title` obligatorio y `done` opcional (por defecto `false`), asigna un ID único y devuelve la tarea creada.
- `PUT /tasks/{task_id}`: reemplaza la tarea completa para ese ID.
- `PATCH /tasks/{task_id}`: actualiza parcialmente `title`, `done` o ambos.
- `DELETE /tasks/{task_id}`: elimina la tarea y devuelve confirmación JSON.

Cada tarea tiene `id` entero, `title` de texto y `done` booleano. Maneja IDs inexistentes con `404` y datos inválidos con los códigos de validación apropiados. Conserva los IDs al reemplazar o actualizar tareas.

## Almacenamiento y convenciones

- Declara una lista llamada `tasks` a nivel de módulo y úsala como único almacén de tareas.
- No añadas base de datos ni persistencia en archivos. Que los datos se reinicien al reiniciar el servidor es el comportamiento esperado.
- Sigue la estructura y los esquemas existentes en `src/app`; evita cambios no relacionados.

## Compatibilidad con el frontend

- No modifiques el frontend. Su flujo actual envía audio multipart o una transcripción manual como JSON a `POST /transcribe` y espera una respuesta con `transcription`, `instruction` y `result`.
- Implementa o conserva `POST /transcribe` según ese contrato: procesa audio con la transcripción de Groq o acepta la transcripción manual, obtiene la instrucción mediante la misma lógica LLM de `/instruction`, ejecuta la operación de tareas indicada y devuelve los tres campos esperados. No dupliques ni sustituyas la detección de intención con reglas manuales.
- Configura CORS y la URL de API para que el frontend incluido pueda completar este flujo sin cambios en su código.

## Criterios de aceptación

- Verifica que `GET`, `POST`, `PUT`, `PATCH` y `DELETE /tasks` funcionen, devuelvan JSON y manejen correctamente IDs y estados.
- Verifica el recorrido de voz de extremo a extremo para crear, listar, actualizar y eliminar tareas. La transcripción de «añade comprar leche a mi lista» debe acabar creando una tarea visible al listar.
- Comprueba que `/instruction` devuelve el descriptor estructurado para distintas intenciones, que CORS permite el origen del frontend y que `.env` permanece ignorado por Git.