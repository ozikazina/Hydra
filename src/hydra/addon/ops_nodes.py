import bpy.types
from Hydra.utils import nodes

class AddUVOperator(bpy.types.Operator):
	bl_idname = "hydra.planet_uv"
	bl_label = "Planet UVs"
	bl_description = "Add texture coordinates for Image textures with Sphere projection. This matches mapping used in Hydra"

	@classmethod
	def poll(cls, ctx):
		return ctx.area.spaces[0].shader_type == "OBJECT"

	def invoke(self, ctx, event):
		tree = ctx.area.spaces[0].node_tree
		nodes.add_planet_shader_uv_nodes(tree.nodes, tree.links)
		return {'FINISHED'}

def get_exports()->list:
	return [
		AddUVOperator
	]