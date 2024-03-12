"""ModernGL initialization module."""

from pathlib import Path
from Hydra import common

# --------------------------------------------------------- Init

def init_context():
	"""Compiles shader programs and adds them to :data:`common.data`."""
	data = common.data
	ctx = data.context
	dr = Path(__file__).resolve().parent
	base = Path(dr, "GLSL")

	for prog in data.programs.values():
		prog.release()
	
	for shader in data.shaders.values():
		shader.release()

	def make_prog(name, v, f):
		data.programs[name] = ctx.program(
			vertex_shader=v,
			fragment_shader=f
		)

	with open(Path(base, "height.vert"), "r") as f:
		vert = f.read()
	with open(Path(base, "height.frag"), "r") as f:
		frag = f.read()
	make_prog("heightmap", vert, frag)

	with open(Path(base, "identity.vert"), "r") as f:
		vert = f.read()
	with open(Path(base, "redraw.frag"), "r") as f:
		frag = f.read()
	make_prog("redraw", vert, frag)

	with open(Path(base, "erosion.glsl"), "r") as f:
		comp = f.read()
	data.shaders["erosion"] = ctx.compute_shader(comp)

	with open(Path(base, "erosion.frag"), "r") as f:
		frag = f.read()
	make_prog("erosion", vert, frag)
	
	with open(Path(base, "flow.glsl"), "r") as f:
		comp = f.read()
	data.shaders["flow"] = ctx.compute_shader(comp)

	with open(Path(base, "diff.glsl"), "r") as f:
		comp = f.read()
	data.shaders["diff"] = ctx.compute_shader(comp)

	with open(Path(base, "thermalA.glsl"), "r") as f:
		comp = f.read()
	data.shaders["thermalA"] = ctx.compute_shader(comp)
	with open(Path(base, "thermalB.glsl"), "r") as f:
		comp = f.read()
	data.shaders["thermalB"] = ctx.compute_shader(comp)

	with open(Path(base, "snow.glsl"), "r") as f:
		comp = f.read()
	data.shaders["snow"] = ctx.compute_shader(comp)

	with open(Path(base, "linear.glsl"), "r") as f:
		comp = f.read()
	data.shaders["linear"] = ctx.compute_shader(comp)

	with open(Path(base, "plug.glsl"), "r") as f:
		comp = f.read()
	data.shaders["plug"] = ctx.compute_shader(comp)

	with open(Path(base, "scaling.glsl"), "r") as f:
		comp = f.read()
	data.shaders["scaling"] = ctx.compute_shader(comp)
	
	for i in range(1,6+1):
		with open(Path(base, f"mei{i}.glsl"), "r") as f:
			comp = f.read()
		data.shaders[f"mei{i}"] = ctx.compute_shader(comp)
