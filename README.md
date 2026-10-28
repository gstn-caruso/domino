# Dominó

Un dominó calmo, sin anuncios, complejidad innecesaria ni sobresaltos, para
Android (teléfonos y tablets) y Linux. Proyecto en **Godot 4.7.2 / GDScript**;
React Native quedó descartado. [Repositorio público](https://github.com/gstn-caruso/domino).

**Estado actual: preview del menú solo en castellano, sin selector de idioma.**
«Jugar» está deshabilitado y muestra «En preparación». Todavía no hay partida,
sonidos ni CPU. No se promete una experiencia de juego terminada.

## Desarrollo en Linux

Requisitos: Godot 4.7.2, Python 3.11 o posterior, GNU Make y `dpkg-deb` para
empaquetar. Las pruebas rápidas no requieren Java, Android SDK ni plantillas.

```sh
export GODOT_BIN=/ruta/a/Godot_v4.7.2-stable_linux.x86_64
make test             # importa recursos; 2 casos UI y 6 casos Python
make run              # abre el menú; necesita sesión gráfica
make verify ACTIONLINT=/ruta/a/actionlint  # mismas pruebas + validación del workflow
```

`GODOT_BIN` acepta una ruta absoluta (por defecto, `godot` en PATH). Se verificó
localmente el motor en `$HOME/.cache/domino-tools/godot-4.7.2/` y actionlint 1.7.12.
El descubrimiento Python usa los `load_tests` existentes: no es una suite vacía.

Para exportar ambos instaladores se necesitan además Java 17 (`JAVA_HOME`), Android
SDK (`ANDROID_HOME`, o `ANDROID_SDK_ROOT` como alternativa en Make), `platform-tools`,
`build-tools;35.0.1`, `platforms;android-35`, licencias SDK aceptadas y las plantillas
oficiales 4.7.2 en `~/.local/share/godot/export_templates/4.7.2.stable/`:
`linux_release.x86_64`, `android_debug.apk`, `android_release.apk` y `version.txt`.
No se usa Gradle ni NDK. En Ubuntu, `desktop-file-utils` permite validar el lanzador.

```sh
export JAVA_HOME=/ruta/al/jdk-17
export ANDROID_HOME=/ruta/al/android-sdk
make build VERSION=0.1.7 VERSION_CODE=7 BUILD_DIR=builds/0.1.7
make test-exports     # opt-in: exportaciones reales, mucho más lento
```

`VERSION_CODE` es un entero positivo compatible con Android. El constructor usa un
proyecto temporal y **rechaza sobrescribir instaladores existentes**; elegí un
directorio o versión nuevos. Las herramientas no se instalan en el sistema local.
La preparación reproducible de CI está en `.github/actions/setup-godot/action.yml`
(motor y plantillas) y en el paso «Dependencias de exportación» de
`.github/workflows/delivery.yml` (Android command-line tools 19.0): descargas
oficiales con SHA256 fijado, SDK aislado en `$RUNNER_TEMP/sdk`, sin depender de
Android preinstalado ni usar una caché enorme.

## Instalación de la preview

Descargá **ambos instaladores y SHA256SUMS** desde una
[GitHub Release](https://github.com/gstn-caruso/domino/releases), en la misma carpeta:

```sh
sha256sum -c SHA256SUMS
sudo apt install ./domino_0.1.N_amd64.deb  # reemplazar N por la versión descargada
# Lanzar «Dominó» desde el menú del escritorio o con /usr/games/domino.
adb install domino-0.1.N.apk             # Android: USB debugging + platform-tools
```

El `.deb` es para Linux **amd64**, con entorno gráfico compatible con Godot/OpenGL.
El APK incluye **arm64-v8a y armeabi-v7a**; también puede abrirse desde el dispositivo
habilitando la instalación desde esa fuente. **Es debug, no una entrega para Play.**
Cada construcción genera una firma efímera: Android puede exigir desinstalar la
preview anterior antes de instalar la siguiente, perdiendo sus datos locales.
No guardes claves privadas ni contraseñas en el repositorio.

## Entregas automáticas

`delivery.yml` ejecuta **tests → build → publish** en Ubuntu 24.04. Las PR prueban,
construyen y adjuntan APK + `.deb` + manifest como artefacto de Actions, pero **jamás
publican** ni reciben `contents: write`. Solo el trabajo de publicación de un push
a `main` tiene escritura. Usa el mismo SHA y los instaladores de esa ejecución,
validados con `apksigner`, `aapt`, `dpkg-deb` y arranque headless del ejecutable
extraído del `.deb`. El arranque gráfico y dispositivos físicos no se verifican ahí.

Cada ejecución genera `0.1.<github.run_number>` y el mismo Android versionCode;
el tag es `v0.1.N`. Una PR también consume números, por lo que puede haber saltos.
Un rerun conserva la versión. No se edita la versión a mano en una PR, no se depende
de que un tag creado con `GITHUB_TOKEN` dispare otro workflow y no hay cancelación
global de merges pendientes. Las acciones oficiales están fijadas a SHA.

Tras pasar pruebas y construcción, `publish.py` verifica ambos instaladores y el
tag, crea un **borrador prerelease**, adjunta ambos y SHA256SUMS y recién entonces
lo hace visible. Si falla tests/build, no se ejecuta publicación ni se crea un tag.
Un fallo de red durante publicación puede dejar tag/borrador: no hay transacción
atómica entre GitHub y la subida; nunca se promete rollback automático.

**Recuperación manual, sin borrados:** inspeccionar el run, su SHA, tag, borrador
y adjuntos. Si no existe release, puede reintentarse con los artefactos de ese
mismo run; un tag previo debe apuntar directamente al SHA correcto. El publicador
**rechaza toda release existente, incluso borradores**, y no la reanuda ni pisa.
Ante un borrador, una persona autorizada debe verificar/completar ambos instaladores
y sus checksums antes de publicarlo manualmente; si ya se publicó, no reejecutar la
publicación. Un tag conflictivo requiere investigación, no moverlo ni borrarlo.
Un nuevo push a main obtiene otra versión; conservar la evidencia del fallo anterior.

## Idiomas y próximos pasos

Los textos están en `translations/menu.csv` con claves `MENU_` y solo catálogo ES.
Godot importa el CSV y genera `*.translation`; se conservan `*.uid` y metadatos
`*.import`, no `.godot/`. El menú abre siempre en castellano, también con el sistema
en otro idioma, y no tiene selector. La internacionalización queda preparada para
un futuro inglés, todavía no habilitado; no hay persistencia de idioma.

Roadmap breve: reglas de dominó doble-seis con pozo; CPU difícil con fuerza medible,
sin acceso a fichas ocultas, cuando se pida; audio suave opcional, apagado por
defecto; adaptación y verificación en teléfonos/tablets. Cada incremento debe
mantener el juego simple y tranquilo.

## Licencias

Todavía **no se ha elegido una licencia para el código propio**. Que el repositorio
sea público no concede una licencia de reutilización. No se añade una sin autorización.
Godot Engine es software de sus autores y colaboradores bajo licencia MIT:
[licencia y atribuciones](https://godotengine.org/license/) y
[obligaciones al distribuir](https://docs.godotengine.org/en/stable/about/complying_with_licenses.html).
Los avisos completos de Godot **4.7.2-stable** y sus terceros se conservan sin
cambios en `third_party/GODOT_LICENSE.txt` y `third_party/GODOT_COPYRIGHT.txt`,
obtenidos de los archivos oficiales
[LICENSE.txt](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/LICENSE.txt) y
[COPYRIGHT.txt](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/COPYRIGHT.txt).
Ambos acompañan a los binarios: en `assets/third_party/` dentro del APK y en
`/usr/share/doc/domino/` dentro del `.deb`.
