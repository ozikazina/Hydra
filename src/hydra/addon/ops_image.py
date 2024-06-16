"""Module responsible for image operators."""

from Hydra import common
from Hydra.utils import apply, texture
from Hydra.addon import ops_common
from Hydra.sim import heightmap

#-------------------------------------------- Generate

class LandscapeOperator(ops_common.ImageOperator):
	"""Landscape generation operator."""
	bl_idname = "hydra.landscape"
	bl_label = "Generate"
	bl_description = "Generate a landscape using this heightmap"
			
	def invoke(self, ctx, event):
		apply.add_landscape(self.get_target(ctx))
		return {'FINISHED'}

class OverrideImageOperator(ops_common.ImageOperator):
	"""Apply result back to original."""
	bl_idname = "hydra.override_original"
	bl_label = "Apply to original"
	bl_description = "Write this result back to the original image"
	
	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		if target.hydra_erosion.map_result == "":
			self.report({'ERROR'}, "No result to apply")
			return {'CANCELLED'}

		apply.remove_preview()
		texture.write_image(target.name, common.data.get_map(target.hydra_erosion.map_result).texture)
		heightmap.set_result_as_source(target, as_base=True)
		target.hydra_erosion.is_generated = False
		return {'FINISHED'}

#-------------------------------------------- Exports
	
def get_exports()->list:
	return [
		LandscapeOperator,
		OverrideImageOperator
	]