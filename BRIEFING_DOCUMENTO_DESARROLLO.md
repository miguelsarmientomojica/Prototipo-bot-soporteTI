# Briefing para Diana — Documento de desarrollo del prototipo
### (Para usar directamente, incluso pegándolo en una conversación nueva con Claude)

Este documento reúne todo lo que necesitas para escribir el nuevo documento que pidió
el profesor. Es distinto del documento de investigación (Parte 1/Parte 2) que ya se
entregó antes — **este es el documento de desarrollo del prototipo**: metodología
Scrum, requerimientos, tecnologías, historias de usuario, resultados con evaluación
humana, y conclusiones. Verifica también `plantilla_proyecto.md` (la plantilla oficial
de la universidad) para formato, normas APA y la política de uso de IA — ese archivo
sigue aplicando para forma; este briefing te da el contenido.

**Puedes usar Claude (u otra IA) para redactar** — pega este archivo completo como
primer mensaje en una conversación nueva y pide que te ayude a desarrollar cada
sección. Solo recuerda la política institucional: máximo 15% de contenido generado por
IA, y el análisis/diagnóstico/conclusiones deben reflejar criterio propio del equipo.

---

## 1. Qué cambió — notas del profesor, ya interpretadas

| Nota del profesor (tal como se tomó en clase) | Qué significa en la práctica |
|---|---|
| "Desarrollar modelo de IA para una fintech en general, que no sea Credyty" | El documento no debe nombrar la empresa real ni datos suyos — se plantea como una fintech genérica. Ya está así en el prototipo (comercios ficticios, sin nombres reales). |
| "Fintech en Colombia, no generalizar y ya" | Ojo: esto NO contradice lo anterior. Significa: sitúa el proyecto en el contexto de las fintech colombianas específicamente (no "el mundo entero" ni "cualquier sector"), pero sin afirmar que los resultados apliquen a todas las fintech de Colombia sin más — sigue siendo un caso ilustrativo, no una generalización estadística. |
| "El proyecto pasó de implementar el bot a solo desarrollarlo" | No hace falta desplegar en producción ni conectar con sistemas reales de ninguna empresa. Sí hace falta **mostrar el bot funcionando**, aunque sea en tu propio computador. Esto ya lo tienes: el dashboard web corriendo local es exactamente esa evidencia. |
| "Crear un sistema que permita la automatización de clasificación de tickets" / "Crear un prototipo que permita la clasificación" / "Generar una clasificación general funcional" | Estos tres puntos ya están cumplidos por el prototipo actual — ver sección 2. |
| "Pedir a la IA generar 5k tickets... front, back, base de datos, todo lo que meta soporte TI" | Esto **no se ha ejecutado todavía** — se documenta como trabajo futuro (ver sección 7), no como algo ya hecho. No lo presentes como completado. |
| "Metodología implementada (Scrum)... requerimientos funcionales y no funcionales... tecnologías... historias de usuario o casos de uso (creación manual de tickets)... conclusión y trabajos futuros" | Esta es literalmente la estructura del nuevo documento — ver sección 8, ya viene armada. |
| "Resultados (instrumento de evaluación): someter a pruebas, evaluación del producto por personas" | Necesitas que **personas reales** (compañeros, el profesor, alguien del dominio) evalúen las clasificaciones del bot con un instrumento — no basta con que el bot "funcione", hay que demostrarlo con evaluación externa. Te dejo un instrumento listo en la sección 6. |
| "Dar el alcance más real posible, basado en lo que el prototipo pueda alcanzar" | El documento debe describir lo que YA EXISTE, no aspiraciones. Ver sección 3 (qué existe) y sección 9 (alcance honesto). |

---

## 2. Estado actual del prototipo (para que lo describas con precisión)

### Arquitectura actual

