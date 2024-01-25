#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D b_map;
layout (r32f) uniform image2D s_map;
layout (r32f) uniform image2D c_map;    //capacity -> new sediment

uniform float Ks = 0.25;
uniform float Kd = 0.25;

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	float c = imageLoad(c_map, pos).x;
    float b = imageLoad(b_map, pos).x;
    float s = imageLoad(s_map, pos).x;

    float bE = b - Ks * (c - s);
    float sE = s + Ks * (c - s);
    float bD = b + Kd * (s - c);
    float sD = s - Kd * (s - c);

    b = c > s ? bE : bD;
    b = max(b, 0.0);
    s = c > s ? sE : sD;
	imageStore(b_map, pos, vec4(b));
	imageStore(c_map, pos, vec4(s));
}//main
