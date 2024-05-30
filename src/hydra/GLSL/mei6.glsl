#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D s_sampler;
uniform sampler2D color_sampler;
layout (rg32f) uniform image2D v_map;
layout (r32f) uniform image2D out_s_map;
layout (rgba32f) uniform image2D out_color_map;

uniform float dt = 0.25;

uniform bool diagonal = true;

uniform bool use_color = false;
uniform float color_mixing = 0.25;

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	mat2 rotation = mat2(
		1 / sqrt(2), -1 / sqrt(2),
		1 / sqrt(2), 1 / sqrt(2)
	);

	vec2 vpos = dt * imageLoad(v_map, pos).xy;
	if (diagonal) {
		vpos *= rotation;
	}

    vpos = (vec2(pos) - vpos + vec2(0.5)) / imageSize(out_s_map);

	float s = texture(s_sampler, vpos).r;
    imageStore(out_s_map, pos, vec4(max(s, 0)));

	if (use_color) {
		vec4 new_color = texture(color_sampler, vpos);
		vec4 current_color = texture(color_sampler, (vec2(pos) + vec2(0.5)) / imageSize(out_color_map));
		imageStore(out_color_map, pos, new_color * color_mixing + current_color * (1 - color_mixing));
	}
}//main