#version 430

in vec4 gl_FragCoord;
out vec4 FragColor;

layout (r32f) uniform image2D img;
layout (r32f) uniform image2D depth;
layout (r32f) uniform image2D sediment;
layout (rgba32f) uniform image2D color;

uniform int squareSize = 16;
uniform bool useColor = false;
uniform bool useSideData = false;

uniform bool interpolate = true;
uniform bool interpolateColor = true;

uniform ivec2 off;

uniform int iterations = 50;
uniform float acceleration = 0.5;
uniform float bite = 0.25;	//erosion strength
uniform float release = 0.5;	//deposition strength
uniform float maxVel = 2.0;
uniform float drag = 0.8;
uniform float capacityFactor = 1e-2;

uniform float contrastErode = 20;
uniform float contrastDeposit = 40;
uniform float colorStrength = 0.8;

uniform float maxJump = 0.02;

float erode(vec2 pos, float amt, float h) {
	pos -= vec2(0.5,0.5);
	ivec2 corner = ivec2(pos);
	vec2 npos = pos - vec2(corner);
	float ret = 0;
	float sxy = imageLoad(img, corner).x;
	if (sxy > h) {
		imageStore(img, corner, vec4(sxy - amt * (1-npos.x) * (1-npos.y)));
		ret += (1-npos.x) * (1-npos.y);
	}
	
	float sXy = imageLoad(img, corner + ivec2(1,0)).x;
	if (sXy > h) {
		imageStore(img, corner + ivec2(1,0), vec4(sXy - amt * npos.x * (1-npos.y)));
		ret += npos.x * (1-npos.y);
	}
	
	float sxY = imageLoad(img, corner + ivec2(0,1)).x;
	if (sxY > h) {
		imageStore(img, corner + ivec2(0,1), vec4(sxY - amt * (1-npos.x) * npos.y));
		ret += (1-npos.x) * npos.y;
	}
	
	float sXY = imageLoad(img, corner + ivec2(1,1)).x;
	if (sXY > h) {
		imageStore(img, corner + ivec2(1,1), vec4(sXY - amt * npos.x * npos.y));
		ret += npos.x * npos.y;
	}

	return amt * ret;
}

void colorize(vec2 pos, vec4 col) {
	pos -= vec2(0.5,0.5);
	ivec2 corner = ivec2(pos);
	vec2 npos = pos - vec2(corner);
	
	vec4 sxy = imageLoad(color, corner);
	float factor = colorStrength * (1-npos.x) * (1-npos.y);
	imageStore(color, corner, sxy * (1-factor) + col * factor);
	
	vec4 sXy = imageLoad(color, corner + ivec2(1,0));
	factor = colorStrength * npos.x * (1-npos.y);
	imageStore(color, corner + ivec2(1,0), sXy * (1-factor) + col * factor);
	
	vec4 sxY = imageLoad(color, corner + ivec2(0,1));
	factor = colorStrength * (1-npos.x) * npos.y;
	imageStore(color, corner + ivec2(0,1), sxY * (1-factor) + col * factor);
	
	vec4 sXY = imageLoad(color, corner + ivec2(1,1));
	factor = colorStrength * npos.x * npos.y;
	imageStore(color, corner + ivec2(1,1), sXY * (1-factor) + col * factor);
}

void main(void) {
	float heights[] = float[4](0,0,0,0);
	ivec2 base = ivec2(gl_FragCoord.xy) * squareSize + off;
	vec2 vel = vec2(0,0);
	vec2 pos = vec2(base) + vec2(0.5,0.5);
	float capacity = 0.0;
	float saturation = 0;
	float add = 0;
	ivec2 ipos = base;
	vec4 col = imageLoad(color, ipos);
	
	for (int i = 0; i < iterations; ++i) {
		heights[0] = imageLoad(img, ipos + ivec2(0,-1)).x;
		heights[1] = imageLoad(img, ipos + ivec2(-1,0)).x;
		heights[2] = imageLoad(img, ipos + ivec2(1,0)).x;
		heights[3] = imageLoad(img, ipos + ivec2(0,1)).x;
		
		float mx = max(max(heights[0],heights[1]), max(heights[2],heights[3]));
		float mn = min(min(heights[0],heights[1]), min(heights[2],heights[3]));
		
		float h = imageLoad(img, ipos).x;
		
		if (vel.x > 0) {
			float hdif = h-heights[2];
			if (hdif <= maxJump)
				vel.x += acceleration*hdif;
		}
		else {
			float hdif = h-heights[1];
			if (hdif <= maxJump)
				vel.x -= acceleration*hdif;
		}
		
		if (vel.y > 0) {
			float hdif = h-heights[3];
			if (hdif <= maxJump)
				vel.y += acceleration*hdif;
		}
		else {
			float hdif = h-heights[0];
			if (hdif <= maxJump)
				vel.y -= acceleration*hdif;
		}
		
		if (h < mn) vel = vec2(0,0);
		
		vel *= drag;
		
		float len = length(vel);
		vec2 norm = len == 0 ? vel : vel/len;
		if (len > maxVel) {
			len = maxVel;
			vel = norm * maxVel;
		}

		capacity = capacityFactor*len;

		float dif = capacity-saturation;
		
		h = imageLoad(img, ipos).x;
		
		if (dif > 0) {	//erode
			dif *= bite;
			
			if (h > mn) {
				add = min(dif, h-mn);
				if (interpolate)
					add = erode(pos, add, mn);
				else {
					h -= add;	//Otherwise done in interpolated erode function
					imageStore(img, ipos, vec4(max(h,0),0,0,1));
				}
				saturation += add;
				if (useColor) {
					col = colorStrength * imageLoad(color, ipos) + (1 - colorStrength)*col;
				}
				if (useSideData) {
					vec4 dp = imageLoad(depth, ipos);
					imageStore(depth, ipos, dp + contrastErode*add);
				}
			}
		}
		else if (h < mx) {	//deposit
			dif *= release;
			
			add = min(-dif, mx-h);
			h += add;
			imageStore(img, ipos, vec4(h,0,0,1));
			saturation -= add;
			
			if (useColor) {
				if (interpolateColor) {
					colorize(pos, col);
				}
				else {
					vec4 ncol = (1 - colorStrength) * imageLoad(color, ipos) + colorStrength * col;
					imageStore(color, ipos, ncol);
				}
			}
			if (useSideData) {
				vec4 sed = imageLoad(sediment, ipos);
				imageStore(sediment, ipos, sed + contrastDeposit*add);
			}
		}
		pos += norm;
		ipos = ivec2(pos);
		
		if (pos.x <= 0 || pos.y <= 0) break;
	}//i loop

	FragColor = vec4(0, 0, 0, 1);
}//main