```
Generador de tickets sintéticos (datos ficticios)
        │
        ├──► Modo por lote: run_simulation.py → clasifica 30 tickets fijos → reporte Excel
        │
        └──► Modo dashboard web: genera y clasifica tickets uno a uno (automático o
             manual), visualizado en tiempo real en el navegador, con persistencia
             en base de datos SQLite local
```

Todo corre en una sola máquina, sin ningún servicio externo de pago obligatorio
(Ollama es gratis) y sin conexión a ningún sistema real de una empresa.

### Componentes ya construidos

- **`classifier/html_cleaner.py`** — limpia el HTML de un ticket a texto plano.
- **`classifier/prompt_builder.py`** — arma las instrucciones que recibe el modelo,
  incluida la taxonomía de 6 categorías y las reglas de negocio (política de
  prioridad, chequeo de completitud).
- **`classifier/ollama_client.py`** / **`classifier/claude_client.py`** — clasifican el
  ticket llamando al modelo (Ollama local por defecto, o Claude como alternativa de
  pago), forzando la respuesta a un formato JSON estructurado (function calling).
- **`classifier/routing.py`** — reglas deterministas (no decididas por el modelo) para
  calcular la fecha de vencimiento sugerida y el responsable sugerido.
- **`classifier/ticket_generator.py`** — genera tickets sintéticos aleatorios con
  plantillas por categoría, evitando repeticiones seguidas.
- **`database.py`** — base de datos SQLite local (2 tablas: tickets y
  clasificaciones), con persistencia real entre sesiones.
- **`dashboard/`** — aplicación web (Flask + HTML/CSS/JS) con dos vistas: tickets en
  vivo y tabla completa con filtros por categoría, comercio, prioridad, responsable,
  acción y nivel de confianza.

### Qué clasifica el bot, exactamente, por cada ticket

1. **Categoría** (Pregunta, Incidente, Problema, Pedido, Requerimiento, No soporte).
2. **Nivel de confianza** (0 a 1).
3. **Prioridad sugerida** (Baja, Normal, Alta, Urgente) — con una regla estricta: nunca
   sube la prioridad solo porque el texto diga "urgente", solo si hay un bloqueo real.
4. **Comercio sugerido** (a qué aliado/convenio pertenece el ticket).
5. **Fecha de vencimiento sugerida** — calculada con reglas fijas, no por el modelo.
6. **Responsable sugerido** — calculado con reglas fijas según categoría y comercio.
7. **Chequeo de completitud** (solo para "Incidente"): si el ticket no trae los datos
   mínimos para que un desarrollador lo pueda tratar, se marca como incompleto y se
   fuerza a revisión humana, sin importar qué tan segura esté el modelo.

### Qué NO existe todavía (sé honesta con esto en el documento)

- No hay conexión con Plumsail Helpdesk ni ningún sistema real (se descartó por
  seguridad de datos).
- No hay despliegue en la nube ni en un servidor accesible fuera de tu computador.
- No existe todavía el conjunto de 5,000 tickets sintéticos que pidió el profesor para
  la simulación a gran escala.
- No existe todavía un instrumento de evaluación ejecutado con personas reales (lo
  vamos a diseñar en este briefing, pero falta aplicarlo).

---

## 3. Tecnologías usadas (para la sección de tecnologías)

| Tecnología | Para qué se usa |
|---|---|
| Python 3 | Lenguaje principal de todo el backend y la lógica de clasificación |
| Flask | Framework web para el backend del dashboard |
| SQLite | Base de datos local, persistente, sin necesidad de instalar un servidor |
| Ollama + Qwen3:14B | Modelo de lenguaje ejecutado localmente, sin costo por uso |
| API de Anthropic (Claude) | Alternativa opcional de pago, intercambiable con Ollama |
| HTML5 / CSS3 / JavaScript (vanilla) | Frontend del dashboard, sin frameworks pesados |
| BeautifulSoup | Limpieza de HTML del contenido de los tickets |
| openpyxl | Generación de reportes en Excel (modo de simulación por lote) |
| Function calling / salida estructurada JSON | Técnica central para forzar que el modelo responda en un formato predecible y procesable por código |

