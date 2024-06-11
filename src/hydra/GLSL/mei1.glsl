#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D d_map;
layout (r32f) uniform image2D water_src;

uniform float dt = 0.25;
uniform float Ke = 0.3;
uniform float Kr = 0.1;

uniform bool use_water_src = false;
uniform int seed = 0;
uniform bool rainfall = true;

uint pcg(uint v)
{
	uint state = v * 747796405u + 2891336453u;
	uint word = ((state >> ((state >> 28u) + 4u)) ^ state) * 277803737u;
	return (word >> 22u) ^ word;
}

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
	vec4 d = imageLoad(d_map, pos);

	float kr;
	if (use_water_src) {
		kr = imageLoad(water_src, pos).x;
	}
	else if (rainfall) {
		kr = (pcg(uint(pos.x * 7877 + pos.y * 2833 + seed)) & 0xF) > 13 ? Kr : 0.0f;
	}
	else {
		kr = Kr;
	}

	d.x = d.x * (1 - dt * Ke) + dt * kr;
	
	imageStore(d_map, pos, d);
}//main
