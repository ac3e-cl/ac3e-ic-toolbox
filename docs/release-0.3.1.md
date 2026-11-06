# Release 0.3.1 — GF180 y auditoría de aceptación

**Estado: imagen construida; validación incompleta y release no aprobada.**
Resultado final y evidencia en [release-0.3.1-validation.md](release-0.3.1-validation.md).
El [plan GF180](gf180-update-0.3.1-plan.md) define el alcance completo.
Estas notas distinguen objetivos de integración de resultados realmente obtenidos.

## Revisiones objetivo y límites

| Componente | Objetivo inmutable |
| --- | --- |
| Template wafer.space GF180 | 1.6.0 — `d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c` |
| LibreLane privado GF | `99148a9c1e648cdfdb9d7b772481af32e0dfbe8b` |
| PDK GF global y privado | `792ef67037d74c8c51811eab3ce23cf793491296` |
| Ciel global | 3.1.0 — `e180507a4190462d65cdded4448eb4f7bd2f30fa` |
| Precheck GF del plan | 1.7.4 — `9b4e7dab6af073d02b81ecc368069540d2f67db9`; instalación y ejecución requieren evidencia independiente |

Los nuevos argumentos son `CIEL_VERSION`, `CIEL_REPO_COMMIT` y
`GF180_PDK_COMMIT`. Los argumentos legacy, incluidos `OPEN_PDKS_*` y
`PDK_BUILD_JOBS`, se conservan por compatibilidad, pero **no identifican el nuevo
artefacto GF** ni describen un build Volare. `open_pdks` conserva su nombre como
alias de stage. `pdk_builder` pasa a depender de `builder`, no de `magic`:
Ciel descarga y activa el artefacto, sin recompilarlo mediante Volare.

La interfaz pública sigue siendo `/opt/pdks/gf180mcuD`. Debe copiarse la raíz
Ciel completa con sus destinos de enlaces bajo
`/opt/pdks/ciel/gf180mcu/versions/`; copiar solo el enlace público no basta.
No mezclar decks nuevos con macros o modelos del antiguo open_pdks. El inventario
`tests/run/inventory/tools.json` identifica GF como Ciel y registra su raíz
resuelta y revisión esperada, separadas del pin legacy. La clave histórica
`OPEN_PDKS_NAME` se mantiene para consumidores del inventario, con
`legacy_inventory_key: true`, `manager: ciel` y `revision_key: GF180_PDK_COMMIT`;
no representa una instalación del antiguo open_pdks.

Los PDKs privados de los templates siguen separados en
`/opt/librelane-templates/pdks/<key>`. Preservar sus `flake.lock`; no actualizar
ramas ni resolver descargas durante el uso offline. Una coincidencia del nombre
del PDK no autoriza intercambiar entornos Nix o raíces privadas/globales.

La selección conserva `sak-pdk`/`set_pdk`, IHP como predeterminado y la SCL GF
`gf180mcu_fd_sc_mcu7t5v0`. Las SCL `gf180mcu_as_sc_mcu7t3v3` y
`gf180mcu_ocd_sc_rt12t3v3` son opciones solo donde estén instaladas y soportadas:
la primera no está completamente verificada en silicio y la segunda no está
verificada en silicio. Su presencia no constituye signoff.

## Protección IHP y herramientas compartidas

Se mantienen sin cambios:

- Template IHP `23c62045bb212175c20d8186a7ab308e15fba98c`.
- LibreLane privado IHP `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.
- PDK privado IHP `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`.
- PDK global IHP `cfc0e22b92306178ebb5a5bc4865afe3294654d0`.

Los contratos conservan el baseline histórico y permiten únicamente las tres
adiciones Ciel/GF y los tres cambios de revisión del template GF. Los demás pins,
incluido LibreLane global, permanecen protegidos; cualquier cambio compartido
adicional necesita justificación y una excepción explícita, no regenerar el
baseline. Congelar pins no demuestra compatibilidad del runtime reconstruido.

El fallo histórico IHP de 2701 marcadores Magic DRC está documentado en la
[investigación IHP](ihp-template-drc-investigation.md). No es un resultado de
0.3.1, ni una aprobación para omitir reglas o publicar una regresión. Repetir el
flujo y comparar evidencias; un fallo no se registra como PASS.

## Gates de aceptación (pendientes hasta aportar evidencia)

| Gate | Evidencia exigida | Qué no demuestra |
| --- | --- | --- |
| Contratos host | Salida de unittest, pins GF exactos, IHP congelado, grafo Ciel y ausencia de Volare GF | No ejecutan EDA ni validan artefactos descargados |
| Sintaxis y Docker | `bash -n`, `git diff --check`, check con argumentos del wrapper | No construyen una imagen |
| Stage GF | Log persistente de `gf180_pdk`, versión/ruta Ciel y revisión activa | No valida el runtime final ni IHP |
| Imagen final | ID/digest exacto, inventario, enlaces válidos y recursos analógicos | No equivale a suite completa |
| Suite habitual offline | `tests/run_all.sh`, resumen sin fallos no excluidos | Excluye flujos largos; exclusiones no son pases |
| GF global | MOSFET ngspice, PCells KLayout, extracción y smoke LibreLane | No valida el template privado |
| Templates completos | RTL → implementación → métricas/GDS no vacíos → GL, GF e IHP secuenciales | No sustituye precheck ni signoff |
| Precheck 1.7.4 | Entorno propio, PDK privado, caso positivo y negativo con salida comprobada | Un fixture negativo no valida fabricación |
| Reglas nuevas | Fixtures y resultados DCF.1a, DF.11, CO.5a/b, LDMOS y filler | La presencia de decks no prueba correcciones |
| Regresión IHP | Analógico, KLayout, extracción, template y alternancia IHP → GF → IHP | Pins iguales no prueban ausencia de contaminación |

Comandos de host desde la raíz del repositorio:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n build/*.sh images/*/install.sh images/final_structure/{configure,install}/*.sh tests/*.sh tests/*/*.sh
CHECK_ONLY=1 ./build/build-image.sh
git diff --check
# Construcción real: conservar logs; no ejecutarla como si fuera un check estático.
MAX_BUILD_JOBS=2 ./build/build-stage.sh gf180_pdk
```

Después de construir la imagen final, montar `tests/` en `/home/designer/tests`
y ejecutar dentro de **esa imagen**, con diseños separados y salidas en `tests/run/`:

```bash
bash /home/designer/tests/run_all.sh
bash /home/designer/tests/test_all_full.sh
```

Registrar separadamente ID de baseline y candidato, arquitectura, inventarios,
comandos, códigos de salida, exclusiones y rutas de logs. Repetir los flujos
largos secuencialmente en hosts con memoria limitada; no desactivar IR drop,
filler ni DRC para obtener éxito. Ningún build, prueba de contenedor o precheck
se declara aprobado por la mera existencia de estas notas.

## Publicación y rollback

No publicar hasta resolver o documentar explícitamente los bloqueos de aceptación
con resultados de la combinación final. La rama de publicación sería
`release/0.3.1`, con `release.version` coincidente; crearla o empujarla no forma
parte de esta preparación. La CI habitual no sustituye los gates largos y de
precheck anteriores. Conservar la imagen anterior por ID y sus pins; no borrar
PDKs, diseños ni caches para forzar la migración. Si GF o IHP regresan, detener
la publicación, corregir o aislar la incompatibilidad y repetir los gates afectados.
