"""Module responsible for VAO creation and mesh operations."""

import numpy as np
import bpy, bmesh
import bpy.types
import moderngl as mgl

# --------------------------------------------------------- Models

def create_vao(ctx: mgl.Context, program: mgl.Program, vertices:list[tuple[float]]=None, indices:list[int]=None):
	"""Creates a :class:`moderngl.VertexArray` object.
	
	:param ctx: ModernGL context.
	:type ctx: :class:`moderngl.Context`
	:param program: Program to bind to the VAO.
	:type program: :class:`moderngl.Program`
	:param vertices: Optional list of 3D vertex position.
	:type vertices: :class:`list[tuple[float, float, float]]`
	:param indices: Optional list of vertex indices.
	:type indices: :class:`list[int]`
	:return: Created VAO object.
	:rtype: :class:`moderngl.VertexArray`"""
	if vertices is None:
		vertices = [(1,1,0), (1,-1,0), (-1,-1,0), (1,1,0), (-1,-1,0),  (-1,1,0)]
		indices = None
		
	vbo = ctx.buffer(data=np.array(vertices).astype('f4').tobytes())
	if indices is None:
		return ctx.vertex_array(
			program=program,
			content=[(vbo, "3f", "position")]
		)
	else:
		ind = ctx.buffer(data=np.array(indices).tobytes())
		return ctx.vertex_array(
			program=program,
			content=[(vbo, "3f", "position")], index_buffer=ind
		)

def evaluate_mesh(obj: bpy.types.Object)->bpy.types.Mesh:
	"""Evaluates an object as a mesh.
	
	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	:return: Evaluated mesh with calculated loop triangles.
	:rtype: :class:`bpy.types.Mesh`"""
	depsgraph = bpy.context.evaluated_depsgraph_get()
	eval = obj.evaluated_get(depsgraph)
	mesh = bpy.data.meshes.new_from_object(eval)
	mesh.calc_loop_triangles()
	return mesh

def get_resize_matrix(obj: bpy.types.Object) -> tuple[float]:
	"""
	Creates a resizing matrix that scales the input object into normalized device coordinates, so that 1-Z is the normalized surface height.

	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	:return: Created resizing matrix.
	:rtype: :class:`tuple[float]`
	"""
	ar = np.array(obj.bound_box)
	cx = (ar[4][0] + ar[0][0]) * 0.5
	cy = (ar[2][1] + ar[0][1]) * 0.5
	cz = (ar[1][2] + ar[0][2]) * 0.5
	dx = 2.0/(ar[4][0] - ar[0][0])
	dy = 2.0/(ar[2][1] - ar[0][1])
	dz = 1.0/(ar[1][2] - ar[0][2])

	return (dx,0,0,-cx*dx, 0,dy,0,-cy*dy, 0,0,-dz,0.5+cz*dz, 0,0,0,1)

def recalculate_scales(obj: bpy.types.Object) -> None:
	"""
	Sets :data:`hydra_erosion.scale_ratio`, `hydra_erosion.org_scale`. `hydra_erosion.org_width` and :data:`hydra_erosion.height_scale` for the object.

	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	:return: Created resizing matrix.
	:rtype: :class:`tuple[float]`
	"""
	ar = np.array(obj.bound_box)
	dx = (ar[4][0] - ar[0][0]) / 2
	dy = (ar[2][1] - ar[0][1]) / 2
	dz = (ar[1][2] - ar[0][2])

	obj.hydra_erosion.scale_ratio = dy / dx if dx > 1e-3 else 1
	obj.hydra_erosion.height_scale = dz / dx if dx > 1e-3 else 1
	obj.hydra_erosion.org_scale = abs(obj.dimensions.z / obj.scale.z) if abs(obj.scale.z) > 1e-3 else 1
	obj.hydra_erosion.org_width = abs(obj.dimensions.x / obj.scale.x) if abs(obj.scale.x) > 1e-3 else 1
