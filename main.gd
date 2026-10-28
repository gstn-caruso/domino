extends Control


func _select_language(locale: String) -> void:
	TranslationServer.set_locale(locale)
