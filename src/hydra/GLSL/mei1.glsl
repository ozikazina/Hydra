#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D d_map;

uniform float dt = 0.25;
uniform float Ke = 0.3;
uniform float Kr = 0.1;

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
	vec4 d = imageLoad(d_map, pos);

	d.x = d.x * (1 - dt * Ke) + dt * Kr;
	
	imageStore(d_map, pos, d);
}//main