---

## 4. Requerimientos funcionales y no funcionales (punto de partida, ajústalos)

### Funcionales

- RF1. El sistema debe generar tickets sintéticos automáticamente, con datos ficticios.
- RF2. El sistema debe permitir la creación manual de un ticket mediante un formulario
  (simulando a alguien de la empresa redireccionando o escalando un caso).
- RF3. El sistema debe clasificar cada ticket en una de 6 categorías predefinidas.
- RF4. El sistema debe sugerir prioridad, comercio asociado, fecha de vencimiento y
  responsable para cada ticket.
- RF5. El sistema debe verificar si un ticket de tipo "Incidente" trae la información
  mínima necesaria para ser atendido, y marcarlo como incompleto si no la trae.
- RF6. El sistema debe persistir cada ticket y su clasificación en una base de datos
  local.
- RF7. El sistema debe mostrar en una interfaz web, en tiempo real, los tickets
  recién procesados y su resultado de clasificación.
- RF8. El sistema debe permitir consultar el historial completo de tickets con
  filtros (categoría, comercio, prioridad, responsable, acción, confianza mínima).

### No funcionales

- RNF1. El sistema debe operar en su totalidad en infraestructura local, sin depender
  de servicios de nube de pago para su funcionamiento básico.
- RNF2. El modelo de lenguaje usado por defecto no debe generar costos recurrentes por
  uso (ejecución local vía Ollama).
- RNF3. El sistema no debe almacenar ni exponer datos reales de clientes o usuarios de
  ninguna organización — todos los datos de prueba son sintéticos.
- RNF4. El código debe mantener una separación modular entre limpieza de texto,
  construcción de instrucciones para el modelo, cliente del modelo, y reglas de
  negocio, para facilitar su mantenimiento y extensión futura.
- RNF5. (Sugerido, defínelo con tu equipo) El tiempo de respuesta por ticket
  clasificado debe mantenerse en un rango razonable para uso interactivo.

---

## 5. Historias de usuario / casos de uso

- **Como agente de soporte**, quiero que el sistema clasifique automáticamente los
  tickets entrantes, para no tener que leerlos y categorizarlos manualmente uno por
  uno.
- **Como coordinador de un comercio aliado**, quiero poder generar manualmente un
  ticket describiendo un caso escalado, para que el sistema lo analice igual que
  cualquier ticket real. *(Este es el caso de uso de creación manual que pidió el
  profesor — ya implementado en el dashboard.)*
- **Como líder de soporte**, quiero ver en un panel los tickets recientes y su
  clasificación en tiempo real, para monitorear el comportamiento del sistema.
- **Como líder de soporte**, quiero poder filtrar el historial de tickets por
  categoría, prioridad o responsable, para auditar las decisiones del sistema.
- **Como desarrollador del equipo de soporte**, quiero que el sistema detecte cuando
  un ticket de tipo "Incidente" no trae la información mínima necesaria, para evitar
  que se me asignen casos que no puedo resolver sin pedir más datos.

---

## 6. Instrumento de evaluación (para la sección de Resultados)

El profesor pide que el producto sea evaluado por personas — esto es lo que da validez
a la afirmación de que la investigación "tuvo éxito". Propuesta concreta, sencilla de
ejecutar antes del 30 de agosto:

**Diseño:**
1. Toma una muestra de 15-20 tickets ya clasificados por el bot (puedes usar el reporte
   que genera `run_simulation.py`).
2. Consigue 3-5 evaluadores (compañeros de clase, alguien con conocimiento de soporte
   TI, o el mismo docente) que no hayan visto las respuestas del bot de antemano.
3. Cada evaluador revisa cada ticket (el texto original + la clasificación del bot) y
   responde:

