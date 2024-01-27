"""Module responsible for image UI elements and operators."""

from Hydra.utils import apply
from Hydra.addon import ops_common

#-------------------------------------------- Generate

class LandscapeOperator(ops_common.ImageOperator):
	"""Landscape generation operator."""
	bl_idname = "hydra.landscape"
	bl_label = "Generate"
	bl_description = "Generate a landscape using this heightmap"
			
	def invoke(self, ctx, event):
		apply.add_landscape(self.get_target(ctx))
		return {'FINISHED'}

#-------------------------------------------- Exports
	
def get_exports()->list:
	return [
		LandscapeOperator
	]