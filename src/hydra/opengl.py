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
	
	data.release_shaders()

	def make_prog(name, v, f):
		data.programs[name] = ctx.program(
			vertex_shader=v,
			fragment_shader=f
		)

	vert = Path(base, "height.vert").read_text()
	frag = Path(base, "height.frag").read_text()
	make_prog("heightmap", vert, frag)

	vert = Path(base, "height_polar.vert").read_text()
	frag = Path(base, "height_polar.frag").read_text()
	make_prog("polar", vert, frag)

	vert = Path(base, "height_equirect.vert").read_text()
	make_prog("equirect", vert, frag)

	vert = Path(base, "identity.vert").read_text()
	frag = Path(base, "redraw.frag").read_text()
	make_prog("redraw", vert, frag)
	
	frag = Path(base, "resize.frag").read_text()
	make_prog("resize", vert, frag)