# Validación local — release/0.3.1

## Imagen candidata

- Imagen: `isaiash/ac3e-ic-toolbox:0.3.1`
- ID: `sha256:c193ad93a3b2735cb50d37da0497c029765211a9a366fda54a4838e906b7e3ae`
- Tamaño informado por Docker: `41244826951` bytes.
- Rama local: `release/0.3.1`. El estado de validación es independiente del
  commit/push posterior; no constituye aprobación ni publicación de la imagen.
- Build final: salida 0, proceso `proc_90e6a37deb50`.

## Evidencia obtenida

- 215 tests host: OK, 2 omitidos; `build/_build_logs/host-0.3.1.log`.
- Sintaxis Bash, chequeo Docker con manifiesto y `git diff --check`: correctos.
- Arranque sin red de la candidata: Ciel 3.1.0, launcher precheck con corrección
  de run-tag y activación precheck instalados; GF resuelve a la revisión
  `792ef67037d74c8c51811eab3ce23cf793491296` bajo la raíz Ciel.
- Pruebas preliminares en overlay de referencia (NO sustituyen la candidata):
  selección de nuevas SCL, alternancia IHP/GF/IHP, entorno, MOSFET, PCells y flujo
  LibreLane GF completos pasan; `build/_build_logs/gf-runtime-probe-tests.log`.
- 19 casos de regresión de reglas reales en ese overlay pasan; incluye controles
  negativos y comparación con golden upstream LDMOS. Evidencia en
  `tests/run/gf180-rules/validation.log`. No es signoff de fabricación.

## Gates de integración (estado actual)

- Suite habitual offline en el ID candidato: **PASS**, salida 0: 26 PASS,
  0 FAIL y 7 exclusiones explícitas, 33 entradas en total. Resumen:
  `tests/run/summary.tsv`; log `build/_build_logs/release-0.3.1-regular.log`.
  Incluye pruebas nuevas Ciel, precheck negativo y reglas GF, y regresiones IHP.
- Activación de templates IHP y GF sin red con UID/GID `12345:23456`: PASS,
  HOME writable, LibreLane ejecutable y PDK privado accesibles.
- Flujos completos: GF **PASS**, incluida RTL, implementación completa, métricas,
  GDS y gate-level. Evidencia: `tests/run/librelane-template-gf/run.Gsz2E2kF/project/evidence`.
- IHP **FAIL** tras completar 82 etapas: Magic DRC 2701, KLayout DRC 0, LVS PASS.
  Comparación completada: el informe DRC coincide byte a byte con baseline;
  los 2701 marcadores, coordenadas y duplicados son idénticos. También coinciden
  los 80 inputs IHP inventariados y las herramientas aisladas comparadas. No hay
  regresión observada en este fallo. Detalle: `release-0.3.1-ihp-blocker.md`.
  Evidencia: `tests/run/librelane-template-ihp/run.9sE0hlZI/project/evidence/flow.log`.
  La suite larga termina con salida 1: 1 PASS, 1 FAIL, 1 exclusión SKY.
  Resumen: `tests/run/full/summary.tsv`; log `build/_build_logs/release-0.3.1-full.log`.
- IHP gate-level ejecutada independientemente sobre el netlist de ese checkpoint:
  1 testcase PASS, sin errores ni skips, XML `evidence/gl-after-drc-failure.xml`.
  Se creó un enlace `final` únicamente en la copia desechable del test. Este
  resultado funcional NO cambia el FAIL DRC del flujo completo.
- Precheck completo positivo sobre el GDS generado por GF: **INTERRUMPIDO al
  cerrar el trabajo por solicitud del usuario**, después de más de tres horas;
  había llegado a KLayout DRC, reglas DF.3c. No se declara PASS ni signoff.
  Log conservado: `build/_build_logs/release-0.3.1-precheck-positive.log`.
- Contenedor del precheck detenido y ausencia de contenedores de validación de
  esta release comprobada. Imagen y evidencia conservadas; no se borraron caches.

## Cierre

Trabajo cerrado por solicitud del usuario. Imagen construida y rama preparada,
pero **release no aprobada**: IHP full reproduce un bloqueo DRC preexistente y
el precheck positivo completo quedó incompleto. No se modificaron reglas ni
exclusiones para convertir fallos en PASS. No se hizo commit, push ni publicación.
Los cambios quedan en el árbol de trabajo de `release/0.3.1`.

La duración principal provino del build nativo/Nix, del flujo GF completo
(3 h 44 min 20 s), del flujo IHP (1 h 11 min 20 s) y del precheck completo
interrumpido tras más de 3 h. La ejecución usó un worker/thread para los flujos
pesados para limitar presión de memoria; no fue una prueba reducida.
