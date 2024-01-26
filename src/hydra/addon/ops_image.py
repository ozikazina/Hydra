"""Module responsible for image UI elements and operators."""

import bpy
from Hydra import common
from Hydra.sim import thermal, flow, erosion, heightmap
from Hydra.utils import nav, apply, model
from Hydra.addon import ops_common

#-------------------------------------------- Flow

class FlowOp(ops_common.FlowOperator, ops_common.ImageOperator):
	"""Flowmap generation operator."""
	bl_idname = "hydra.flow_img"

#-------------------------------------------- Erosion

class ErodeOp(bpy.types.Operator):
	"""Water erosion operator."""
	bl_idname = "hydra.imgerode"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion
		data = common.data
		data.clear()
		data.running = True
		
		erosion.erosionPrepare(img)
		erosion.erosionRun(img)
		_ = erosion.erosionFinish(img)

		img = apply.addImagePreview(data.maps[hyd.map_current].texture)
		nav.gotoImage(img)
		data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Thermal

class ThermalOp(bpy.types.Operator):
	"""Thermal erosion operator."""
	bl_idname = "hydra.imgthermal"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		data = common.data
		data.clear()
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion

		thermal.thermalPrepare(img)
		thermal.thermalRun(img)
		thermal.thermalFinish(img)

		img = apply.addImagePreview(data.maps[hyd.map_current].texture)
		nav.gotoImage(img)
		data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Generate

class LandscapeOp(bpy.types.Operator):
	"""Landscape generation operator."""
	bl_idname = "hydra.landscape"
	bl_label = "Generate"
	bl_description = "Generate a landscape using this heightmap"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		data = common.data
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion

		if not data.hasMap(hyd.map_base):
			heightmap.prepareHeightmap(img)
		
		txt = data.maps[hyd.map_base].texture
		obj = model.createLandscape(txt, img.name, subscale=hyd.gen_subscale)
		apply.configureLandscape(obj, txt)
		nav.gotoObject(obj)
		return {'FINISHED'}

#-------------------------------------------- Exports
	
def get_exports()->list:
	return [
		ErodeOp,
		ThermalOp,
		FlowOp,
		LandscapeOp
	]