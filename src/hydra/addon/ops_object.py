"""Module responsible for object UI elements and operators."""

import bpy, bpy.types

from Hydra import common, startup, opengl
from Hydra.sim import erosion, flow, heightmap, thermal, mei
from Hydra.utils import nav, texture, apply
from Hydra.addon.ui_common import ObjectOperator, FlowOperator

#-------------------------------------------- Heightmap

class HeightmapOp(bpy.types.Operator):
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
		txt = heightmap.genHeightmap(act, normalized=normalized, world_scale=world_scale, local_scale=local_scale)

		img = texture.writeImage(f"HYD_{act.name}_Heightmap", txt)
		txt.release()
		act.hydra_erosion.img_size = size
		nav.gotoImage(img)
		self.report({'INFO'}, f"Successfuly created heightmap: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Erosion

class ErodeOp(bpy.types.Operator):
	"""Water erosion operator."""
	bl_idname = "hydra.erode"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		data.clear()
		data.running = True

		if hyd.erosion_solver == "particle":
			erosion.erosionPrepare(ctx.object)
			erosion.erosionRun(ctx.object)
			imgs = erosion.erosionFinish(ctx.object)
		else:
			mei.erosionPrepare(ctx.object)
			mei.erosionRun(ctx.object)
			_ = mei.erosionFinish(ctx.object)
		
		heightmap.preview(ctx.object, data.maps[hyd.map_current], data.maps[hyd.map_base])
		nav.gotoModifier()
		if hyd.out_color:
			nav.gotoImage(imgs[2])
		elif hyd.out_sediment:
			nav.gotoImage(imgs[1])
		elif hyd.out_depth:
			nav.gotoImage(imgs[0])
		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Flow

class FlowOp(FlowOperator, ObjectOperator):
	"""Flowmap generation operator."""
	bl_idname = "hydra.flow"

#-------------------------------------------- Thermal

class ThermalOp(bpy.types.Operator):
	"""Thermal erosion operator."""
	bl_idname = "hydra.thermal"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		data = common.data
		data.clear()
		hyd = ctx.object.hydra_erosion
		apply.removePreview()

		thermal.thermalPrepare(ctx.object)
		thermal.thermalRun(ctx.object)
		thermal.thermalFinish(ctx.object)

		heightmap.preview(ctx.object, data.maps[hyd.map_current], data.maps[hyd.map_base])
		nav.gotoModifier()
		data.report(self, callerName="Erosion")
		return {'FINISHED'}

#--------------------------------------------

class ReloadShadersOp(bpy.types.Operator):
	"""Operator for reloading shaders."""
	bl_idname = "hydra.reloadshaders"
	bl_label = "Reload shaders"
	bl_description = "Reloads OpenGL shaders"

	def execute(self, context):
		opengl.initContext()
		self.report({'INFO'}, "Successfuly reloaded shaders.")
		return {'FINISHED'}

class NukeUIOp(bpy.types.Operator):
	"""Destroys Blender's UI."""
	bl_idname = "hydra.nukeui"
	bl_label = "Nuke UI"
	bl_description = "Enjoy the authentic developer experience (restart Blender to restore UI)"

	def execute(self, context):
		heightmap.nukeUI()
		self.report({'INFO'}, "Successfuly destroyed UI.")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		ErodeOp,
		ThermalOp,
		FlowOp,
		HeightmapOp,
		ReloadShadersOp,
		NukeUIOp
	]