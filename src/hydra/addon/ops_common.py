import bpy
from bpy.props import BoolProperty

from Hydra import common, opengl
from Hydra.sim import flow, thermal, heightmap, erosion_particle, erosion_mei, snow
from Hydra.utils import nav, apply

class HydraOperator(bpy.types.Operator):
	bl_options = {'REGISTER'}

	@classmethod
	def get_target(cls, ctx):
		if ctx.space_data.type == common._SPACE_IMAGE:
			ret = ctx.area.spaces.active.image
			ret.hydra_erosion.img_size = ret.size
			return ret
		else:
			return ctx.object

class ImageOperator(bpy.types.Operator):
	bl_options = {'REGISTER'}

	@classmethod
	def get_target(cls, ctx):
		ret = ctx.area.spaces.active.image
		ret.hydra_erosion.img_size = ret.size
		return ret
	
	def is_space_type(self, name:str)->bool:
		return name == common._SPACE_IMAGE
	
class ObjectOperator(bpy.types.Operator):
	bl_options = {'REGISTER'}

	@classmethod
	def get_target(self, ctx):
		return ctx.object
	
	def is_space_type(self, name:str)->bool:
		return name == common._SPACE_OBJECT

#-------------------------------------------- Erosion
	
class ErosionOperator(HydraOperator):
	bl_label = "Erode"
	bl_idname = "hydra.erode"
	bl_description = "Erode object using current settings, or set current result as source and continue"

	apply: BoolProperty(
		name="Apply",
		default=False
	)

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		if self.apply:
			heightmap.set_result_as_source(target)

		if hyd.erosion_solver == "particle":
			results = erosion_particle.erode(target)
			if "color" in results:
				nav.goto_image(results["color"])
			elif "sediment" in results:
				nav.goto_image(results["sediment"])
			elif "depth" in results:
				nav.goto_image(results["depth"])
		else:
			results = erosion_mei.erode(target)
			if "color" in results:
				nav.goto_image(results["color"])

		apply.add_preview(target)

		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}
	
#-------------------------------------------- Thermal
	
class ThermalOperator(HydraOperator):
	"""Thermal erosion operator."""
	bl_label = "Erode"
	bl_idname = "hydra.thermal"
	bl_description = "Erode object using current settings, or set current result as source and continue"

	apply: BoolProperty(
		name="Apply",
		default=False
	)
	
	def invoke(self, ctx, event):
		target = self.get_target(ctx)

		if self.apply:
			heightmap.set_result_as_source(target)

		thermal.erode(target)

		apply.add_preview(target)

		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}
	
#-------------------------------------------- Snow

class SnowOperator(HydraOperator):
	"""Snow erosion operator."""
	bl_label = "Erode"
	bl_idname = "hydra.snow"
	bl_description = "Simulate snow layer on current object"
	
	apply: BoolProperty(
		name="Apply",
		default=False
	)

	def invoke(self, ctx, event):
		target = self.get_target(ctx)

		if self.apply:
			heightmap.set_result_as_source(target)

		img = snow.simulate(target)

		if target.hydra_erosion.snow_output != "displacement":
			nav.goto_image(img)

		if target.hydra_erosion.snow_output != "texture":
			apply.add_preview(target)

		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Flow
	
class FlowOperator(HydraOperator):
	bl_label = "Generate Flow"
	bl_idname = "hydra.flow"
	bl_description = "Generates a map of flow concentration using particle erosion. Uses eroded heightmaps, if they exist"

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		img = flow.generate_flow(target)
		nav.goto_image(img)
		self.report({"INFO"}, f"Successfuly created image: {img.name}")
		return {'FINISHED'}
	
#-------------------------------------------- Decoupling

class DecoupleOperator(HydraOperator):
	"""Isolate and unlock entity operator."""
	bl_label = "Decouple"
	bl_idname = "hydra.decouple"
	bl_description = "Decouples this entity from it's owner, preventing overwriting. Allows erosion of this entity"

	def invoke(self, ctx, event):
		target = self.get_target(ctx)

		if target.name.startswith("HYD_"):
			target.name = target.name[4:]

		target.hydra_erosion.is_generated = False

		self.report({"INFO"}, "Target decoupled.")
		return {'FINISHED'}
	
#-------------------------------------------- Cleanup

class CleanupOperator(bpy.types.Operator):
	"""Resource release operator."""
	bl_idname = "hydra.release_cache"
	bl_label = "Clean"
	bl_description = "Release cached textures"
	bl_options = {'REGISTER', 'UNDO'}
	
	def invoke(self, ctx, event):
		apply.remove_preview()
		common.data.free_all()
		self.report({'INFO'}, "Successfuly freed cached textures.")
		common.show_message("Successfuly freed cached textures.")
		return {'FINISHED'}

#-------------------------------------------- Debug
	
class ReloadShadersOperator(bpy.types.Operator):
	"""Operator for reloading shaders."""
	bl_idname = "hydra.reload_shaders"
	bl_label = "Reload shaders"
	bl_description = "Reloads OpenGL shaders"

	def execute(self, ctx):
		opengl.init_context()
		self.report({'INFO'}, "Successfuly reloaded shaders.")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		ErosionOperator,
		FlowOperator,
		ThermalOperator,
		SnowOperator,
		DecoupleOperator,
		CleanupOperator,
		ReloadShadersOperator
	]
