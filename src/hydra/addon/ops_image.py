"""Module responsible for image operators."""

from Hydra import common
from Hydra.utils import apply, texture, nodes
from Hydra.addon import ops_common
from Hydra.sim import heightmap

from bpy.props import BoolProperty, StringProperty

#-------------------------------------------- Generate

class LandscapeOperator(ops_common.ImageOperator):
	"""Landscape generation operator."""
	bl_idname = "hydra.landscape"
	bl_label = "Generate"
	bl_description = "Generate a landscape using this heightmap. 'Detach' makes the created terrain fixed, otherwise it stays linked to this image"
			
	detach: BoolProperty(name="Detach", default=False,
		description="Detach the generated landscape from the original image"
	)

	target_name: StringProperty(name="Name", default="",
		description="Name of newly created object (can be empty)"
	)

	def execute(self, ctx):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		name = self.target_name if self.target_name != "" else None

		if hyd.tiling == "planet":
			apply.add_planet(target, max_verts_per_side=hyd.planet_resolution, name=name, detach=self.detach)
		else:
			apply.add_landscape(target, max_verts_per_side=hyd.landscape_resolution, name=name, detach=self.detach, tile=hyd.tiling!="none")

		common.data.report(self, "Landscape")
		return {'FINISHED'}

	def invoke(self, ctx, event):
		self.target_name = ""	# to clear name after detach
		return ctx.window_manager.invoke_props_dialog(self)

	def draw(self, ctx):
		layout = self.layout
		layout.prop(self, "target_name")

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