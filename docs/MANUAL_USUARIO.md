# Manual de usuario — Buscador de convocatorias

Guía práctica para usar la herramienta: encontrar convocatorias reales
(licitaciones, fondos, subvenciones, RFP/EOI), filtrarlas, verificarlas y llevar
el control de a cuáles se postuló tu organización.

Este manual es de **uso**. No explica cómo está construido el sistema.

---

## 1. Qué encuentras aquí y qué NO

**Qué encuentras:** convocatorias **reales**, publicadas por entidades y
organismos oficiales (contratación pública colombiana, agencias del Estado,
Naciones Unidas, banca multilateral y fondos internacionales). La herramienta
las revisa periódicamente, se queda con las que coinciden con los temas de
interés configurados, y te las muestra en un solo lugar para que no tengas que
entrar sitio por sitio.

**Qué NO encuentras:**

- **Datos inventados o completados.** Si la fuente oficial no publica el monto,
  la fecha de cierre o los requisitos, aquí aparece vacío ("Sin monto
  publicado", "Sin fecha"). La herramienta **nunca rellena un dato que la fuente
  no publicó**. Un campo vacío significa "la fuente no lo dice", no "no existe".
- **Interpretaciones oficiales.** Nada de lo que ves aquí reemplaza el documento
  original de la convocatoria.

**La regla de oro:** cada convocatoria trae siempre el enlace a su
**publicación original**. Antes de invertir tiempo en una propuesta —y siempre
antes de postularte— abre ese enlace y confirma allí las condiciones, las fechas
y los requisitos. La herramienta te ahorra la búsqueda; la verificación final la
haces tú.

---

## 2. Recorrido por la interfaz

En la barra superior están las cinco secciones: **Dashboard**, **Buscar**,
**Histórico**, **Asistente IA** y **Fuentes**. A la derecha está el botón
**Actualizar ahora**, y abajo a la derecha, un botón redondo con un signo
**?** que abre la **Ayuda con IA**.

### Dashboard
La foto general del momento. Muestra:

- Cuatro indicadores: **Total convocatorias**, **Abiertas**, **Nuevas (7 días)**
  y **Cierran (7 días)**.
- Tres gráficos de barras: **Por fuente**, **Por estado** y **Por departamento**,
  para ver de dónde viene el grueso de lo que hay disponible.
- **Cierran pronto (abiertas)**: las convocatorias abiertas con la fecha de
  cierre más próxima. Es la lista por la que conviene empezar el día.

### Buscar
El buscador completo, con todos los filtros y el listado de resultados. Es donde
harás la mayor parte del trabajo. Cada resultado es una tarjeta con la entidad
que publica, el monto, las fechas, y tres acciones: marcar **Participar**, abrir
**Ver ficha y validar** y **Ver publicación oficial y verificar entidad**.

### Histórico
El registro de lo que tu organización ya decidió. Aquí quedan las convocatorias
marcadas como **"Ya nos postulamos"** y las **descartadas**. Puedes consultar
cuáles fueron, **quién** las marcó y **cuándo**, y **deshacer la marca** si se
hizo por error (al deshacerla, la convocatoria vuelve a aparecer en Buscar).

### Asistente IA
Un buscador en el que escribes con tus palabras, en lugar de llenar filtros. Ver
la sección 6.

### Fuentes
El estado de los sitios oficiales de los que se traen las convocatorias. Para
cada uno verás si está activo, cuándo fue la última revisión, cuántas
convocatorias trajo (**Obtenidos**, **Nuevos**, **Actualizados**, **Cerrados**)
y un mensaje de error si algo falló. Con **Ejecutar fuente** pides que se revise
esa fuente en ese momento, y con **Historial** ves sus revisiones anteriores.

Esta pantalla sirve para responder una pregunta muy concreta: *"¿no hay
convocatorias nuevas porque no las hay, o porque una fuente está fallando?"*.

### Botón "Actualizar ahora"
Pide que se revisen **todas** las fuentes activas de inmediato, sin esperar a la
revisión automática. Tarda unos minutos; el avance se ve en **Fuentes**. No hace
falta usarlo a diario: la herramienta se actualiza sola de forma periódica.

---

## 3. Cómo buscar bien

Todos los filtros están en la parte de arriba de **Buscar**. Se combinan entre
sí (se aplican todos a la vez) y se activan con el botón **Buscar**. El botón
**Limpiar** los borra todos y vuelve al listado completo.

| Filtro | Qué hace | Cuándo usarlo |
|---|---|---|
| **Palabra clave** | Busca el texto en el título y la descripción de la convocatoria. | Para acotar por tema o sector: *primera infancia*, *energía solar*, *formación docente*. Es el filtro más potente; empieza siempre por aquí. |
| **Orden** | Cambia el criterio del listado: publicación (recientes o antiguas primero), cierre (próximas o lejanas primero), monto (mayor o menor primero) o última vez visto. | *Cierre (próximas primero)* cuando corres contra el tiempo; *Publicación (recientes primero)* para revisar novedades. |
| **Fuente** | Limita a un solo origen (SECOP II, PNUD, MinCiencias, MinTIC, Banco Mundial, Grants.gov...). | Cuando ya sabes que solo te sirve un origen, o cuando quieres revisar a fondo lo que trajo uno en concreto. |
| **Estado** | `abierta`, `cerrada`, `adjudicada`, `vencida`, `desconocido`. | Deja **abierta** para lo que todavía se puede postular. `desconocido` = la fuente no publicó un estado claro; conviene abrir la publicación oficial. |
| **Tipo** | `licitacion`, `subvencion`, `fondo`, `rfp`, `eoi`, `otro`. | Si buscas financiación no reembolsable, prueba `subvencion` y `fondo`. Si buscas prestar un servicio, `licitacion` y `rfp`. |
| **Departamento** | Departamento donde se ejecuta o desde donde se publica. Se escribe completo (ej. *Antioquia*). | Para concentrarte en tu zona de operación. |
| **Ciudad** | Municipio o ciudad de la convocatoria (ej. *Medellín*, *Barranquilla*). | Cuando tu trabajo es local y el departamento te trae demasiado ruido. Ten en cuenta que no todas las fuentes publican la ciudad: si filtras por ciudad, dejas fuera las que no la informan. |
| **Ámbito** | El alcance de quien convoca: **nacional** (ministerios, agencias y entidades del orden nacional), **territorial** (alcaldías, gobernaciones, distritos y autoridades regionales) e **internacional** (organismos multilaterales, cooperación y fondos de otros países). | **territorial** es el filtro clave si tu organización trabaja con gobiernos locales; **internacional** si buscas cooperación o fondos en divisas. |
| **Solo aptas para fundaciones nuevas / primerizas** | Casilla que deja únicamente las convocatorias con el distintivo explicado en la sección 4. | Cuando tu organización es reciente o no tiene un historial de contratos que acreditar. |
| **Publicada desde / Publicada hasta** | Rango de fecha de publicación. | Para ver solo lo aparecido desde tu última revisión. |
| **Cierra desde / Cierra hasta** | Rango de fecha de cierre. | Para encontrar lo que cierra dentro de un plazo que sí alcanzas a preparar. |
| **Monto mínimo / Monto máximo** | Rango del valor publicado, en la moneda de cada convocatoria (normalmente pesos colombianos). | Para descartar lo demasiado pequeño o lo que excede tu capacidad operativa. Ojo: **las convocatorias sin monto publicado quedan fuera** cuando usas este filtro. |

**Consejos prácticos**

- Empieza amplio y ve cerrando. Si pones cinco filtros de entrada, es fácil
  terminar con cero resultados sin saber cuál sobraba.
- Junto al listado se indica cuántos **filtros activos** tienes y cuántos
  resultados hay. Si el número te sorprende, revisa esa cuenta.
- Filtrar por monto, ciudad o fechas **excluye** las convocatorias a las que la
  fuente no les publicó ese dato. Si sospechas que se te está escapando algo,
  quita ese filtro y revisa a mano.
- Los enlaces del buscador conservan tus filtros: puedes guardar la dirección de
  una búsqueda que uses mucho y volver a ella.

---

## 4. El distintivo "Apto para fundaciones nuevas"

Algunas convocatorias muestran una etiqueta **"Fundaciones nuevas"**, y con la
casilla **"Solo aptas para fundaciones nuevas / primerizas"** puedes ver
únicamente esas.

**Qué significa:** el texto de esa convocatoria (título, descripción,
requisitos y modalidad) contiene señales de que está abierta a organizaciones
recién creadas, primerizas o sin trayectoria previa —por ejemplo, capital
semilla, emprendimiento, primera convocatoria, sin exigencia de experiencia
acreditada— y **no** contiene señales de lo contrario, como exigir años de
experiencia previa o contratos similares ya ejecutados.

**Qué NO significa:**

- **No es una garantía de elegibilidad.** Es una señal orientativa calculada a
  partir del texto publicado, no una revisión de los términos de referencia.
- **Que una convocatoria no tenga la etiqueta no quiere decir que estés
  excluido.** Significa solo que no se encontró evidencia en el texto: puede ser
  que la fuente publique poco detalle en el listado y los requisitos reales
  estén en un documento adjunto.

**Cómo usarlo bien:** trátalo como un atajo para priorizar tu lectura, no como
un veredicto. Antes de trabajar en una propuesta, abre **Ver publicación oficial
y verificar entidad** y confirma en el documento oficial los requisitos de
experiencia, la naturaleza jurídica exigida y los años de constitución.

---

## 5. Flujo de trabajo recomendado

La herramienta está pensada para que un equipo pueda revisar convocatorias sin
pisarse ni repetir trabajo. El ciclo completo es este:

**1. Marca "Participar" en las que te interesan.**
En cada tarjeta de resultado hay una casilla **Participar**. Al marcarla, la
convocatoria entra en tu selección de trabajo. Abajo aparece una barra flotante
con el conteo (*"N convocatoria(s) seleccionada(s) para participar"*). La
selección se mantiene mientras navegas entre páginas y secciones, así que puedes
ir juntando candidatas de varias búsquedas distintas. El botón **Limpiar** de
esa barra vacía la selección.

**2. Descarga el Excel con la selección.**
Con el botón **Descargar Excel** obtienes un archivo con todas las
convocatorias marcadas y sus datos para trabajar (entidad, fechas, monto,
requisitos y el **enlace a la publicación original** de cada una). Es el archivo
que puedes compartir con tu equipo, revisar en reunión o usar para repartir
responsables. Como incluye la URL original, cualquiera puede comprobar que la
convocatoria existe y sigue vigente.

**3. Cuando envíes la postulación, marca "Ya nos postulamos".**
Al momento de radicar la propuesta, marca la convocatoria como **"Ya nos
postulamos"** e indica el **responsable** (quién quedó a cargo). Esa
convocatoria **sale del listado de Buscar** y pasa a **Histórico**. Así nadie
del equipo la vuelve a evaluar desde cero ni se duplica el esfuerzo.

**4. Descarta lo que no interesa.**
Para las convocatorias que revisaste y decidiste no perseguir, usa
**Descartar**. También salen de la búsqueda y quedan registradas en el
**Histórico**. Descartar es tan importante como postularse: mantiene el listado
limpio y hace que lo que queda visible sea trabajo pendiente real.

**5. Consulta y corrige en el Histórico.**
En **Histórico** ves todo lo marcado —postulado y descartado—, con **quién** lo
marcó y **cuándo**. Si algo se marcó por error, puedes **deshacer la marca** y
la convocatoria vuelve al listado de Buscar como si nada.

**Regla de oro del flujo:** solo se marca "Ya nos postulamos" cuando la
postulación **realmente se envió**. Si aún la estás preparando, déjala en
"Participar" — así sigue visible para el equipo y no se pierde de vista su fecha
de cierre.

---

## 6. El Asistente IA

La sección **Asistente IA** te deja buscar escribiendo con tus propias palabras,
sin llenar filtros. Escribes la frase, pulsas **Preguntar** y el asistente la
traduce a filtros y te muestra las convocatorias **reales** que hay en la base
de datos. Debajo de los resultados verás qué **filtros aplicó**, para que sepas
cómo interpretó tu pregunta y puedas afinarla.

**Ejemplos de preguntas que funcionan bien:**

- *fondos de innovación abiertos en Antioquia*
- *licitaciones de software abiertas*
- *convocatorias de educación en Bogotá*
- *subvenciones para fundaciones nuevas o primerizas*
- *convocatorias que cierran este mes con monto mayor a 50 millones*
- *convocatorias de cooperación internacional en salud*

Cuanto más concreta la frase (tema + lugar + estado + plazo), mejor traduce.

**Resumir una convocatoria.** Dentro de **Ver ficha y validar**, el botón
**Resumir con IA** genera un resumen corto de la descripción y los requisitos.
Sirve para decidir rápido si vale la pena leer el documento completo. El resumen
se hace **solo** con el texto que publicó la fuente: si la fuente publica poco,
el resumen lo dirá en lugar de rellenar.

**El botón "?" (Ayuda con IA).** El botón redondo abajo a la derecha abre un
chat de ayuda sobre **cómo usar la herramienta** (los filtros, el flujo de
trabajo, qué significa cada cosa). Responde con base en este manual.

**Si aparece el aviso de que la IA no está disponible:**

> *El asistente de IA no está disponible; se usó búsqueda por palabra clave
> simple con tu pregunta.*

No es un fallo grave y **no pierdes acceso a nada de los datos**. Significa que
la interpretación en lenguaje natural está fuera de servicio en ese momento, así
que tu frase se usa tal cual como palabra clave. Los resultados serán menos
afinados, pero siguen siendo convocatorias reales. Mientras tanto, usa **Buscar**
con los filtros: es la vía completa y no depende de la IA en ningún momento. Si
el aviso persiste durante días, avisa a quien administra el sistema.

**Importante:** las respuestas de la IA son una ayuda de lectura, no una fuente.
Las convocatorias que muestra son reales y salen de la base de datos, pero
cualquier interpretación, resumen o condición debe confirmarse en la publicación
oficial.

---

## 7. Cómo verificar que una convocatoria y su entidad son reales

Nunca prepares una propuesta —y mucho menos envíes documentos o dinero— sin
hacer esta comprobación. Toma dos minutos.

**1. Abre la publicación oficial.**
En cada tarjeta y dentro de la ficha está el enlace **"Ver publicación oficial y
verificar entidad"**. Te lleva al aviso tal como lo publicó la entidad en su
sitio oficial. Ahí confirmas que la convocatoria existe, que sigue abierta y
cuáles son las condiciones y los plazos vigentes. **Si el enlace no abre, la
página no existe o el contenido no coincide con lo que ves aquí, no sigas
adelante** hasta aclararlo.

**2. Revisa el bloque "Validar organización emisora".**
Al abrir **Ver ficha y validar** verás, destacado, el nombre de la entidad que
publica y su ubicación. Es el dato que debes verificar, no el título de la
convocatoria.

**3. Consulta la entidad en RUES.**
Desde la misma ficha, el enlace **"Buscar en RUES (Colombia)"** te lleva al
Registro Único Empresarial y Social con el nombre de la entidad ya cargado. Ahí
compruebas que la organización existe legalmente, su estado y sus datos de
identificación. El enlace **"Buscar en la web"** hace una búsqueda general por
el nombre real de la entidad, útil para detectar suplantaciones o nombres
parecidos.

**Señales de alerta:**

- La convocatoria pide un pago para "inscribirse" o "reservar cupo".
- El contacto es un correo personal o un dominio que no corresponde a la entidad.
- La entidad no aparece en RUES ni tiene sitio oficial verificable.
- El enlace oficial lleva a una página distinta de la que dice ser.

Ante cualquiera de ellas, no envíes documentación y consulta con tu equipo.

---

## 8. Preguntas frecuentes

**¿De dónde salen estas convocatorias?**
De los sitios oficiales de las entidades y organismos que las publican. La
herramienta las lee de ahí y las trae; no las redacta ni las edita.

**¿Puede aparecer una convocatoria falsa o inventada?**
La herramienta no inventa ninguna. Todo lo que ves viene de una publicación
oficial y trae su enlace. Aun así, la verificación de la sección 7 es
obligatoria: te protege de errores de la fuente y de suplantaciones.

**¿Por qué esta convocatoria no tiene monto / fecha de cierre / requisitos?**
Porque la fuente no los publicó en el listado. Preferimos dejarlo vacío antes
que inventar un dato. Ábrela en la publicación oficial: casi siempre están en
los documentos adjuntos.

**¿Cada cuánto se actualiza?**
Se revisa sola de forma periódica varias veces al día. Si necesitas lo más
reciente en este instante, usa **Actualizar ahora** y espera unos minutos.

**¿Por qué el Dashboard dice que hay convocatorias abiertas y en Buscar veo menos?**
Porque las que ya marcaste como **"Ya nos postulamos"** o **descartadas** salen
del listado de Buscar. Las encuentras en **Histórico**.

**Marqué "Ya nos postulamos" por error, ¿puedo arreglarlo?**
Sí. Ve a **Histórico**, busca la convocatoria y deshaz la marca. Vuelve a
aparecer en Buscar inmediatamente.

**¿Otra persona del equipo ve mis marcas?**
Sí. Las marcas de "Ya nos postulamos" y "Descartar" quedan registradas con
responsable y fecha, y son las mismas para todo el equipo. Por eso conviene
indicar bien el responsable.

**Una fuente lleva días sin traer nada, ¿qué reviso?**
Entra a **Fuentes** y mira la última ejecución de esa fuente: si hay un mensaje
de error, la fuente probablemente cambió y hay que avisar a quien administra el
sistema. Si no hay error y simplemente trajo cero, es que no hubo publicaciones
nuevas que coincidan con los temas configurados.

**Busqué algo que sé que existe y no aparece.**
Tres causas habituales, en este orden: (1) tienes filtros activos que la
excluyen —pulsa **Limpiar** y busca solo por palabra clave—; (2) ya está marcada
en **Histórico**; (3) la convocatoria no coincide con los temas de interés
configurados en el sistema, y en ese caso hay que pedirle a quien lo administra
que amplíe esos temas.

---

## 9. Glosario

| Término | Qué significa |
|---|---|
| **Convocatoria** | Cualquier oportunidad publicada por una entidad para contratar, financiar o seleccionar: una licitación, un fondo, una subvención, un llamado a propuestas. |
| **SECOP II** | Sistema Electrónico de Contratación Pública de Colombia. Es donde el Estado colombiano publica sus procesos de contratación. |
| **PNUD** | Programa de las Naciones Unidas para el Desarrollo. Publica avisos de adquisiciones y contratación para sus proyectos. |
| **RFP** | *Request for Proposal* (solicitud de propuesta). Piden una propuesta técnica y económica completa para prestar un servicio. |
| **EOI** | *Expression of Interest* (manifestación de interés). Un paso previo, más corto: manifiestas que te interesa y quedas en la lista de invitados a la etapa siguiente. |
| **Licitación** | Proceso competitivo en el que una entidad contrata un bien o servicio. Compites ofreciendo prestarlo. |
| **Subvención / Fondo** | Recursos que se entregan para ejecutar un proyecto, normalmente sin devolución. Compites presentando el proyecto, no un precio. |
| **Convocatoria nacional** | La publica una entidad del orden nacional: un ministerio, una agencia o un organismo del Estado central. |
| **Convocatoria territorial** | La publica un gobierno local: una alcaldía, una gobernación, un distrito o una autoridad regional. Suelen ser de menor monto y más accesibles para organizaciones locales. |
| **Convocatoria internacional** | La publica un organismo multilateral, una agencia de cooperación o un fondo de otro país. Suele exigir documentación en inglés y montos en divisas. |
| **Entidad emisora** | La organización que publica la convocatoria y con la que se firmaría el contrato o el convenio. Es la que hay que verificar. |
| **RUES** | Registro Único Empresarial y Social de Colombia. Registro público donde se comprueba que una organización existe legalmente y en qué estado está. |
| **Estado `desconocido`** | La fuente no publicó un estado claro para esa convocatoria. No quiere decir que esté cerrada: hay que mirarlo en la publicación oficial. |
| **Publicación original** | El aviso tal como lo publicó la entidad en su sitio oficial. Es la única versión que tiene validez. |

---

## Si tu duda no es de uso

Este manual y la **Ayuda con IA** cubren cómo usar la herramienta. Para todo lo
demás —instalar el sistema, cambiar su configuración, agregar fuentes nuevas,
ampliar los temas de interés o resolver un fallo técnico— contacta a **quien
administra el sistema** en tu organización.
