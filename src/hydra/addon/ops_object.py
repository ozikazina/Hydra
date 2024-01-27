"""Module responsible for object UI elements and operators."""

import bpy, bpy.types

from Hydra import common
from Hydra.sim import heightmap
from Hydra.utils import nav, texture
from Hydra.addon import ops_common

#-------------------------------------------- Heightmap

class HeightmapOperator(bpy.types.Operator):
	"""Standalone heightmap operator."""
	bl_idname = "hydra.genheight"
	bl_label = "Heightmap"
	bl_description = "Generate heightmap into an image"

	def invoke(self, ctx, event):
		common.data.clear()
		act = ctx.object

		size = tuple(act.hydra_erosion.img_size)
		act.hydra_erosion.img_size = tuple(act.hydra_erosion.heightmap_gen_size)

		normalized = act.hydra_erosion.heightmap_gen_type == "normalized"
		world_scale = act.hydra_erosion.heightmap_gen_type == "world"
		local_scale = act.hydra_erosion.heightmap_gen_type == "object"
		txt = heightmap.gen_heightmap(act, normalized=normalized, world_scale=world_scale, local_scale=local_scale)

		img = texture.write_image(f"HYD_{act.name}_Heightmap", txt)
		txt.release()
		act.hydra_erosion.img_size = size
		nav.goto_image(img)
		self.report({'INFO'}, f"Successfuly created heightmap: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Erosion

class ErodeOperator(ops_common.ErosionOperator, ops_common.ObjectOperator):
	"""Water erosion operator."""
	bl_idname = "hydra.erode"

#-------------------------------------------- Flow

class FlowOperator(ops_common.FlowOperator, ops_common.ObjectOperator):
	"""Flowmap generation operator."""
	bl_idname = "hydra.flow"

#-------------------------------------------- Thermal

class ThermalOperator(ops_common.ThermalOperator, ops_common.ObjectOperator):
	bl_idname = "hydra.thermal"

#-------------------------------------------- Decoupling

class DecoupleOperator(ops_common.DecoupleOperator, ops_common.ObjectOperator):
	"""Decouple operator."""
	bl_idname = "hydra.decouple"

#-------------------------------------------- Debug

class NukeGUIOperator(bpy.types.Operator):
	"""Destroys Blender's GUI."""
	bl_idname = "hydra.nuke_gui"
	bl_label = "Nuke GUI"
	bl_description = "Enjoy the authentic developer experience (restart Blender to restore)"

	def execute(self, ctx):
		heightmap.nuke_gui()
		self.report({'INFO'}, "Successfuly destroyed GUI.")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		ErodeOperator,
		ThermalOperator,
		FlowOperator,
		HeightmapOperator,
		DecoupleOperator,
		NukeGUIOperator
	]