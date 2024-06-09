#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D color_sampler;
layout (rg32f) uniform image2D v_map;
layout (rgba32f) uniform image2D out_color_map;

uniform float dt = 0.25;

uniform bool diagonal = true;

uniform float color_scaling = 0.05;
uniform float color_min = 0.05;
uniform float color_max = 0.9;

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	mat2 rotation = mat2(
		1 / sqrt(2), -1 / sqrt(2),
		1 / sqrt(2), 1 / sqrt(2)
	);

	vec2 vel = imageLoad(v_map, pos).xy;
	float color_factor = clamp(
		(vel.x * vel.x + vel.y * vel.y) * color_scaling,	//non-linear scaling
		color_min, color_max
	);

	vel *= dt;
	if (diagonal) {
		vel *= rotation;
	}

    vec2 vpos = (vec2(pos) - vel + vec2(0.5)) / imageSize(out_color_map);

    vec4 new_color = texture(color_sampler, vpos);
    vec4 current_color = texture(color_sampler,
        (vec2(pos) + vec2(0.5)) / imageSize(out_color_map)
    );
    imageStore(out_color_map, pos, new_color * color_factor + current_color * (1 - color_factor));

}//main