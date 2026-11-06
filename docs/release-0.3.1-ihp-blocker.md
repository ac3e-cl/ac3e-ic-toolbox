# release 0.3.1: bloqueo IHP full, sin regresión observada por GF180

## Resultado

**IHP full sigue BLOQUEADO; no existe una corrección completa validada dentro
 del alcance permitido.** No se repitió el flujo completo ni se modificaron
producción, PDK, pins, locks o criterios de PASS. No se propone omitir checks.
KLayout DRC 0, LVS PASS y RTL PASS no equivalen a signoff. El runner no ejecutó
GL tras fallar el flujo; posteriormente se ejecutó de forma independiente sobre
el netlist de ese checkpoint y pasó 1 testcase, sin skips ni errores
(`evidence/gl-after-drc-failure.xml`). Ese resultado no cambia el FAIL físico.

- Candidata: `sha256:c193ad93a3b2735cb50d37da0497c029765211a9a366fda54a4838e906b7e3ae`.
- Baseline: `sha256:ea126a1a4c4a209134aad8bf90a21a4074201f20682c87a677f065f773e3c811`.
- Nuevo: `tests/run/librelane-template-ihp/run.9sE0hlZI/project/`.
- Baseline: `tests/run/librelane-template-ihp/run.9FsoK7JP/project/`.
- Contexto previo: [ihp-template-drc-investigation.md](ihp-template-drc-investigation.md).

## Comparación exacta, no solamente del total

Se parsearon ambos `librelane/runs/template/67-magic-drc/reports/drc.magic.rpt`
con Python `Decimal` y `Counter`, comparando multiconjuntos de
**(categoría literal, cuatro coordenadas)**, conservando duplicados.

| Categoría Magic | Baseline | Candidata | Delta |
| --- | ---: | ---: | ---: |
| TM2.bR, metal ancho/largo | 624 | 624 | 0 |
| Partial overlap/abutment between subcells | 1792 | 1792 | 0 |
| Cnt.c N-diffusion contact enclosure | 54 | 54 | 0 |
| Can't overlap those layers | 82 | 82 | 0 |
| Cnt.c SRAM exception | 149 | 149 | 0 |
| **Total** | **2701** | **2701** | **0** |

**Cero marcadores añadidos o retirados; coordenadas y multiplicidades iguales.**
Incluso los informes completos son idénticos byte a byte: SHA-256
`575f88b9d49a0d7f9ddf810c9b4000c0047918031d2ba3613d66b8b0398ec371`.
Las métricas finales de DRC/LVS coinciden; ambos tienen KLayout DRC 0 y
`design__lvs_error__count = 0`. El nuevo `evidence/flow.log` registra 2701 en
las líneas 8646, 10172 y 11328; el último es el error diferido final.
`evidence/rtl.xml` contiene `test_counter` sin fallo.

## Inputs IHP y herramientas efectivas

Inventario offline de **ambas imágenes por ID**, no del árbol de trabajo:

- Los 80 archivos inventariados (archivos bajo `libs.tech/magic`, dos GDS
  SRAM/IO y decks `*.drc` bajo `libs.tech/klayout`) tienen hashes iguales.
- Los cinco inputs contrastados previamente contra upstream —deck Magic DRC,
  CIF input, `read_sram_gds.tcl`, SRAM GDS e IO GDS— conservan en candidata los
  mismos hashes instalados y upstream del baseline. Esta investigación reutiliza
  `upstream-hashes.json`; no vuelve a descargar upstream.
