"""Module for setting particle properties."""

import moderngl

def setUniformsFromOptions(program: moderngl.Program, options):
	"""Sets particle shared particle settings.
	
	:param program: Shader program to configure.
	:type program: :class:`moderngl.Program`
	:param options: Hydra options for the entity being simulated."""
	program["acceleration"] = options.part_acceleration
	program["iterations"] = options.part_lifetime
	program["drag"] = 1-options.part_drag	#multiplicative factor