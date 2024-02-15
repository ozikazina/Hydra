#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D mapH;
layout (rgba32f) uniform image2D requests;

layout (r32f) uniform image2D outH;

uniform bool diagonal = false;

//  1y
//0x  2z
//  3w

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	float nh = imageLoad(mapH, base).x;
	vec4 request = imageLoad(requests, base);

	float inp, sw;
	
	inp = -imageLoad(requests, base + ivec2(-1, diagonal ? -1 : 0)).z;
	sw = inp < 0 ? -1 : 1;
	nh += (request.x * sw < inp * sw) ? request.x : inp;
	
	inp = -imageLoad(requests, base + ivec2(diagonal ? -1 : 0, 1)).w;
	sw = inp < 0 ? -1 : 1;
	nh += (request.y * sw < inp * sw) ? request.y : inp;
	
	inp = -imageLoad(requests, base + ivec2(1, diagonal ? 1 : 0)).x;
	sw = inp < 0 ? -1 : 1;
	nh += (request.z * sw < inp * sw) ? request.z : inp;
	
	inp = -imageLoad(requests, base + ivec2(diagonal ? 1 : 0, -1)).y;
	sw = inp < 0 ? -1 : 1;
	nh += (request.w * sw < inp * sw) ? request.w : inp;
	
	// nh = max(nh, 0);
	
	imageStore(outH, base, vec4(nh));
}
