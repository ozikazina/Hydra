"""Module responsible for heightmap operators."""

import bpy, bpy.types
from bpy.props import StringProperty, BoolProperty

from Hydra import common
from Hydra.sim import heightmap
from Hydra.utils import nav, texture, apply

#-------------------------------------------- Preview

class HMPreviewOp(bpy.types.Operator):
	"""Heightmap modifier preview operator."""
	bl_idname = "hydra.hmpreview"
	bl_label = "Preview"
	bl_description = "Preview map"
	bl_options = {'REGISTER'}

	target: StringProperty(default="")
	"""Current heightmap ID."""
	base: StringProperty(default="")
	"""Base heightmap ID."""

	def invoke(self, ctx, event):
		data = common.data
		if data.hasMap(self.target):
			hm = data.maps[self.target]
			if data.hasMap(self.base):
				base = data.maps[self.base]
				heightmap.preview(ctx.object, hm, base)
			else:
				img = apply.addImagePreview(hm.texture)
				nav.gotoImage(img)
		return {'FINISHED'}
	
class HMNoPreviewOp(bpy.types.Operator):
	"""Heightmap modifier preview removal operator."""
	bl_idname = "hydra.hmnoview"; bl_label = "Remove preview"
	bl_description = "Remove preview modifier"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		apply.removePreview()
		return {'FINISHED'}

#-------------------------------------------- Merge

class HMMergeOp(bpy.types.Operator):
	"""Modifier apply to mesh operator."""
	bl_idname = "hydra.hmmerge"
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
		apply.removePreview()
		name = f"HYD_{ctx.object.name}_Guide"
		if name in bpy.data.objects:
			bpy.data.objects.remove(bpy.data.objects[name])
		heightmap.setCurrentAsSource(ctx.object, asBase=True)
		nav.gotoModifier()
		return {'FINISHED'}

class HMMergeShapeOp(bpy.types.Operator):
	"""Modifier apply as shape key operator."""
	bl_idname = "hydra.hmmergeshape"
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

		apply.removePreview()
		name = f"HYD_{ctx.object.name}_Guide"
		if name in bpy.data.objects:
			bpy.data.objects.remove(bpy.data.objects[name])
		heightmap.setCurrentAsSource(ctx.object, asBase=False)
		nav.gotoShape()
		return {'FINISHED'}

#-------------------------------------------- Move

class HMMoveOp(bpy.types.Operator):
	"""Apply Result as Source operator."""
	bl_idname = "hydra.hmmove"; bl_label = "Set as Source"
	bl_description = "Sets the Result heightmap as the new Source map"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		obj = ctx.area.spaces.active.image if self.useImage else ctx.object
		heightmap.setCurrentAsSource(obj)
		return {'FINISHED'}

class HMMoveBackOp(bpy.types.Operator):
	"""Apply Source as Result operator."""
	bl_idname = "hydra.hmback"; bl_label = "Set as Result"
	bl_description = "Sets this Source as the Result map and previews it"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		obj = ctx.area.spaces.active.image if self.useImage else ctx.object
		hyd = obj.hydra_erosion
		data = common.data
		data.releaseMap(hyd.map_current)
		src = data.maps[hyd.map_source]
		txt = texture.clone(src.texture)
		hmid = data.createMap(src.name, txt)
		hyd.map_current = hmid

		if self.useImage:
			apply.addImagePreview(txt)
		else:
			target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
			apply.addPreview(obj, target)
			target.release()
		return {'FINISHED'}

#-------------------------------------------- Delete

class HMDeleteOp(bpy.types.Operator):
	"""Delete Result operator."""
	bl_idname = "hydra.hmdelete"; bl_label = "Delete this layer"
	bl_description = "Deletes the generated heightmap"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		obj = ctx.area.spaces.active.image if self.useImage else ctx.object
		hyd = obj.hydra_erosion
		if not self.useImage:
			apply.removePreview()
		common.data.releaseMap(hyd.map_current)
		hyd.map_current = ""
		return {'FINISHED'}

class HMClearOp(bpy.types.Operator):
	"""Clear object textures operator."""
	bl_idname = "hydra.hmclear"; bl_label = "Clear"
	bl_description = "Clear textures"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		obj = ctx.area.spaces.active.image if self.useImage else ctx.object
		hyd = obj.hydra_erosion
		if not self.useImage:
			apply.removePreview()
		common.data.releaseMap(hyd.map_base)
		common.data.releaseMap(hyd.map_source)
		common.data.releaseMap(hyd.map_current)
		hyd.map_base = ""
		hyd.map_source = ""
		hyd.map_current = ""
		self.report({'INFO'}, f"Successfuly cleared textures from: {obj.name}")
		return {'FINISHED'}

#-------------------------------------------- Apply

class HMModifierOp(bpy.types.Operator):
	"""Apply as modifier operator."""
	bl_idname = "hydra.hmapplymod"; bl_label = "As Modifier"
	bl_description = "Apply texture as a modifier"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		apply.removePreview()
		target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
		apply.addModifier(ctx.object, target)
		target.release()
		nav.gotoModifier()
		self.report({'INFO'}, f"Successfuly applied map as a modifier")
		return {'FINISHED'}
	
class HMGeometryOp(bpy.types.Operator):
	"""Apply as modifier operator."""
	bl_idname = "hydra.hmapplygeo"; bl_label = "As Geometry Modifier"
	bl_description = "Apply texture as a Geometry Nodes modifier"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		data.clear()
		apply.removePreview()
		target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
		apply.addGeometryNode(ctx.object, target)
		target.release()
		nav.gotoModifier()
		nav.gotoGeometry(ctx.object)
		data.report(self, callerName="Erosion")
		return {'FINISHED'}
	
