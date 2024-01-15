#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D mapH;
layout (rgba32f) uniform image2D requests;

layout (r32f) uniform image2D outH;

uniform bool diagonal = false;

float getH(ivec2 pos) {
	return imageLoad(mapH, pos).r;
}

//  1y
//0x  2z
//  3w

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	ivec2 neigh[4];
	if (diagonal) {
		neigh = ivec2[4](base + ivec2(-1,-1), base + ivec2(-1,1), base + ivec2(1,1), base + ivec2(1,-1));
	}
	else {
		neigh = ivec2[4](base + ivec2(-1,0), base + ivec2(0,1), base + ivec2(1,0), base + ivec2(0,-1));
	}
	
	vec4 oldH = imageLoad(mapH, base);
	
	float h = oldH.x;
	float nh = h;
	vec4 request = imageLoad(requests, base);

	//+ demand - request
	//- supply + request

	float inp;
	
	inp = imageLoad(requests, neigh[0]).z;
	if (inp < 0) {	//supply
		if (-inp > request.x) nh += request.x;
		else nh -= inp;
	}
	else {	//demand
		if (-inp < request.x) nh += request.x;
		else nh -= inp;
	}
	
	inp = imageLoad(requests, neigh[1]).w;
	if (inp < 0) {	//supply
		if (-inp > request.y) nh += request.y;
		else nh -= inp;
	}
	else {	//demand
		if (-inp < request.y) nh += request.y;
		else nh -= inp;
	}
	
	inp = imageLoad(requests, neigh[2]).x;
	if (inp < 0) {	//supply
		if (-inp > request.z) nh += request.z;
		else nh -= inp;
	}
	else {	//demand
		if (-inp < request.z) nh += request.z;
		else nh -= inp;
	}
	
	inp = imageLoad(requests, neigh[3]).y;
	if (inp < 0) {	//supply
		if (-inp > request.w) nh += request.w;
		else nh -= inp;
	}
	else {	//demand
		if (-inp < request.w) nh += request.w;
		else nh -= inp;
	}
	
	oldH.x = clamp(nh, 0, 1);
	
	imageStore(outH, base, oldH);
}
