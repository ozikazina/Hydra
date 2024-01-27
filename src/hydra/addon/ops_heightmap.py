"""Module responsible for heightmap operators."""

import bpy, bpy.types
from bpy.props import StringProperty, BoolProperty

from Hydra import common
from Hydra.sim import heightmap
from Hydra.utils import nav, texture, apply
from Hydra.addon import ops_common

#-------------------------------------------- Preview

class PreviewOp(ops_common.HydraOperator):
	"""Heightmap modifier preview operator."""
	bl_idname = "hydra.hm_preview"
	bl_label = "Preview"
	bl_description = "Preview map"

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		data = common.data
		if data.has_map(hyd.map_result):
			apply.add_preview(target)
		
		return {'FINISHED'}
	
class remove_previewOp(ops_common.HydraOperator):
	"""Heightmap modifier preview removal operator."""
	bl_idname = "hydra.hm_remove_preview"
	bl_label = "Remove preview"
	bl_description = "Remove preview modifier"
	bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		apply.remove_preview()
		return {'FINISHED'}

#-------------------------------------------- Merge

class MergeOp(ops_common.HydraOperator):
	"""Modifier apply to mesh operator."""
	bl_idname = "hydra.hm_merge"
	bl_label = "Apply"
	bl_description = "Applies the preview or modifier directly to the mesh (applies entire stack up to the modifier!)"
	bl_options = {'REGISTER'}

	@classmethod
	def poll(cls, ctx):
		return not ctx.object.data.shape_keys or len(ctx.object.data.shape_keys.key_blocks) == 0

	def invoke(self, ctx, event):
		lst = [x for x in ctx.object.modifiers]
		for mod in lst:
			name = mod.name
			bpy.ops.object.modifier_apply(modifier=mod.name)
			if name.startswith("HYD_"):
				break
		
		apply.remove_preview()
		heightmap.set_result_as_source(ctx.object, as_base=True)
		nav.goto_modifier()
		return {'FINISHED'}

class MergeShapeOp(ops_common.HydraOperator):
	"""Modifier apply as shape key operator."""
	bl_idname = "hydra.hm_merge_shape"
	bl_label = "Apply as shape"
	bl_description = "Applies the preview or modifier as a shape key"
	bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = next((x for x in ctx.object.modifiers if x.name.startswith("HYD_")), None)
		if hyd:
			name = hyd.name
			keys = ctx.object.data.shape_keys
			shapeName = "HYD_Shape"
			if keys and shapeName in keys.key_blocks:
				ctx.object.shape_key_remove(keys.key_blocks[shapeName])

			bpy.ops.object.modifier_apply_as_shapekey(modifier=name)
			shape = ctx.object.data.shape_keys.key_blocks[name]
			shape.name = shapeName
			shape.value = 1

		apply.remove_preview()
		name = f"HYD_{ctx.object.name}_Guide"
		if name in bpy.data.objects:
			bpy.data.objects.remove(bpy.data.objects[name])
		heightmap.set_result_as_source(ctx.object)
		nav.gotoShape()
		return {'FINISHED'}

#-------------------------------------------- Move

class MoveOp(ops_common.HydraOperator):
	"""Apply Result as Source operator."""
	bl_idname = "hydra.hm_move"; bl_label = "Set as Source"
	bl_description = "Sets the Result heightmap as the new Source map"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		heightmap.set_result_as_source(self.get_target(ctx))
		return {'FINISHED'}

class MoveBackOp(ops_common.HydraOperator):
	"""Apply Source as Result operator."""
	bl_idname = "hydra.hm_move_back"; bl_label = "Set as Result"
	bl_description = "Sets this Source as the Result map and previews it"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion
		data = common.data

		data.try_release_map(hyd.map_result)
		src = data.maps[hyd.map_source]

		txt = texture.clone(src.texture)
		hmid = data.create_map(src.name, txt)
		hyd.map_result = hmid

		apply.add_preview(target)
		return {'FINISHED'}

#-------------------------------------------- Delete

class DeleteOp(ops_common.HydraOperator):
	"""Delete Result operator."""
	bl_idname = "hydra.hm_delete"; bl_label = "Delete this layer"
	bl_description = "Deletes the generated heightmap"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		apply.remove_preview()

		common.data.try_release_map(hyd.map_result)
		hyd.map_result = ""
		return {'FINISHED'}

class ClearOp(ops_common.HydraOperator):
	"""Clear object textures operator."""
	bl_idname = "hydra.hm_clear"; bl_label = "Clear"
	bl_description = "Clear textures"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		apply.remove_preview()

		common.data.try_release_map(hyd.map_base)
		common.data.try_release_map(hyd.map_source)
		common.data.try_release_map(hyd.map_result)

		hyd.map_base = ""
		hyd.map_source = ""
		hyd.map_result = ""
		self.report({'INFO'}, f"Successfuly cleared textures from: {target.name}")
		return {'FINISHED'}

#-------------------------------------------- Apply