class HMGeometryInsertOp(bpy.types.Operator):
	"""Apply as modifier operator."""
	bl_idname = "hydra.hmapplygeoinsert"; bl_label = "Into Geometry Modifier"
	bl_description = "Apply texture into an existing Geometry Nodes modifier"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		data.clear()
		apply.removePreview()
		target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
		apply.addIntoGeometryNodes(ctx.object, target)
		target.release()
		nav.gotoModifier()
		nav.gotoGeometry(ctx.object)
		data.report(self, callerName="Erosion")
		return {'FINISHED'}

class HMDisplaceOp(bpy.types.Operator):
	"""Apply as displacement map operator."""
	bl_idname = "hydra.hmapplydisp"; bl_label = "As Displacement"
	bl_description = "Apply texture as a displacement node in the object's shader"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		apply.removePreview()
		target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
		apply.addDisplacement(ctx.object, target)
		target.release()
		nav.gotoShader(ctx.object)
		self.report({'INFO'}, f"Successfuly applied map as a displacement")
		return {'FINISHED'}

class HMBumpOp(bpy.types.Operator):
	"""Apply as bump map operator."""
	bl_idname = "hydra.hmapplybump"; bl_label = "As Bump"
	bl_description = "Apply texture as a bumpmap node in the object's shader"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		apply.removePreview()
		target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
		apply.addBump(ctx.object, target)
		target.release()
		nav.gotoShader(ctx.object)
		self.report({'INFO'}, f"Successfuly applied map as a bumpmap")
		return {'FINISHED'}

class HMImageOp(bpy.types.Operator):
	"""Export as image operator."""
	bl_idname = "hydra.hmapplyimg"; bl_label = "As Image"
	bl_description = "Save heightmap to a Blender Image"; bl_options = {'REGISTER'}

	save_target: StringProperty(default="")
	"""Heightmap ID."""
	name: StringProperty(default="")
	"""Created image name."""

	def invoke(self, ctx, event):
		data = common.data
		img = texture.writeImage(self.name, data.maps[self.save_target].texture)
		nav.gotoImage(img)
		self.report({'INFO'}, f"Created texture: {self.name}")
		return {'FINISHED'}
	
class HMUpdateOp(bpy.types.Operator):
	"""Update displacement texture."""
	bl_idname = "hydra.hmapplyupdate"; bl_label = "Only Update"
	bl_description = "Only update existing deformations"; bl_options = {'REGISTER'}

	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		target = heightmap.subtract(data.maps[hyd.map_current].texture, data.maps[hyd.map_base].texture, hyd.org_scale / hyd.height_scale)
		apply.onlyUpdate(ctx.object, target)
		target.release()
		self.report({'INFO'}, f"Updated texture: {self.name}")
		return {'FINISHED'}

#-------------------------------------------- Reload

class HMReloadOp(bpy.types.Operator):
	"""Reload base map as source operator."""
	bl_idname = "hydra.hmreload"; bl_label = "Reload"
	bl_description = "Load base mesh heightmap as a source"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		obj = ctx.area.spaces.active.image if self.useImage else ctx.object
		hyd = obj.hydra_erosion
		data = common.data
		data.releaseMap(hyd.map_source)
		base = data.maps[hyd.map_base]
		txt = texture.clone(base.texture)
		hyd.map_source = data.createMap(base.name, txt)
		self.report({'INFO'}, f"Reloaded base map.")
		return {'FINISHED'}
	
class HMForceReloadOp(bpy.types.Operator):
	"""Recalculate base and source maps operator."""
	bl_idname = "hydra.hmforcereload"; bl_label = "Recalculate"
	bl_description = "Create a base heightmap from the current object"; bl_options = {'REGISTER'}

	useImage: BoolProperty(default=False)
	"""Apply to image if `True`. Else apply to object."""

	def invoke(self, ctx, event):
		obj = ctx.object if self.useImage else ctx.area.spaces.active.image
		hyd = obj.hydra_erosion
		data = common.data
		data.releaseMap(hyd.map_base)
		data.releaseMap(hyd.map_source)
		heightmap.prepareHeightmap(obj)
		self.report({'INFO'}, f"Recalculated base map.")
		return {'FINISHED'}

#-------------------------------------------- Goto

class NavOp(bpy.types.Operator):
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

#-------------------------------------------- Decoupling

class InstantiateOp(bpy.types.Operator):
	"""Isolate and unlock entity operator."""
	bl_idname = "hydra.instantiate"
	bl_label = "Decouple"
	bl_description = "Decouples this entity from it's owner, preventing overwriting. Allows erosion of this entity"
	bl_options = {'REGISTER', 'UNDO'}
	
	useImage: BoolProperty(default=False)
	"""Apply to object if `True`. Else apply to image."""

	def invoke(self, context, event):
		if self.useImage:
			target = context.area.spaces.active.image
		else:
			target = context.active_object

		if target.name.startswith("HYD_"):
			target.name = target.name[4:]

		target.hydra_erosion.is_generated = False

		if self.useImage:
			self.report({"INFO"}, "Image decoupled.")
		else:
			self.report({"INFO"}, "Object decoupled.")
		return {'FINISHED'}

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		HMClearOp,
		HMMergeOp,
		HMMergeShapeOp,
		HMPreviewOp,
		HMNoPreviewOp,
		HMMoveOp,
		HMMoveBackOp,
		HMDeleteOp,
		HMModifierOp,
		HMGeometryOp,
		HMGeometryInsertOp,
		HMImageOp,
		HMUpdateOp,
		HMDisplaceOp,
		HMBumpOp,
		HMReloadOp,
		HMForceReloadOp,
		NavOp,
		InstantiateOp
	]