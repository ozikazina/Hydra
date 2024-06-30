#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D mapH;
layout (rgba32f) uniform image2D requests;

layout (r32f) uniform image2D outH;

uniform int ds = 1;

uniform bool diagonal = false;

uniform ivec2 size = ivec2(512,512);

uniform bool tile_x = false;
uniform bool tile_y = false;

#define LEFT   (base + ivec2(-ds, diagonal ? -ds : 0))
#define RIGHT  (base + ivec2(ds, diagonal ? ds : 0))
#define UP     (base + ivec2(diagonal ? ds : 0, -ds))
#define DOWN   (base + ivec2(diagonal ? -ds : 0, ds))

ivec2 wrap(ivec2 pos) {
	if (tile_x) {
		pos.x += pos.x < 0 ? size.x : 0;
		pos.x -= pos.x >= size.x ? size.x : 0;
	}
	if (tile_y) {
		pos.y += pos.y < 0 ? size.y : 0;
		pos.y -= pos.y >= size.y ? size.y : 0;
	}
	return pos;
}

//  1y
//0x  2z
//  3w

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	float nh = imageLoad(mapH, base).x;
	vec4 request = imageLoad(requests, base);

	float inp, sw;

	inp = -imageLoad(requests, wrap(LEFT)).z;
	sw = inp < 0 ? -1 : 1;
	nh += (request.x * sw < inp * sw) ? request.x : inp;
	
	inp = -imageLoad(requests, wrap(UP)).w;
	sw = inp < 0 ? -1 : 1;
	nh += (request.y * sw < inp * sw) ? request.y : inp;
	
	inp = -imageLoad(requests, wrap(RIGHT)).x;
	sw = inp < 0 ? -1 : 1;
	nh += (request.z * sw < inp * sw) ? request.z : inp;
	
	inp = -imageLoad(requests, wrap(DOWN)).y;
	sw = inp < 0 ? -1 : 1;
	nh += (request.w * sw < inp * sw) ? request.w : inp;
	
	imageStore(outH, base, vec4(nh));
}
