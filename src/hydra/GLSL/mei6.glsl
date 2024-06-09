#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D s_sampler;
layout (rg32f) uniform image2D v_map;
layout (r32f) uniform image2D out_s_map;

uniform float dt = 0.25;

uniform bool diagonal = true;

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	mat2 rotation = mat2(
		1 / sqrt(2), -1 / sqrt(2),
		1 / sqrt(2), 1 / sqrt(2)
	);

	vec2 vel = imageLoad(v_map, pos).xy;

	vel *= dt;
	if (diagonal) {
		vel *= rotation;
	}

    vec2 vpos = (vec2(pos) - vel + vec2(0.5)) / imageSize(out_s_map);

	float s = texture(s_sampler, vpos).r;
    imageStore(out_s_map, pos, vec4(max(s, 0)));
}//main