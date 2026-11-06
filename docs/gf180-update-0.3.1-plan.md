# Plan de actualización GF180 — dev/0.3.1

## Objetivo y alcance

Actualizar el template wafer.space a 1.6.0, su PDK y su LibreLane, e incorporar
GF180 Precheck 1.7.4. Migrar la instalación GF180 de uso general de Volare a
Ciel 3.1.0 y actualizar su PDK
sin alterar el PDK, el template ni el entorno LibreLane de IHP.
Este documento es un plan: no representa una actualización ya implementada.

## Revisiones verificadas en upstream

| Componente | Actual | Objetivo |
| --- | --- | --- |
| Template GF | `33e4b5ecc9faac82787fa7cb205f08377e27b912` | tag `1.6.0`, commit `d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c` |
| LibreLane privado GF | `df37e133fc3426c16e8356b1f50a17f8d6082f60` | `99148a9c1e648cdfdb9d7b772481af32e0dfbe8b` |
| PDK privado GF | `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` | `792ef67037d74c8c51811eab3ce23cf793491296` |
| Precheck GF | Sin integración encontrada en el repositorio | tag `1.7.4`, commit `9b4e7dab6af073d02b81ecc368069540d2f67db9` |
| Gestor PDK GF | Volare `0.18.1` para GF global | Ciel `3.1.0`, commit `e180507a4190462d65cdded4448eb4f7bd2f30fa` |

Fuentes consultadas: refs Git de los repositorios wafer.space, `Makefile` y
`flake.lock` de ambos commits objetivo. Tanto template como precheck declaran el
mismo PDK y el mismo commit LibreLane. Preservar sus locks; no resolver sus ramas
flotantes (`leo/update-pdks` y `dev`) ni regenerar locks.

- https://github.com/wafer-space/gf180mcu-project-template/tree/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c
- https://github.com/wafer-space/gf180mcu-precheck/tree/9b4e7dab6af073d02b81ecc368069540d2f67db9

### Ciel verificado para wafer.space 1.6.0

El `flake.lock` del template resuelve `librelane.inputs.ciel` al tag `3.1.0`,
commit `e180507a4190462d65cdded4448eb4f7bd2f30fa`. El `pyproject.toml` de ese
commit declara `version = "3.1.0"` y Python `>=3.8`. El lock de precheck 1.7.4
resuelve exactamente el mismo Ciel. Es una comprobación de fuentes y resolución
Nix, no una ejecución del binario: confirmar `ciel --version` en el entorno
materializado y registrar su ruta forma parte de los gates de implementación.

Fuentes adicionales:
- https://github.com/wafer-space/gf180mcu-project-template/blob/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c/flake.lock
- https://github.com/fossi-foundation/ciel/blob/e180507a4190462d65cdded4448eb4f7bd2f30fa/pyproject.toml

## Invariantes de protección de IHP

No modificar:

