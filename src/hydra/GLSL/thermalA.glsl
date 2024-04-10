#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D mapH;
layout (r32f) uniform image2D offset;

uniform bool useOffset = false;

layout (rgba32f) uniform image2D requests;

uniform float bx = 1.0;
uniform float by = 1.0;

uniform float Ks = 0.5;

uniform float alpha = 0.005;

uniform bool diagonal = false;
uniform int ds = 1;

float getH(ivec2 pos) {
	if (useOffset) {
		return imageLoad(mapH, pos).x + imageLoad(offset, pos).x;
	}
	else {
		return imageLoad(mapH, pos).x;
	}
}

//  1y
//0x  2z
//  3w

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	float len = 1.0;
	
	float lx = (diagonal ? bx : bx * sqrt(2)) * ds;
	float ly = (diagonal ? by : by * sqrt(2)) * ds;
	
	float h = getH(base);

	vec4 p = vec4(0.0);

	float dh;

	dh = getH(base + ivec2(-ds, diagonal ? -ds : 0)) - h;
	p.x = dh + (dh > 0 ? -1 : 1) * alpha * lx;
	p.x *= int(abs(dh) > alpha * lx);

	dh = getH(base + ivec2(diagonal ? -ds : 0, ds)) - h;
	p.y = dh + (dh > 0 ? -1 : 1) * alpha * ly;
	p.y *= int(abs(dh) > alpha * ly);
	
	dh = getH(base + ivec2(ds, diagonal ? ds : 0)) - h;
	p.z = dh + (dh > 0 ? -1 : 1) * alpha * lx;
	p.z *= int(abs(dh) > alpha * lx);
	
	dh = getH(base + ivec2(diagonal ? ds : 0, -ds)) - h;
	p.w = dh + (dh > 0 ? -1 : 1) * alpha * ly;
	p.w *= int(abs(dh) > alpha * ly);
	
	vec4 d = 0.5 * (p + abs(p));	//positive part
	vec4 s = p - d;	//negative part

	float mx = max(max(d.x, d.y), max(d.z, d.w));

	h = imageLoad(mapH, base).x;
	//(Negative min) - can supply at most h material
	float mn = max(-h, min(min(s.x, s.y), min(s.z, s.w)));

	//clamp instead of min for NaNs
	float Cd = clamp(Ks * mx / (d.x + d.y + d.z + d.w), 0, 1);
	float Cs = clamp(Ks * mn / (s.x + s.y + s.z + s.w), 0, 1);

	vec4 ret = s * Cs + d * Cd;
	
	imageStore(requests, base, ret);
}
