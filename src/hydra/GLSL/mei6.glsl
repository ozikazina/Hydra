#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D s_sampler;

layout (rg32f) uniform image2D v_map;
layout (r32f) uniform image2D out_s_map;

uniform float dt = 0.25;

uniform vec2 tile_mult = vec2(1/512, 1/512);

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	vec2 vel = dt * imageLoad(v_map, pos).xy;
    vec2 vpos = vec2(pos) - vel;

	float s = texture(s_sampler, (vpos + vec2(0.5)) * tile_mult).r;
    imageStore(out_s_map, pos, vec4(max(s, 0)));
}//main