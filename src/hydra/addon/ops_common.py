import bpy, bpy.types
from Hydra import common, opengl
from Hydra.sim import flow, thermal, heightmap, erosion_particle, erosion_mei
from Hydra.utils import nav, apply

class ImageOperator(bpy.types.Operator):
	bl_options = {'REGISTER'}

	def get_target(self, ctx):
		ret = ctx.area.spaces.active.image
		ret.hydra_erosion.img_size = ret.size
		return ret
	
	def is_space_type(self, name:str)->bool:
		return name == common._SPACE_IMAGE
	
class ObjectOperator(bpy.types.Operator):
	bl_options = {'REGISTER'}

	def get_target(self, ctx):
		return ctx.object
	
	def is_space_type(self, name:str)->bool:
		return name == common._SPACE_OBJECT

#-------------------------------------------- Erosion
	
class ErosionOperator(bpy.types.Operator):
	bl_label = "Erode"
	bl_description = "Erode object"

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		if hyd.erosion_solver == "particle":
			results = erosion_particle.erode(target)
			if "color" in results:
				nav.goto_image(results["color"])
			elif "sediment" in results:
				nav.goto_image(results["sediment"])
			elif "depth" in results:
				nav.goto_image(results["depth"])
		else:
			erosion_mei.erode(target)

		apply.add_preview(target)

		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Flow
	
class FlowOperator(bpy.types.Operator):
	bl_label = "Generate Flow"
	bl_description = "Generates a map of flow concentration using particle erosion. Uses eroded heightmaps, if they exist"

	def invoke(self, ctx, event):
		common.data.clear()
		target = self.get_target(ctx)
		img = flow.generate_flow(target)
		nav.goto_image(img)
		self.report({"INFO"}, f"Successfuly created image: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Thermal
	
class ThermalOperator():
	"""Thermal erosion operator."""
	bl_label = "Erode"
	bl_description = "Erode object"
	
	def invoke(self, ctx, event):
		target = self.get_target(ctx)

		thermal.erode(target)

		apply.add_preview(target)

		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}
	
#-------------------------------------------- Decoupling

class DecoupleOperator(bpy.types.Operator):
	"""Isolate and unlock entity operator."""
	bl_label = "Decouple"
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
		CleanupOperator,
		ReloadShadersOperator
	]