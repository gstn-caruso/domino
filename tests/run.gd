extends SceneTree

const CASE_NAME = "givenIdiomaEs_whenAbrirProyecto_thenMenuVisibleEnEspanol"
const LANGUAGE_CASE_NAME = "givenMenuEs_whenElegirEn_thenTextoVisibleEnIngles"

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
	if not await givenMenuEs_whenElegirEn_thenTextoVisibleEnIngles():
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


func givenMenuEs_whenElegirEn_thenTextoVisibleEnIngles() -> bool:
	TranslationServer.set_locale("es")
	if current_scene != null:
		current_scene.free()
	var scene_path: String = ProjectSettings.get_setting("application/run/main_scene")
	var menu := (load(scene_path) as PackedScene).instantiate()
	root.add_child(menu)
	current_scene = menu
	await process_frame

	var english_button: Button = null
	for button in menu.find_children("*", "Button", true, false):
		if button.is_visible_in_tree() and button.atr(button.text) == "English":
			english_button = button
			break
	if english_button == null:
		return _fail("Falta un botón visible English para elegir el idioma desde el menú.")
	if english_button.disabled or english_button.focus_mode == Control.FOCUS_NONE:
		return _fail("El botón English debe estar habilitado y ser accesible por teclado.")

	english_button.grab_focus()
	var enter := InputEventKey.new()
	enter.keycode = KEY_ENTER
	enter.pressed = true
	root.push_input(enter)
	enter.pressed = false
	root.push_input(enter)
	await process_frame

	var play_visible := false
	for button in menu.find_children("*", "Button", true, false):
		if button.is_visible_in_tree() and button.atr(button.text) == "Play":
			play_visible = true
	var status_visible := false
	for label in menu.find_children("*", "Label", true, false):
		if label.is_visible_in_tree() and label.atr(label.text) == "In preparation":
			status_visible = true
	if not play_visible or not status_visible:
		return _fail("Tras elegir English deben verse Play e In preparation en el menú.")
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
