#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

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

    float dE = Ks * (c - s);
    float dD = Kd * (c - s);

    float dif = c > s ? dE : dD;

    b -= dif;
    s += dif;
    b = max(b, 0.0);
    s = max(s, 0.0);

	imageStore(b_map, pos, vec4(b));
	imageStore(c_map, pos, vec4(s));
}//main
