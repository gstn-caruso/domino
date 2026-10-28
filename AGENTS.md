# Dominó

- Objetivo: dominó calmo, sin anuncios ni sobresaltos. Godot 4.7.2/GDScript;
  Android teléfonos/tablets y Linux; textos ES/EN. React Native descartado.
- Estado: solo menú bilingüe; Jugar deshabilitado. No atribuir partida, CPU o audio.
- Mantener textos en `translations/menu.csv`. Conservar `*.uid` y `*.import`;
  no versionar `.godot`, traducciones generadas, instaladores ni secretos.
- Cambios de comportamiento: TDD, un caso observable a la vez; separar estructura.
  No alterar pruebas para hacer pasar producción. Nada de frameworks especulativos.
- Pruebas rápidas: `make test GODOT_BIN=/ruta/al/godot`. Verificación adicional:
  `make verify ACTIONLINT=/ruta/a/actionlint`. Exportación real opt-in:
  `make test-exports` con GODOT_BIN, JAVA_HOME (17) y ANDROID_HOME configurados.
- Construcción: `make build VERSION=X.Y.Z VERSION_CODE=N BUILD_DIR=builds/X.Y.Z`.
  No sobrescribe salidas; no requiere Gradle ni NDK. Ver README para dependencias.
- Trabajar en rama, preservar cambios ajenos y revisar estado antes de escribir.
  Commits/push/PR/merge requieren autorización; nunca escribir directamente en main.
  Pasos estructurales separados: `refactor: ...` o `refactor(tidy): ...`.
- Cada merge a main entrega APK + .deb + SHA256SUMS + tag + prerelease mediante
  `delivery.yml`. Versión automática 0.1.run_number; no cambiarla manualmente.
  PR sin publicación ni permisos de escritura. Revisar antes de push/merge.
- La firma APK actual es debug efímera. No introducir claves reales ni una licencia
  del código propio sin autorización. Reportar resultados ejecutados y límites.
