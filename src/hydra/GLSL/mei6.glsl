#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D s_alt_map;
layout (rg32f) uniform image2D v_map;
layout (r32f) uniform image2D s_map;

uniform float dt = 0.25;

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	mat2 adj = mat2(
		1 / sqrt(2), -1 / sqrt(2),
		1 / sqrt(2), 1 / sqrt(2)
	);

    vec2 vpos = vec2(pos) - dt * imageLoad(v_map, pos).xy * adj;
	ivec2 corner = ivec2(vpos);
	vec2 factor = vpos - vec2(corner);

    float s = 0;
	s += (1 - factor.x) * (1 - factor.y) * imageLoad(s_map, corner).r;
	s += (factor.x) * (1 - factor.y) * imageLoad(s_map, corner + ivec2(1,0)).r;
	s += (1 - factor.x) * (factor.y) * imageLoad(s_map, corner + ivec2(0,1)).r;
	s += (factor.x) * (factor.y) * imageLoad(s_map, corner + ivec2(1,1)).r;

    imageStore(s_alt_map, pos, vec4(max(s, 0)));
}//main