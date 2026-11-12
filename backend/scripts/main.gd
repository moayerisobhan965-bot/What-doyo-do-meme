extends Node

func _ready():
	# Load Global
	var global = load("res://scripts/global.gd").new()
	add_child(global)
