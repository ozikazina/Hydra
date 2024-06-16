#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D color_sampler;
layout (rgba32f) uniform image2D color_map;
uniform sampler2D v_sampler;
layout (rg32f) uniform image2D v_map;
layout (rgba32f) uniform image2D out_color_map;

uniform float dt = 0.25;

uniform float color_scaling = 0.05;
uniform float color_min = 0.05;
uniform float color_max = 0.9;

uniform vec2 tile_mult = vec2(1/512, 1/512);

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	vec2 vel = imageLoad(v_map, pos).xy;
	float color_factor = clamp(
		(vel.x * vel.x + vel.y * vel.y) * color_scaling,	//non-linear scaling
		color_min, color_max
	);

    vec2 vpos = vec2(pos) - dt * vel;

	vel = texture(v_sampler, (vpos + vec2(0.5)) * tile_mult).xy;
	vec2 vpos2 = vpos + dt * vel;

	vpos += 0.5 * (vec2(pos) - vpos2);

    vec4 new_color = texture(color_sampler, (vpos + vec2(0.5)) * tile_mult);
    vec4 current_color = imageLoad(color_map, pos);

    imageStore(out_color_map, pos, new_color * color_factor + current_color * (1 - color_factor));
}//main