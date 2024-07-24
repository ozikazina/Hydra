"""Module responsible for object operators."""

import bpy, bpy.types

from Hydra import common
from Hydra.sim import heightmap
from Hydra.utils import nav, texture
from Hydra.addon import ops_common

#-------------------------------------------- Heightmap

class HeightmapOperator(ops_common.ObjectOperator):
	"""Standalone heightmap operator."""
	bl_idname = "hydra.genheight"
	bl_label = "Heightmap"
	bl_description = "Generate heightmap into an image"

	def invoke(self, ctx, event):
		act = self.get_target(ctx)
		hyd = act.hydra_erosion
		gen_type = hyd.heightmap_gen_type

		normalized = gen_type == "normalized"
		world_scale = gen_type == "world"
		local_scale = gen_type == "local"
		txt = heightmap.generate_heightmap(act,
			size=hyd.heightmap_gen_size,
			normalized=normalized,
			world_scale=world_scale,
			local_scale=local_scale,
			equirect=hyd.heightmap_equirect)

		img, _ = texture.write_image(f"HYD_{act.name}_Heightmap", txt)
		txt.release()

		if hyd.heightmap_equirect:
			img.hydra_erosion.tiling = "planet"

		nav.goto_image(img)
		self.report({'INFO'}, f"Successfuly created heightmap: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		HeightmapOperator
	]