| Pregunta | Formato de respuesta |
|---|---|
| ¿La categoría asignada es correcta? | Sí / No / Parcialmente |
| ¿La prioridad sugerida es razonable? | Sí / No |
| ¿El resumen generado refleja bien el contenido del ticket? | Escala 1 a 5 |
| ¿La acción sugerida sería útil para un agente real? | Escala 1 a 5 |
| ¿Usarías este sistema como apoyo (no como reemplazo) en un proceso real de soporte? | Sí / No / Tal vez |

4. Consolida los resultados: porcentaje de acuerdo en categoría/prioridad, promedio de
   las escalas 1-5, y porcentaje de respuestas "Sí"/"Tal vez" en la última pregunta.
5. Esos números **son tu evidencia de resultados** — repórtalos tal cual salgan, sin
   ajustar el discurso a lo que "se esperaría" que salga.

---

## 7. Conclusiones y trabajos futuros (puntos sugeridos, redáctalos con tus palabras)

**Trabajos futuros a mencionar explícitamente:**
- Ampliar el conjunto de prueba a una escala mayor (del orden de miles de tickets
  sintéticos) cubriendo sistemáticamente front-end, back-end, base de datos y demás
  subdominios de soporte TI — pendiente, no ejecutado en esta fase.
- Definir un protocolo formal de "ground truth" (respuesta correcta de referencia)
  antes de ampliar el conjunto de prueba.
- Evaluar la integración con un sistema real de mesa de ayuda, sujeta a autorización y
  garantías de seguridad de datos.
- Explorar un diseño con grupo de comparación (clasificación manual paralela) para
  fortalecer la evaluación.

---

## 8. Estructura sugerida del nuevo documento

1. Introducción — "Desarrollo de un bot de IA para la clasificación de tickets de
   soporte TI en el contexto de una fintech colombiana" (ajusta el título con tu equipo)
2. Contexto: fintech en Colombia (sección 1 de este briefing)
3. Metodología de desarrollo: Scrum (ver cronograma de sprints, sección 9)
4. Requerimientos funcionales y no funcionales (sección 4)
5. Tecnologías usadas (sección 3)
6. Historias de usuario / casos de uso (sección 5)
7. Descripción del prototipo desarrollado (sección 2)
8. Resultados — instrumento de evaluación y hallazgos (sección 6)
9. Alcance real y limitaciones (sección "qué NO existe todavía", en la sección 2)
10. Conclusiones y trabajos futuros (sección 7)

---

## 9. Cronograma de sprints (Scrum) — con las fechas reales que diste

Inicio ~14 de junio, entrega preliminar 16 de agosto, entrega final 30 de agosto.
Este cronograma refleja lo que realmente se hizo, en orden:

| Sprint | Fechas aprox. | Qué se hizo |
|---|---|---|
| Sprint 1 | 14 - 27 jun | Diagnóstico del proceso de soporte, definición de la taxonomía real de categorías |
| Sprint 2 | 28 jun - 11 jul | Construcción del clasificador base (limpieza de texto, prompt, cliente del modelo) |
| Sprint 3 | 12 - 25 jul | Ajustes de arquitectura (sin sistemas externos), generador de tickets sintéticos |
| Sprint 4 | 26 jul - 8 ago | Dashboard web (backend + frontend), reglas de fecha/responsable, chequeo de completitud |
| Sprint 5 | 9 - 16 ago | Base de datos persistente, **entrega preliminar (16 ago)** |
| Sprint 6 | 17 - 30 ago | Instrumento de evaluación, documentación final, **entrega final (30 ago)** |

---

## 10. Recordatorio de seguridad

Ningún dato en el prototipo es real: nombres, comercios, correos y documentos son
ficticios. Si Diana necesita ejemplos de tickets para el documento, puede tomarlos
directamente de `data/tickets_sinteticos.json` o generarlos con
`classifier/ticket_generator.py` — nunca debe usarse información real de ninguna
empresa en este documento, dado que queda en custodia de la universidad.
