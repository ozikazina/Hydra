"""Module responsible for image UI elements and operators."""

import bpy
from Hydra.utils import apply
from Hydra.addon import ops_common

#-------------------------------------------- Flow

class FlowOperator(ops_common.FlowOperator, ops_common.ImageOperator):
	"""Flowmap generation operator."""
	bl_idname = "hydra.flow_img"

#-------------------------------------------- Erosion

class ErodeOperator(ops_common.ErosionOperator, ops_common.ImageOperator):
	"""Water erosion operator."""
	bl_idname = "hydra.erode_img"

#-------------------------------------------- Thermal

class ThermalOperator(ops_common.ThermalOperator, ops_common.ImageOperator):
	"""Thermal erosion operator."""
	bl_idname = "hydra.thermal_img"

#-------------------------------------------- Decoupling
	
class DecoupleOperator(ops_common.DecoupleOperator, ops_common.ImageOperator):
	"""Decouple operator."""
	bl_idname = "hydra.decouple_img"

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
		ErodeOperator,
		ThermalOperator,
		FlowOperator,
		LandscapeOperator,
		DecoupleOperator
	]