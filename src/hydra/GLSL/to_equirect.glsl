#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D in_height;
layout(r32f) uniform image2D out_height;

uniform int offset_y = 0;
uniform bool flip_y = false;

uniform vec2 tile_mult = vec2(1, 1);

#define PI 3.14159265

void main(void) {
	vec2 pos = gl_GlobalInvocationID.xy * tile_mult * vec2(2 * PI, PI);
    float strength;

    if (flip_y) {
        pos.y = 0.25 * PI - pos.y;
        pos.x += 0.5 * PI;
    }
    else {
        pos.x = 0.5 * PI - pos.x;
    }
    pos.x += pos.x < 0 ? 2 * PI : 0;

    strength = clamp(2 * (0.25 * PI - abs(pos.y)), 0, 1);

    float mult = tan(pos.y);
    vec2 coords = vec2(cos(pos.x) * mult, sin(pos.x) * mult);
    coords = (coords + vec2(1)) / 2; // Normalize to [0, 1]

    vec4 height = imageLoad(out_height, ivec2(gl_GlobalInvocationID.xy) + ivec2(0, offset_y));
    height = mix(height, texture(in_height, coords), strength);
    imageStore(out_height, ivec2(gl_GlobalInvocationID.xy) + ivec2(0, offset_y), height);
}