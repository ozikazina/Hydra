"""Module responsible for VAO creation and mesh operations."""

import numpy as np
import bpy, bmesh
import bpy.types
import moderngl as mgl
import math

# --------------------------------------------------------- Models

def createVAO(ctx: mgl.Context, program: mgl.Program, vertices:list[tuple[float]]=None, indices:list[int]=None):
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

def evaluateMesh(obj: bpy.types.Object)->tuple[any, any]:
	"""Evaluates an object as a mesh.
	
	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	:return: Created `BMesh` and a list of vertices.
	:rtype: :class:`tuple[BMesh, list[Vertex]]`"""
	depsgraph = bpy.context.evaluated_depsgraph_get()
	eval = obj.evaluated_get(depsgraph)
	mesh = bpy.data.meshes.new_from_object(eval)
	bm = bmesh.new()
	bm.from_mesh(mesh)
	bmesh.ops.triangulate(bm, faces=bm.faces)
	return bm, mesh.vertices

def getResizeMatrix(obj: bpy.types.Object) -> tuple[float]:
	"""
	Creates a resizing matrix that scales the input object into normalized device coordinates, so that 1-Z is the normalized surface height.
	Also sets :data:`hydra.scale_ratio` and :data:`hydra.height_scale` for the object.

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

	obj.hydra.scale_ratio = dx / dy
	obj.hydra.height_scale = dx / dz
	obj.hydra.org_scale = 2 * obj.dimensions.z / obj.scale.z
	return (dx,0,0,-cx*dx, 0,dy,0,-cy*dy, 0,0,-dz,0.5+cz*dz, 0,0,0,1)

def createLandscape(txt: mgl.Texture, name: str)->bpy.types.Object:
	"""Creates a grid object of the given texture resolution. Divides the resolution by global settings. Doesn't write height data!
	
	:param txt: Texture of the intended resolution.
	:type txt: :class:`moderngl.Texture`
	:param name: Owner name.
	:type name: :class:`str`
	:return: Created grid object.
	:rtype: :class:`bpy.types.Object`"""
	sub = bpy.context.scene.hydra.gen_subscale
	resX = math.ceil(txt.size[0] / sub)
	resY = math.ceil(txt.size[1] / sub)

	bpy.ops.mesh.primitive_grid_add(x_subdivisions=resX, y_subdivisions=resY, location=bpy.context.scene.cursor.location)
	act = bpy.context.active_object

	act.name = f"HYD_{name}_Landscape"
	act.hydra.is_generated = True

	for polygon in act.data.polygons:
		polygon.use_smooth = True
	return act