- Manifiesto IHP idéntico: template `23c62045bb212175c20d8186a7ab308e15fba98c`,
  PDK aislado `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`, LibreLane
  `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.
- `evidence/flake.lock`, ejecutables registrados, versión LibreLane y
  `librelane/config.yaml` son idénticos. `67-magic-drc/config.json` solamente
  difiere en las rutas del identificador de corrida; normalizadas son iguales.
- Seis herramientas resueltas (Magic, KLayout, LibreLane, OpenROAD, Yosys y
  Python) tienen las mismas rutas Nix y SHA-256 de sus ejecutables/wrappers.
  Los archivos `.drv` inventariados de Magic/KLayout también son idénticos.

Herramientas de signoff de la plantilla, **no** las versiones globales Docker:

```text
/nix/store/7ar043dk92xygs16rwqivrzv8s467rg0-magic-vlsi-8.3.677/bin/magic
/nix/store/cw81fji9f4zsggnpi3h42c3smyzj4iq7-klayout-0.30.12/bin/klayout
/nix/store/zkadb62gnclvlbdnz0q97agj9qv9jrc2-magic-vlsi-8.3.677.drv
/nix/store/6avas7ibvbjp4lwr67djxdqbgv6n86i3-klayout-0.30.12.drv
```

SHA-256 del `.drv` Magic activo:
`3efa0d9eeca7b7ad48c4ce41aa96a336aa03076d561333ffe611b471e0e8b1f7`;
KLayout activo:
`0cbd4c08abb373f8655a4e7beff51a54d185e06ae99b27fd6dd4121f879aca92`.
Los textos `.drv` conservados identifican sus outputs. `nix-store --query
--deriver` no pudo abrir el lock de base de datos con rootfs read-only;
se compararon los `.drv` directamente, sin hacer escribible Nix. El primer
intento además encontró que no existe el alias global de `nix-store`; se
localizó el binario instalado bajo `/nix/store/*-nix-*/bin/nix-store`.

**Conclusión acotada:** este fallo IHP es la reproducción exacta del bloqueo
previo, no una regresión observada causada por la actualización GF180.
Esto no certifica toda la imagen ni todos los inputs IHP no inventariados.
El PDK relevante es el aislado bajo `/opt/librelane-templates/pdks/ihp`,
no el PDK global indicado por `IHP_PDK_REPO_COMMIT` en el entorno Docker.

## Miniprobes repetidos en candidata

Se reutilizó `targeted_drc.tcl` del baseline, siempre `drc style drc(full)`;
ningún deck fue editado. Corridas secuenciales, offline, rootfs read-only,
un CPU, límite duro 384 MiB RAM sin swap, timeout 55 s por probe. El precheck
GF positivo estaba activo al comenzar y no fue detenido ni modificado.

| Probe existente | Resultado Magic | Tiempo con arranque Docker |
| --- | --- | ---: |
| `pdn-original.gds`, gap 2 µm | 4 TM2.bR | 1.235 s |
| `pdn-spacing5.gds`, gap 5 µm | 0 | 0.987 s |
| IO `sg13g2_IOPadOut30mA`, flatglob upstream | 112 abutment + 2 overlap | 34.134 s |
| Mismo IO, añadiendo `gds flatglob *` | 0 | 3.439 s |

Los cuatro informes son idénticos byte a byte a sus miniprobes baseline.
Exit 0 de Magic no se trató como PASS: se exigió `PROBE_COUNT` y se leyeron
los informes. Los cero errores solamente corresponden a esos probes.

### Corrección mínima defendible y límite de alcance

1. **PDN:** el cambio geométrico local probado es aumentar el gap de 2 a 5 µm
   para los dos polígonos de 6 µm del probe. La regla TM2.bR no cambia. No
   valida cambiar globalmente `PDN_HSPACING`: faltan conexiones de alimentación
   de SRAM y cobertura de todos los marcadores del checkpoint.
2. **Pads:** el import flattening elimina los 114 errores del pad aislado sin
   tocar su GDS ni reglas. Es una dirección de corrección, no un patch de
   integración validado: `flatglob *` sobre todo IO no demuestra un flattening
   selectivo seguro del chip ni equivalencia de extracción/LVS.
3. **SRAM:** el probe baseline independiente sigue siendo evidencia de 95
   errores (27 Cnt.c + 68 SRAM exception) con los mismos inputs y herramienta.
   No se repitió por no necesitar otro trabajo potencialmente pesado. No hay
   corrección validada de importación/capas derivadas. Los 13 marcadores extra
   del primer SRAM en chip siguen sin explicación demostrada.

Por tanto **no hay un cambio mínimo completo autorizado y validado que haga
IHP full PASS**. Resolverlo requiere trabajo específico de integración de
PDN/importación/SRAM y validación física posterior, fuera de esta investigación
read-only. No es defendible convertir LVS/KLayout/RTL positivos en PASS del
flujo ni relajar reglas, cambiar pins o excluir Magic.

## Evidencia y reproducción exacta

Nueva evidencia ignorada bajo el `evidence/` de la corrida nueva:

- `compare_release_031.py`, `release-031-comparison.json`: categorías literales,
  comparación completa de marcadores, hashes y métricas.
- `inventory_ihp.py`, `{baseline,candidate}-inventory.json`,
  `release-031-inventory-comparison.json`: SHA-256, textos `.drv`, rutas
  resueltas y comparación con las cinco URLs upstream exactas del baseline.
- `run_miniprobes.py`, `release-031-miniprobes.json`: comandos Docker completos,
  flags, variables, tiempos, códigos de salida, conteos y hashes de informes.
- `release-031-{pdn-original,pdn-spacing5,pad-native,pad-flat}.{log,rpt}`.

Desde la raíz del repositorio:

```bash
E=tests/run/librelane-template-ihp/run.9sE0hlZI/project/evidence
python3 "$E/compare_release_031.py"
# Inventario: ambos IDs anteriores, misma invocación, montaje de evidencia RO:
docker run --rm --network none --memory 256m --cpus 1 --read-only \
  -v "$PWD/$E:/evidence:ro" --entrypoint /usr/bin/python3 IMAGE_ID \
  /evidence/inventory_ihp.py
# Solo los cuatro probes acotados descritos, nunca el flujo completo:
python3 "$E/run_miniprobes.py"
```

Fuentes: informes/config/métricas/XML de ambas corridas; bytes de ambas imágenes
inmutables; baseline `upstream-hashes.json`, `nix-magic-derivations.json`,
`targeted-results.json`, `sram-native.rpt`; informe de investigación previo.
No commits. Único documento nuevo: este; el resto de escrituras son evidencia
ignorada. Los cambios concurrentes del repositorio no fueron alterados.
