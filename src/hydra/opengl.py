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

	
	with open(Path(base, "resize.frag"), "r") as f:
		frag = f.read()
	make_prog("resize", vert, frag)


	with open(Path(base, "erosion.frag"), "r") as f:
		frag = f.read()
	make_prog("erosion", vert, frag)


	for path in base.iterdir():
		if path.suffix == ".glsl":
			comp = path.read_text("utf-8")
			data.shaders[path.stem] = ctx.compute_shader(comp)