- `librelaneTemplates.ihp`, incluido su PDK `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`
  y LibreLane `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.
- El pin global `IHP_PDK_REPO_COMMIT`:
  `cfc0e22b92306178ebb5a5bc4865afe3294654d0`.
- La selección predeterminada y los parches/instaladores de IHP, salvo adaptación
  mínima de compatibilidad justificada y cubierta por pruebas.
- `/opt/pdks/ihp-sg13g2` ni los recursos privados del template IHP.

Se permite actualizar LibreLane global y herramientas compartidas cuando una
necesidad de GF esté demostrada. La protección de IHP pasa de congelar todas las
herramientas a conservar sus PDKs y validar su funcionamiento con las versiones
nuevas. La ausencia de restricciones declaradas no demuestra compatibilidad.

La reconstrucción de capas compartidas no garantiza binarios idénticos cuando
hay dependencias flotantes. Registrar inventarios y validar IHP en la imagen
resultante, además de comprobar los pins.

## Fase 1 — Baseline y migración del PDK global a Ciel

1. Capturar inventario de una imagen base identificada por ID: pins, versiones,
   destinos de enlaces, recursos y resultados de pruebas GF/IHP disponibles.
2. Confirmar el repositorio/familia y los artefactos Ciel que corresponden al
   commit `792ef67037d74c8c51811eab3ce23cf793491296`; revisar estructura,
   manifiestos de bibliotecas, soporte analógico, licencias y compatibilidad con
   KLayout, Xschem, ngspice y Magic instalados.
3. Sustituir el build GF Volare/open_pdks por descarga y activación con Ciel
   3.1.0 durante el build. El pin antiguo open_pdks
   `0fe599b2afb6708d281543108caf8310912f54af` no se sustituye por el commit del
   PDK nuevo: registrar pins separados para Ciel y el artefacto GF en el manifiesto.
4. Usar el comando upstream como referencia, con raíz global explícita:
   `ciel enable 792ef67037d74c8c51811eab3ce23cf793491296 --pdk-root /opt/pdks --pdk gf180mcuD --include-libraries all`.
   Verificar disponibilidad de artefactos para la arquitectura objetivo y preservar
   la raíz Ciel completa y los enlaces necesarios al copiar al runtime. Mantener
   `/opt/pdks/gf180mcuD` como interfaz pública y las raíces privadas independientes.
   Si faltan recursos analógicos o falla compatibilidad, registrar el bloqueo y
   resolverlo antes de aceptar la migración; no ocultarlo con fallback a Volare.
5. No copiar decks nuevos sobre bibliotecas antiguas sin verificar su matriz de
   compatibilidad. No aplicar ciegamente el parche actual open_pdks a Ciel.

## Fase 1B — Herramientas compartidas y matriz de compatibilidad

1. Comparar requisitos de GF nuevo con las versiones globales actuales y con las
   dependencias fijadas en los locks IHP/GF. Registrar por herramienta: versión
   actual, objetivo inmutable, motivo, consumidores y pruebas necesarias. Revisar
   KLayout, Magic, ngspice, Xschem, Netgen, Python y LibreLane según dependencias
   reales; no asumir que todas necesitan actualización.
2. Cambiar solo herramientas necesarias, una por vez o por grupo de dependencias
   inseparables. No elegir automáticamente la última versión ni asumir que el
   LibreLane del template puede sustituir al global sin revisar su instalación.
3. Mantener los locks y entornos privados de ambos templates. Una actualización
   global no debe reemplazar sus ejecutables Nix ni inyectar paquetes Python o
   bibliotecas mediante variables heredadas. Verificar qué ejecutable y versión
   resuelve cada contexto, incluyendo herramientas que invoquen rutas absolutas.
4. Después de cada cambio compartido, construir su stage y ejecutar regresiones
   rápidas de GF e IHP en un runtime que contenga realmente el cambio. Validar
   ambos flujos completos con la combinación final antes de aceptar la imagen.
5. Si aparece regresión IHP, investigar y adaptar mínimamente la integración sin
   cambiar su PDK. Si no se consigue una versión común compatible, conservar
   versiones aisladas por entorno; no sacrificar IHP para unificar versiones.
6. Ampliar los contratos del manifiesto con una lista explícita de cambios
   compartidos autorizados. Mantener el resto de pins congelados y registrar
   diferencias de inventario y resultados frente al baseline.

## Fase 2 — Template y precheck aislados

1. Actualizar únicamente `librelaneTemplates.gf` en `manifest.json` con los tres
   commits objetivo. Mantener `gf180mcuD` y los defaults upstream.
2. Validar el instalador con el nuevo Makefile y lock. Instalar todas las
   bibliotecas necesarias: upstream ahora usa `--include-libraries all`.
3. Registrar el pin del precheck explícitamente en el manifiesto e implementar
   su instalación y launcher GF-only. No existe actualmente una integración que
   se pueda actualizar simplemente cambiando una versión.
4. Materializar el entorno Nix del precheck a partir de SU lock; reutilizar un
   entorno solo si se demuestra la compatibilidad de sus dependencias completas,
   no solo porque coincide el commit de LibreLane.
5. Ejecutar precheck con su PDK GF privado, entorno saneado, parámetros explícitos
   y salida en el proyecto o `tests/run/`. No descargar ni actualizar locks en
   runtime. Conservar soporte para UID/GID arbitrario de los launchers actuales.
6. Actualizar LibreLane global solo si un flujo global GF lo requiere y supera
   las regresiones IHP; template y precheck conservan sus entornos privados.

## Fase 3 — PDK global GF y bibliotecas

1. Reescribir `images/pdks/install_gf180mcu.sh` para usar Ciel en vez de
   `volare build`/`volare enable`. Revisar el stage `gf180_pdk`, sus argumentos,
   dependencias, copias y metadatos. No ejecutar `prepare_open_pdks` ni extraer
   macros del fd_pr antiguo para completar automáticamente el PDK nuevo.
   Auditar los recursos del artefacto Ciel y adaptar solo lo necesario.
2. Instalar Ciel 3.1.0 de forma reproducible en el entorno de build y, si se
   expone el comando al usuario, en un entorno runtime compatible y controlado.
   Registrar versión y commit en el manifiesto; verificar `ciel --version` y la
   ruta efectiva. Auditar dependencias Python antes de modificar paquetes comunes.
   Los templates mantienen el Ciel de sus propios locks, incluido IHP.
3. Auditar todos los consumidores de Volare, incluidos
   `images/base/python_packages.sh`, `images/builder/exhaustive-install.sh`,
   `images/pdks/prepare_open_pdks.sh`, `gf180_integrity.py`, Dockerfile, inventario
   y contratos. Retirar dependencias y helpers solo si ya no tienen consumidores;
   no reemplazar globalmente cadenas `volare` que sigan siendo válidas.
4. Adaptar el chequeo de integridad a la estructura real `ciel/gf180mcu/versions/`
   y verificar enlaces sin asumir el backing A de la instalación antigua.
   Preservar recursos privados necesarios; no exponer variantes extra por accidente.
5. Mantener `set_pdk gf180mcuD`/`sak-pdk gf180mcuD`, la SCL predeterminada actual y
   la selección IHP. Las bibliotecas nuevas son opciones, no cambios de default.
6. Verificar presencia y selección explícita de `gf180mcu_as_sc_mcu7t3v3` y
   `gf180mcu_ocd_sc_rt12t3v3` en los entornos que las soporten. Documentar que la
   primera no está completamente verificada en silicio y la segunda no está
   verificada en silicio; no presentar estas opciones como signoff validado.
7. Revisar los parches GF actuales: estructura de PCells, activación gdsfactory,
   efuse, macros, variantes y rutas Xschem. Retirar/adaptar solo lo que corresponda
   al nuevo upstream; probar idempotencia y comportamiento entre capas Docker.

## Fase 4 — Pruebas y gates

### Contratos de host y comprobaciones estáticas

- Introducir pruebas que fallen con los pins antiguos y pasen con los objetivos;
  fijar explícitamente las invariantes IHP y el aislamiento de entornos.
- Adaptar `tests/test_librelane_templates.py` y
  `tests/test_repository_contract.py`: hoy exigen igualdad de pins GF con el
  baseline. No actualizar masivamente el baseline ni eliminar protección IHP.
- Probar argv, código de salida y ausencia de descargas del launcher precheck.
- Añadir contratos de instalación Ciel: versión exacta, commit GF, raíz explícita,
  todas las bibliotecas, enlaces válidos y ausencia de invocaciones Volare en el
  instalador GF. Actualizar inventario: no identificar el nuevo GF como el
  open_pdks antiguo. Probar funcionamiento offline con PDKs preinstalados.
- Ejecutar contratos host, `bash -n`, chequeo Docker con argumentos resueltos por
  los wrappers y `git diff --check`.

### Builds y pruebas reales

1. Construir primero el stage GF afectado y/o overlay de templates, con jobs
   acotados y logs persistentes. Esto no sustituye la imagen final.
2. Construir la imagen final y registrar su ID. Montar tests separados de diseños;
   escribir resultados en `tests/run/`, nunca sobre trabajo del usuario.
3. GF global: entorno, selección de SCL, enlaces, ngspice MOSFET, KLayout PCells,
   extracción/layout y smoke LibreLane compatibles con la instalación elegida.
4. Template GF: RTL, implementación completa, métricas y GDS no vacíos y simulación
   gate-level. Mantener IR drop y política upstream, sin omisiones para forzar éxito.
5. Precheck 1.7.4: ejecutar sobre un diseño compatible y añadir caso negativo con
   salida de error comprobada. Un fixture que deba fallar no valida signoff.
6. Reglas nuevas: buscar y ejercitar fixtures upstream para DCF.1a, DF.11,
   CO.5a/b, extracción LDMOS y filler; registrar resultados. La presencia de un
   archivo o el pin por sí solos no prueban esas correcciones.
7. IHP: selección, simulación analógica, KLayout, extracción y template completo
   RTL → GDS → GL; repetir alternancia IHP → GF → IHP en el mismo shell para
   detectar contaminación de variables/rutas. Usar tests existentes y añadir los
   que falten tras revisar cobertura real.
8. Confirmar que los flujos largos excluidos de `make test` se ejecutan
   explícitamente; no confundir suite habitual con validación completa.

## Criterios de aceptación

- Template GF 1.6.0 y precheck 1.7.4 instalados y ejercitados con pins exactos.
- GF global instalado mediante Ciel 3.1.0 con el commit objetivo, sin build Volare
  ni mezcla silenciosa de recursos antiguos; comandos habituales funcionan
  offline y los enlaces son válidos en la imagen final.
- PDK GF objetivo verificado en los entornos actualizados. Informar por separado
  el estado global y el privado; cualquier bloqueo global queda pendiente, no
  declarado como resuelto.
- Ningún pin del PDK o template IHP cambia. Cada actualización compartida está
  justificada y fijada; pruebas IHP y GF pasan en la imagen nueva, sin contaminación
  al alternar PDKs. Los contratos permiten solo los cambios autorizados.
- Nuevas SCL disponibles donde corresponda, opt-in y con advertencias de silicio.
- Documentación actualizada de versiones, rutas, comandos y límites de validación.
- Entrega con IDs de imagen, inventarios, logs y resultados reales, distinguiendo
  chequeos estáticos, builds parciales, imagen final y signoff de fabricación.

## Rollback

Mantener la imagen anterior por ID y los pins anteriores. No borrar caches ni
PDKs de la imagen base para recuperar espacio sin aprobación. Si falla GF o IHP,
no publicar: revertir o aislar la herramienta compartida incompatible, o corregir
la integración y repetir los gates afectados. Revertir también cambios GF cuando
corresponda; conservar registro de la combinación de versiones validada.
No hacer commit, push ni publicación sin solicitud explícita.