class ModifierOp(ops_common.HydraOperator):
	"""Apply as modifier operator."""
	bl_idname = "hydra.hm_apply_mod"; bl_label = "As Modifier"
	bl_description = "Apply texture as a modifier"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)

		apply.remove_preview()
		displacement = heightmap.get_displacement(target, name=f"HYD_{target.name}_DISPLACE")
		apply.add_modifier(ctx.object, displacement)

		nav.goto_modifier()
		self.report({'INFO'}, f"Successfuly applied map as a modifier")
		return {'FINISHED'}
	
class GeometryOp(ops_common.HydraOperator):
	"""Apply as modifier operator."""
	bl_idname = "hydra.hm_apply_geo"; bl_label = "As Geometry Modifier"
	bl_description = "Apply texture as a Geometry Nodes modifier"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		apply.remove_preview()
		displacement = heightmap.get_displacement(target, name=f"HYD_{target.name}_DISPLACE")

		apply.add_geometry_nodes(ctx.object, displacement)

		nav.goto_modifier()
		nav.goto_geometry(target)
		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}

class DisplaceOp(ops_common.HydraOperator):
	"""Apply as displacement map operator."""
	bl_idname = "hydra.hm_apply_disp"; bl_label = "As Displacement"
	bl_description = "Apply texture as a displacement node in the object's shader"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		apply.remove_preview()
		displacement = heightmap.get_displacement(target, name=f"HYD_{target.name}_DISPLACE")

		apply.add_displacement(target, displacement)

		nav.goto_shader(target)
		self.report({'INFO'}, f"Successfuly applied map as a displacement")
		return {'FINISHED'}

class BumpOp(ops_common.HydraOperator):
	"""Apply as bump map operator."""
	bl_idname = "hydra.hm_apply_bump"; bl_label = "As Bump"
	bl_description = "Apply texture as a bumpmap node in the object's shader"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		apply.remove_preview()
		displacement = heightmap.get_displacement(target, name=f"HYD_{target.name}_DISPLACE")

		apply.add_bump(target, displacement)

		nav.goto_shader(target)
		self.report({'INFO'}, f"Successfuly applied map as a bumpmap")
		return {'FINISHED'}

class ImageOp(ops_common.HydraOperator):
	"""Export as image operator."""
	bl_idname = "hydra.hm_apply_img"; bl_label = "As Image"
	bl_description = "Save heightmap to a Blender Image"; bl_options = {'REGISTER'}

	save_target: StringProperty(default="")
	"""Heightmap ID."""
	name: StringProperty(default="")
	"""Created image name."""

	def invoke(self, ctx, event):
		data = common.data
		img = texture.write_image(self.name, data.maps[self.save_target].texture)
		nav.goto_image(img)
		self.report({'INFO'}, f"Created texture: {self.name}")
		return {'FINISHED'}

#-------------------------------------------- Reload

class ReloadOp(ops_common.HydraOperator):
	"""Reload base map as source operator."""
	bl_idname = "hydra.hm_reload"
	bl_label = "Reload"
	bl_description = "Load base mesh heightmap as a source"
	bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion
		data = common.data

		data.try_release_map(hyd.map_source)

		base = data.maps[hyd.map_base]
		txt = texture.clone(base.texture)

		hyd.map_source = data.create_map(base.name, txt)

		self.report({'INFO'}, "Reloaded base map.")
		return {'FINISHED'}
	
class ForceReloadOp(ops_common.HydraOperator):
	"""Recalculate base and source maps operator."""
	bl_idname = "hydra.hm_force_reload"
	bl_label = "Recalculate"
	bl_description = "Create a base heightmap from the current object"
	bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		target = self.get_target(ctx)
		hyd = target.hydra_erosion

		common.data.try_release_map(hyd.map_base)
		common.data.try_release_map(hyd.map_source)

		heightmap.prepare_heightmap(target)

		self.report({'INFO'}, f"Recalculated base map.")
		return {'FINISHED'}

#-------------------------------------------- Goto

class NavOp(ops_common.HydraOperator):
	"""Navigate to entity operator."""
	bl_idname = "hydra.nav"; bl_label = "View"
	bl_description = "View this image"; bl_options = {'REGISTER'}

	target: StringProperty(default="")
	"""Target name."""
	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		if not self.useImage:
			if self.target in bpy.data.objects:
				nav.gotoObject(bpy.data.objects[self.target])
			else:
				self.report({'ERROR'}, f"Failed to find object.")
		else:
			if self.target in bpy.data.images:
				nav.gotoImage(bpy.data.images[self.target])
			else:
				self.report({'ERROR'}, f"Failed to find image.")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		ClearOp,
		MergeOp,
		MergeShapeOp,
		PreviewOp,
		remove_previewOp,
		MoveOp,
		MoveBackOp,
		DeleteOp,
		ModifierOp,
		GeometryOp,
		ImageOp,
		DisplaceOp,
		BumpOp,
		ReloadOp,
		ForceReloadOp,
		NavOp
	]