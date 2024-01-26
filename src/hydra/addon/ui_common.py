import bpy, bpy.types
from bpy.props import StringProperty, BoolProperty
from Hydra import common
from Hydra.sim import flow
from Hydra.utils import nav, apply

class ImageOperator(bpy.types.Operator):
	def get_target(self, ctx):
		ret = ctx.area.spaces.active.image
		ret.hydra_erosion.img_size = ret.size
		return ret
	
class ObjectOperator(bpy.types.Operator):
	def get_target(self, ctx):
		return ctx.object

class HydraPanel(bpy.types.Panel):
	bl_region_type = 'UI'
	bl_category = "Hydra"
	bl_options = {'DEFAULT_CLOSED'}

class ImagePanel(HydraPanel):
	bl_space_type = 'IMAGE_EDITOR'

	@classmethod
	def poll(cls, ctx):
		img = ctx.area.spaces.active.image
		if not img or tuple(img.size) == (0,0):
			return False
		return not img.hydra_erosion.is_generated

class ObjectPanel(HydraPanel):
	bl_space_type = 'VIEW_3D'
	bl_context = "objectmode"

	@classmethod
	def poll(cls, ctx):
		ob = ctx.object
		if not ob:
			return
		if ob.hydra_erosion.is_generated:
			return False
		return ob.type == "MESH" and len(ob.data.vertices) != 0
	
# class FlowPanel(ImagePanel):
# 	"""Panel for flowmap generation."""
# 	bl_label = "Hydra - Flow"
# 	bl_idname = "HYDRA_PT_imgflowpanel"
# 	bl_description = "Generate flow data into an image"

# 	def draw(self, ctx):
# 		img = ctx.area.spaces.active.image
# 		hyd = img.hydra_erosion

# 		col = self.layout.column()
# 		col.operator('hydra.imggenflow', text="Generate Flowmap", icon="MATFLUID")

# 		col.separator()
# 		fragmentSize(col.box())
		
# 		fragmentNav(col, f"HYD_{img.name}_Flow", "Flow")

# 		col.separator()
# 		box = col.box()
# 		box.prop(hyd, "flow_contrast", slider=True)
# 		box.prop(hyd, "interpolate_flow")
# 		split = box.split()
# 		split.label(text="Chunk size")
# 		split.prop(hyd, "flow_subdiv", text="")
		
# 		col.separator()
# 		col.label(text="Particle settings")
# 		box = col.box()
# 		box.prop(hyd, "part_lifetime")
# 		box.prop(hyd, "part_acceleration", slider=True)
# 		box.prop(hyd, "part_drag", slider=True)

# class FlowPanel(ObjectPanel):
# 	"""Panel for flowmap generation."""
# 	bl_label = "Hydra - Flow"
# 	bl_idname = "HYDRA_PT_flowpanel"
# 	bl_description = "Generate flow data into an image"

# 	def draw(self, ctx):
# 		hyd = ctx.object.hydra_erosion
		
# 		col = self.layout.column()
# 		col.operator('hydra.genflow', text="Generate Flowmap", icon="MATFLUID")
	
# 		fragmentSize(col.box(), ctx.object)
		
# 		name = f"HYD_{ctx.object.name}_Flow"
# 		if name in bpy.data.images:
# 			col.separator()
# 			col.label(text="Generated:")
# 			box = col.box()
# 			split = box.split()
# 			split.label(text=name)
# 			op = split.operator('hydra.nav', text="", icon="IMAGE_DATA")
# 			op.target = name

# 		col.separator()
# 		box = col.box()
# 		box.prop(hyd, "flow_contrast", slider=True)
# 		box.prop(hyd, "interpolate_flow")
# 		split = box.split()
# 		split.label(text="Chunk size")
# 		split.prop(hyd, "flow_subdiv", text="")

# 		col.separator()
# 		col.label(text="Particle settings")
# 		box = col.box()
# 		box.prop(hyd, "part_lifetime")
# 		box.prop(hyd, "part_acceleration", slider=True)
# 		box.prop(hyd, "part_drag", slider=True)

class FlowOperator(bpy.types.Operator):
	bl_label = "Generate Flow"
	bl_description = "Generates a map of flow concentration using particle erosion. Uses eroded heightmaps, if they exist"
	bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		common.data.clear()
		target = self.get_target(ctx)
		img = flow.generate_flow(target)
		nav.goto_image(img)
		self.report({"INFO"}, f"Successfuly created image: {img.name}")
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
	
def get_exports():
	return [
		CleanupOperator
	]