import bpy, bpy.types
from Hydra import common
from Hydra.sim import flow, thermal, heightmap
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
		data = common.data
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		if self.is_space_type(common._SPACE_OBJECT):
			apply.remove_preview()

		thermal.erode(target)

		if self.is_space_type(common._SPACE_OBJECT):
			heightmap.preview(ctx.object)
		else:
			img = apply.add_image_preview(data.maps[hyd.map_current].texture)
			nav.gotoImage(img)

		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Cleanup

class CleanupOperator(bpy.types.Operator):
	"""Resource release operator."""
	bl_idname = "hydra.release_cache"
	bl_label = "Clean"
	bl_description = "Release cached textures"
	bl_options = {'REGISTER', 'UNDO'}
	
	def invoke(self, context, event):
		apply.remove_preview()
		apply.remove_preview_image()
		common.data.free_all()
		self.report({'INFO'}, "Successfuly freed cached textures.")
		common.show_message("Successfuly freed cached textures.")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [CleanupOperator]