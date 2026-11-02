# Plan de reducción de tamaño de la imagen

## Alcance y evidencia

El análisis y las referencias de líneas siguientes describen el baseline previo
al recorte; algunos archivos SKY citados ya se retiraron en `dev/no-sky`.

### Estado de implementación en `dev/no-sky`

- SKY general y plantilla privada retirados de la composición de la única imagen.
- La exclusión de SKY es temporal para analizar espacio antes de reincorporarlo
  en una versión posterior. Sus tests, datos y helpers se conservan: las suites
  normal y completa los reportan como `EXCLUDED`; los tests host del adaptador
  llevan `unittest.skip`. No se borran ni se contabilizan como aprobados.
- IHP, GF y LibreLane global conservados, sin cambiar sus revisiones.
- ORFS sin descarga de submódulos fuente ni historial Git en el árbol distribuido.
- CPython 3.11.18 añadido en `/opt/python`, con paquetes EDA en `/opt/eda-venv` y
  precedencia para el usuario. Ubuntu 22.04 y `/usr/bin/python3` permanecen intactos;
  las herramientas Nix y sus intérpretes aislados no se reemplazan.
- Contratos host y sintaxis verificados; falta construir y ejecutar la imagen.
  El intento con `BUILD_IMAGE_TAG=isaiash/ac3e-ic-toolbox:dev-no-sky` falló por
  permisos del socket Docker antes de ejecutar stages. No se han creado commits.
  No se declara todavía ningún ahorro real del build nuevo.

El resultado previsto es **una sola imagen**, conservando IHP y GF y priorizando
la retirada de SKY. No se proponen variantes por PDK, imágenes complementarias ni
descargas diferidas como sustituto de reducir la imagen distribuida.
El criterio de prioridad es ahorrar del orden de **1 GiB o más por intervención**,
no acumular limpiezas de unos pocos MB. No se cambian los pins para adelgazar la imagen.

Se revisaron el Dockerfile, el manifiesto, los instaladores de PDKs y LibreLane,
la configuración de ejecución y los contratos/tests relacionados.

El daemon Docker local no fue accesible: permiso denegado sobre su socket y
`sudo -n` requiere contraseña. Por tanto, **no se midió la imagen local de 11 GB**.
Como alternativa se consultaron el manifiesto OCI y el historial de configuración
de la imagen pública `docker.io/isaiash/ac3e-ic-toolbox:0.2.0`, plataforma linux/amd64:

- Manifiesto de plataforma: `sha256:340fa40e9953e52d0623a126b38a19faf7541f00e09ff6a20a7394481969d4b4`.
- Configuración: `sha256:b8e85480371741df6418fc9675c376692797fd6a741a0484e719dcaa7fb56977`.
- Fecha de creación registrada: `2026-10-18T14:34:34.937636488Z`.
- Suma de blobs de capas comprimidas: **12 932 857 565 bytes = 12,045 GiB**.

Esta referencia publicada no debe identificarse automáticamente con la imagen
local mencionada. Tampoco se deben comparar GB decimales, GiB, tamaño comprimido,
sistema de archivos visible y tamaño acumulado de capas como si fueran equivalentes.

### Bloques grandes medidos en el registro

| Instrucción / contenido | GiB comprimidos | Qué demuestra |
| --- | ---: | --- |
| Instalación de las tres plantillas LibreLane | 5,155 | Es el mayor bloque; incluye entornos Nix y PDKs privados juntos, no solo SKY. |
| Copia de `/opt/pdks` desde `open_pdks` | 2,016 | SKY y GF generales juntos. No permite atribuir 2 GiB a SKY solamente. |
| Copia de `/opt/OpenROAD-flow-scripts` | 1,869 | ORFS completo es una oportunidad real, no una optimización de MB. |
| Instalación del LibreLane global con Nix | 1,471 | Un cuarto entorno LibreLane, además de los tres de las plantillas. |

Son pesos actuales de capas, **no ahorros garantizados de limpiezas parciales**.
Los ahorros de opciones que comparten Nix no son aditivos: el store ya comparte
rutas idénticas; distintas revisiones y derivaciones pueden necesitar rutas distintas.

## Análisis comparativo de las plantillas: coste marginal, no suma de tamaños

Se descargaron los `flake.lock` y `flake.nix` de IHP y GF en los commits exactos
de `manifest.json`, el lock del LibreLane global y se compararon con el adaptador
SKY del repositorio. Se verificó igualdad de los objetos `locked`, incluido
`narHash`, no solamente los nombres de los inputs.

