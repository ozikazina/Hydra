#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D mapH;

layout (rgba32f) uniform image2D requests;

uniform float bx = 1.0;
uniform float by = 1.0;

uniform float Ks = 0.5;

uniform float alpha = 0.005;

uniform bool diagonal = false;

float getH(ivec2 pos) {
	return imageLoad(mapH, pos).x;
}

//  1y
//0x  2z
//  3w

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	float len = 1.0;
	
	float lx = bx;
	float ly = by;
	
	ivec2 neigh[4];
	
	if (diagonal) {
		neigh =  ivec2[4](base + ivec2(-1,-1), base + ivec2(-1,1), base + ivec2(1,1), base + ivec2(1,-1));
		lx *= sqrt(2);
		ly *= sqrt(2);
	}
	else {
		neigh = ivec2[4](base + ivec2(-1,0), base + ivec2(0,1), base + ivec2(1,0), base + ivec2(0,-1));
	}
	
	float h = getH(base);
	
	vec4 s = vec4(0.0);
	vec4 d = vec4(0.0);

	float dh;

	dh = getH(neigh[0]);
	if (abs(dh - h) > alpha * lx) {
		if (dh > h) d.x = dh - h - alpha * lx;	//demand
		else s.x = dh - h + alpha * lx;	//supply
	}

	dh = getH(neigh[1]);
	if (abs(dh - h) > alpha * ly) {
		if (dh > h) d.y = dh - h - alpha * ly;
		else s.y = dh - h + alpha * ly;
	}
	
	dh = getH(neigh[2]);
	if (abs(dh - h) > alpha * lx) {
		if (dh > h) d.z = dh - h - alpha * lx;
		else s.z = dh - h + alpha * lx;
	}
	
	dh = getH(neigh[3]);
	if (abs(dh - h) > alpha * ly) {
		if (dh > h) d.w = dh - h - alpha * lx;
		else s.w = dh - h + alpha * ly;
	}
	
	float mx = max(max(d.x, d.y), max(d.z, d.w));
	float mn = min(min(s.x, s.y), min(s.z, s.w));

	float Cd = clamp(Ks * mx / (d.x + d.y + d.z + d.w), 0, 1);
	float Cs = clamp(Ks * mn / (s.x + s.y + s.z + s.w), 0, 1);
	
	vec4 ret = s * Cs + d * Cd;
	
	imageStore(requests, base, ret);
}
