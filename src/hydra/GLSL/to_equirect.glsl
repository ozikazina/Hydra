#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D in_height;
layout(r32f) uniform image2D out_height;

uniform int offset_y = 0;
uniform bool flip_y = false;

uniform vec2 tile_mult = vec2(1, 1);

#define CAMERA_DIST -1
#define PI 3.14159265

void main(void) {
	vec2 pos = gl_GlobalInvocationID.xy * tile_mult * vec2(2 * PI, PI);
    if (flip_y) {
        pos.y = 0.5 * PI - pos.y;
    }
    else {
        pos.x = PI - pos.x;
        pos.x += pos.x < 0 ? 2 * PI : 0;
    }

    float mult = sin(pos.y) / (cos(pos.y) - CAMERA_DIST);
    vec2 coords = vec2(cos(pos.x) * mult, sin(pos.x) * mult);
    coords = (coords + vec2(1)) / 2;

    float h = texture(in_height, coords).r;

    imageStore(out_height, ivec2(gl_GlobalInvocationID.xy) + ivec2(0, offset_y), vec4(h));
}