| Input | IHP | GF | SKY | Global |
| --- | --- | --- | --- | --- |
| nixpkgs | `9b696460ac78…` | `9b696460ac78…` | **`b3aad468604d…`** | `9b696460ac78…` |
| nix-eda | `8a8e673d5327…` | `854dd782733d…` | `8f990fb77529…` | `e0126a50c541…` |
| Ciel | `1d2526e67a06…` | `1d2526e67a06…` | `afcb23d36861…` | `6978e6b37970…` |
| devshell | `a67c0f87b63b…` | `a67c0f87b63b…` | `255a2b1725a2…` | `255a2b1725a2…` |

Fuentes reproducibles para esta comparación:

- [Lock IHP](https://raw.githubusercontent.com/IHP-GmbH/ihp-sg13-librelane-template/23c62045bb212175c20d8186a7ab308e15fba98c/flake.lock).
- [Lock GF](https://raw.githubusercontent.com/wafer-space/gf180mcu-project-template/33e4b5ecc9faac82787fa7cb205f08377e27b912/flake.lock).
- [Lock global](https://raw.githubusercontent.com/librelane/librelane/ca6adb1e2982cd75445a68b632d461213d8ca421/flake.lock).
- SKY: `images/librelane/sky/flake.lock` y `flake.nix`.

### Qué se comparte y qué no

**IHP y GF aprovechan una misma base de paquetes**, también utilizada por el
LibreLane global. Comparten exactamente nixpkgs, Ciel y devshell; sus shells
solicitan utilidades y simuladores similares. Esto permite compartir derivaciones
idénticas de la base. No demuestra identidad de toda su clausura: tienen distintos
LibreLane y nix-eda. Como comprobación adicional, las recetas `nix/klayout.nix`
de ambos nix-eda tienen el mismo blob Git, pero `nix/yosys.nix` difiere. Incluso
una receta idéntica puede producir otra derivación si cambia un input u overlay.

**SKY es el conjunto menos alineado con el resto:** usa otro nixpkgs, otro
nix-eda y otro Ciel. Además, el adaptador fuerza Python 3.11 y una derivación
KLayout 0.29.12, modifica los wrappers Python de Yosys/OpenROAD e incluye un venv
con requirements propios de Tiny Tapeout (`images/librelane/sky/flake.nix:16-45`
y `bootstrap.sh:18-23`). Esto incorpora una segunda familia de dependencias con
menor posibilidad de reutilización. SKY no es totalmente independiente: por
ejemplo, su devshell coincide con el global, y algunas rutas podrían compartirse.

**Conclusión para decidir el recorte:** SKY es el primer candidato a retirar por
su coste marginal estructuralmente menos aprovechado. Mantener IHP y GF conserva
dos tecnologías sobre una base común. No hay evidencia suficiente para afirmar
que el total exclusivo de SKY en bytes ya está demostrado como el mayor: un
PDK GF grande podría alterar el ranking aunque su entorno comparta más paquetes.
La capa conjunta de 5,155 GiB no permite separar las tres contribuciones.

### Medición necesaria para cerrar el ranking en bytes

Para cada plantilla T, obtener su clausura de rutas Nix y restar la unión de las
rutas requeridas por **todos los demás roots conservados**, incluido LibreLane
global y el propio Nix. Sumar `narSize` de las rutas exclusivas y, por separado,
los bytes de su PDK privado, checkout y venv fuera de Nix. No sumar tres tamaños
de clausura completos, ni confundir fuentes de flakes con clausuras de ejecución.

El informe debe mostrar para SKY, IHP y GF: clausura total, bytes compartidos,
bytes exclusivos, PDK privado y recursos auxiliares. La retirada del SKY general
se mide aparte, pues no pertenece a la plantilla. `narSize` permite comparar
contenido Nix, pero el ahorro distribuido definitivo lo confirma el build y su
manifiesto comprimido. Esta medición requiere acceso a la imagen/store existente;
el socket Docker sigue sin permisos y no hay Nix local disponible.

## 1. Retirar SKY de la única imagen, conservando IHP y GF

La intervención prioritaria es omitir Tiny Tapeout SKY junto con su adaptador,
venv, PDK privado y dependencias Nix exclusivas. Para maximizar el recorte de SKY,
el plan también contempla no distribuir su PDK general. Son dos ahorros distintos:
el primero evita el entorno menos compartido; el segundo retira datos de PDK.

Actualmente hay dos instalaciones independientes:

- SKY general: `Dockerfile:242-248,258-262,492`; el enlace público apunta al backing
  de Volare. `images/pdks/install_sky130.sh:24-29` ya elimina SKY130B y las rutas
  `.build`/`.source` indicadas. No contabilizar nuevamente esa limpieza.
- SKY privado: `images/librelane/install.sh:26-47` crea adaptador, venv, entorno Nix
  y PDK Ciel bajo `/opt/librelane-templates`.

Cambios previstos, sin crear mecanismos de variantes:

1. Ajustar el conjunto soportado de plantillas a IHP/GF en manifiesto e instalador.
   Hoy el instalador exige exactamente `ihp`, `gf`, `sky` (`install.sh:12,20`).
2. Retirar la rama SKY del instalador y los recursos del adaptador que dejen de
   tener consumidores. Mantener intactos los locks y PDKs privados de IHP/GF.
3. Hacer que la composición final de `open_pdks` no dependa de `sky130_pdk` ni copie
   su backing. No quitar Magic: también sirve para los PDKs conservados.
4. Excluir SKY desde el principio del build. No instalarlo para borrarlo después,
   ni hacer GC en una capa posterior esperando recuperar capas ya distribuidas.
5. Actualizar launcher, inventario, documentación y tests para anunciar IHP/GF como
   conjunto soportado. No ocultar fallos ni afirmar cobertura SKY ya retirada.
6. Validar los flujos IHP/GF y medir el ahorro marginal total, separando plantilla
   SKY de PDK general SKY. No atribuirle la capa completa de las tres plantillas.

Efecto funcional explícito: la única imagen deja de incluir soporte PDK SKY y
Tiny Tapeout SKY listo para usar. Conserva IHP/GF y sus entornos aislados. La
retirada está implementada en el código; aún falta validarla en la imagen construida.
No sustituir silenciosamente PDKs privados por los generales: sus pins difieren.

## 2. ORFS de ejecución sin repositorios de compilación

**Objetivo:** eliminar del orden de GB de fuentes e historial que hoy se distribuyen
sin ser necesarios para usar los binarios ya compilados.

Evidencia:

- `images/orfs/install.sh:7-17` clona ORFS y todos sus submódulos recursivamente.
- `images/orfs/install.sh:19-22` deja comentada la eliminación de `.git`.
- `Dockerfile:516` copia el árbol completo al runtime.
- El OpenROAD ejecutable ya se instala por separado (`Dockerfile:515`), al igual
  que Yosys (`Dockerfile:514`).
- Se consultaron los árboles Git upstream de las revisiones exactas: ORFS
  `40674dd5cf48db6dc9028d6ab5a98f107208f5bb` referencia OpenROAD
  `83ff25699764e58118fc536056a34326b22cba8f`. Solo los blobs versionados de ese
  submódulo OpenROAD suman **1,340 GiB lógicos**, antes de su `.git` y de sus
  propios submódulos. Esto no es una estimación del tamaño comprimido.
- En el ORFS principal, `flow/platforms` suma 0,738 GiB y `flow/designs` 0,267 GiB
  lógicos. No son todos basura: contienen plataformas y ejemplos utilizables.

Cambios previstos:

1. Revisar usos de `tools/` y Git en los targets ORFS soportados, no solo el test de síntesis.
2. Preparar un árbol de distribución ORFS en su stage, sin inicializar/copiando
   fuera los submódulos de compilación OpenROAD, Yosys y yosys-slang cuando los
   targets soportados usen los ejecutables instalados. Conservar los recursos de
   ejecución que esa revisión realmente referencie.
3. Excluir los metadatos Git, incluidos los de submódulos, **antes del COPY final**.
   Registrar los SHAs como metadatos de procedencia en lugar de conservar el historial.
4. Conservar inicialmente Makefiles, `flow/scripts`, `flow/util` y plataformas.
   No recortar bibliotecas por extensión. Si se decide retirar plataformas o
   ejemplos completos, hacerlo como una decisión de funcionalidad separada.

Validación: `tests/digital/test-orfs.sh`, más un flujo físico completo pequeño
sobre las plataformas que se declare soportar. El test actual solo prueba síntesis
Nangate45 y no valida por sí solo todo ORFS. Medir el nuevo COPY y el delta total.

## 3. LibreLane global: conservar inicialmente; evaluar solo su coste exclusivo

El perfil global se instala en `Dockerfile:625-628` y las plantillas en
`Dockerfile:640-642`. El launcher de plantillas ejecuta su propio entorno y PDK
(`images/librelane/librelane-template:30-37`), no necesita resolver el comando
LibreLane desde el perfil global.

La política base del plan es conservar LibreLane global junto con las plantillas
IHP/GF en la misma imagen. Su nixpkgs coincide con ambas: su capa de **1,471 GiB**
no equivale a otros tantos GiB recuperables al retirarlo, porque IHP/GF podrían
tener que incorporar parte de esas rutas. No se propone eliminarlo por su peso
bruto. Solo reconsiderarlo si se mide al menos 1 GiB exclusivo y se acepta perder
el perfil global; nunca convertirlo en otra imagen ni reemplazar locks de IHP/GF.

No intentar hacer compartir bibliotecas Ubuntu a binarios Nix a través de PATH,
PYTHONPATH o LD_LIBRARY_PATH. No unificar locks ni cambiar versiones sin un trabajo
separado de compatibilidad. El pin y aislamiento actuales son deliberados.

Si se retira el perfil global, revisar precedencia PATH, activación Nix y pruebas
que hoy esperan el comando global. Ejecutar pruebas digitales nativas y flujos
completos de las plantillas conservadas; respetar el fallo upstream IHP documentado,
sin convertirlo en PASS ni desactivar DRC para adelgazar la imagen.

## 4. Residuos y fuentes Nix/PDK — promoción condicionada a medir al menos 1 GiB

No hay evidencia suficiente para prometer GB extra por un `find ... -delete`.
La investigación debe concentrarse dentro de los bloques grandes medidos:

- GF general conserva backing y source caches expresamente
  (`images/pdks/install_gf180mcu.sh:30-38`). Inventariar tamaños reales y recorrer
  enlaces transitivamente antes de considerar sobrantes. GF180D depende del
  backing A; `images/pdks/gf180_integrity.py` y `tests/test_gf_cleanup.py` protegen
  precisamente ese caso. No borrar A/B/C o caches por su nombre.
- Para Nix, identificar la unión de clausuras de todos los perfiles/roots que
  permanezcan: perfil de Nix, perfil global, perfiles GF/IHP y rutas referenciadas
  por los scripts de activación. No conservar roots de SKY retirados.
  Comparar con el store total e inspeccionar roots y caches.
- Solo si hay al menos 1 GiB realmente prescindible, preparar un stage de exportación
  de las clausuras necesarias, su registro Nix y recursos de ejecución, o instalar
  y limpiar dentro del mismo RUN. Validar activación sin red, UID arbitrario y que
  Nix siga operativo. No borrar derivaciones/fuentes activas a ciegas.
- Ejecutar GC en una capa posterior no elimina bytes de capas inferiores.
  No usar `nix-store --optimise` como sustituto de excluir contenido: hardlinks
  entre capas no garantizan reducción de los blobs distribuidos.

Esta fase no cuenta como ahorro obtenido ni como cambio aprobado hasta medirla.

## Secuencia y criterios de aceptación

1. **Baseline local:** identificar tag/ID exacto de los 11 GB; medir con
   `docker image inspect`, `docker history --no-trunc`, `du -x`/`du -x --apparent-size`
   sin seguir enlaces por duplicado y consultas de clausuras Nix. Guardar bytes,
   plataforma, pins y métrica. El manifiesto remoto anterior sirve como referencia,
   no reemplaza ese baseline local.
2. **Atribución por plantilla:** calcular el coste marginal SKY/IHP/GF como se
   describe arriba; registrar qué parte es entorno y qué parte es PDK privado.
3. **Primer cambio:** excluir SKY privado y su entorno; medir. Excluir también el
   SKY general como segundo paso del mismo recorte; medir por separado. Verificar
   ausencia de dependencias de build y contenido, no solo de enlaces públicos.
4. **Segundo cambio:** ORFS runtime-only, conservando los recursos utilizados.
5. **Solo con evidencia:** residuos Nix/PDK de escala GB; el perfil LibreLane global
   no se retira por defecto ni se cambia la compatibilidad de IHP/GF para deduplicar.
6. Validar revisiones sucesivas del mismo producto. Un tag temporal de comprobación
   no constituye una variante distribuida: el resultado es una única imagen con
   IHP/GF. No sobrescribir/publicar el tag estable antes de validar. Comparar cada
   delta y el combinado con la misma métrica; no sumar estimaciones.
7. Ejecutar comprobaciones estáticas, tests de contratos actualizados y la suite
   de integración para capacidades conservadas. Ejecutar explícitamente los flujos
   largos pertinentes: no pertenecen todos a la suite habitual. Para pruebas de
   layout dependientes de SKY, crear cobertura equivalente con PDK conservado o
   marcar la capacidad retirada; no afirmar que se validó SKY en una imagen sin él.
8. Aceptar intervenciones de tamaño solo cuando el delta real alcance el orden de
   GB y no rompa funcionalidades declaradas. Registrar también tamaño comprimido
   si importa descarga/distribución.

## Fuera de prioridad

No dedicar esta tarea a cambiar Ubuntu por Alpine, quitar editores, docs pequeñas,
bytecode o limpiar builders que nunca se copian al runtime. Los instaladores ya
limpian varios temporales y caches. La copia de IHP y su `chown` posterior duplican
unos **0,152 GiB comprimidos** cada uno en la referencia: es un problema de capas,
pero corregir ese `chown` no alcanza el umbral solicitado. Tampoco considerar que
`strip` posterior al COPY ahorra lo que hubiera ahorrado hacerlo antes del COPY.
Estas observaciones no justifican desviar el plan de ORFS, PDKs y entornos LibreLane.
