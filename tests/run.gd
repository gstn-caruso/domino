extends SceneTree

const CASE_NAME = "givenIdiomaEs_whenAbrirProyecto_thenMenuVisibleEnEspanol"
const LANGUAGE_CASE_NAME = "givenSistemaEn_whenAbrirMenu_thenCastellanoSinSelector"

var active_case := CASE_NAME


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	# El watchdog conserva la salida de error incluso si una corrutina se interrumpe.
	create_timer(5.0).timeout.connect(func() -> void:
		_fail("El test no terminó en cinco segundos; revisar errores de ejecución.")
		quit(1)
	)
	if not givenIdiomaEs_whenAbrirProyecto_thenMenuVisibleEnEspanol():
		quit(1)
		return
	print("PASS: " + CASE_NAME)

	active_case = LANGUAGE_CASE_NAME
	if not await givenSistemaEn_whenAbrirMenu_thenCastellanoSinSelector():
		quit(1)
		return
	print("PASS: " + LANGUAGE_CASE_NAME)
	quit(0)


func givenIdiomaEs_whenAbrirProyecto_thenMenuVisibleEnEspanol() -> bool:
	TranslationServer.set_locale("es")
	var scene_path: String = ProjectSettings.get_setting("application/run/main_scene", "")
	if scene_path.is_empty():
		return _fail("Falta la escena inicial: configurar application/run/main_scene en project.godot.")

	var initial_scene := load(scene_path) as PackedScene
	if initial_scene == null:
		return _fail("La escena inicial configurada no se puede cargar: " + scene_path)

	var menu := initial_scene.instantiate()
	root.add_child(menu)
	current_scene = menu
	if not _has_visible_play_button(menu):
		return _fail("Al abrir la escena inicial en es no hay un botón visible con el texto Jugar.")
	return true


func givenSistemaEn_whenAbrirMenu_thenCastellanoSinSelector() -> bool:
	TranslationServer.set_locale("en")
	if current_scene != null:
		current_scene.free()
	var scene_path: String = ProjectSettings.get_setting("application/run/main_scene")
	var menu := (load(scene_path) as PackedScene).instantiate()
	root.add_child(menu)
	current_scene = menu
	await process_frame

	var play_text := ""
	var play_disabled := false
	var status_text := ""
	var language_selector_visible := false
	for button in menu.find_children("*", "Button", true, false):
		if not button.is_visible_in_tree():
			continue
		if button.text == "MENU_PLAY":
			play_text = button.atr(button.text)
			play_disabled = button.disabled
		if button.atr(button.text) in ["Español", "English"]:
			language_selector_visible = true
	for selector in menu.find_children("*", "OptionButton", true, false):
		if selector.is_visible_in_tree():
			language_selector_visible = true
	for label in menu.find_children("*", "Label", true, false):
		if label.is_visible_in_tree() and label.text == "MENU_STATUS":
			status_text = label.atr(label.text)

	if play_text != "Jugar" or not play_disabled or status_text != "En preparación" or language_selector_visible:
		return _fail("Con sistema en inglés se espera Jugar deshabilitado y En preparación traducidos desde sus claves, sin selector. Observado: %s / %s; deshabilitado: %s; selector visible: %s." % [play_text, status_text, play_disabled, language_selector_visible])
	return true


func _has_visible_play_button(node: Node) -> bool:
	if node is Button and node.is_visible_in_tree() and node.atr(node.text) == "Jugar":
		return true
	for child in node.get_children():
		if _has_visible_play_button(child):
			return true
	return false


func _fail(message: String) -> bool:
	printerr("FAIL: " + active_case + " — " + message)
	return false
