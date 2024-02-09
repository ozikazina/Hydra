#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D img;
layout (r32f) uniform image2D flow;

uniform int squareSize = 16;
uniform ivec2 off;

uniform int iterations = 50;
uniform float acceleration = 0.5;
uniform float maxVel = 2.0;
uniform float drag = 0.8;
uniform float strength = 0.10;

uniform bool interpolate = true;

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy)*squareSize + off;
	vec2 vel = vec2(0,0);
	vec2 pos = vec2(base) + vec2(0.5,0.5);
	ivec2 ipos = base;
			
	float heights[] = float[4](0,0,0,0);
	
	for (int i = 0; i < iterations; ++i) {

		heights[0] = imageLoad(img, ipos + ivec2(0,-1)).x;
		heights[1] = imageLoad(img, ipos + ivec2(-1,0)).x;
		heights[2] = imageLoad(img, ipos + ivec2(1,0)).x;
		heights[3] = imageLoad(img, ipos + ivec2(0,1)).x;
		
		float mn = min(min(heights[0],heights[1]), min(heights[2],heights[3]));
		
		float h = imageLoad(img, ipos).x;
		
		if (vel.x > 0) {
			vel.x += acceleration*(h-heights[2]);
		}
		else {
			vel.x -= acceleration*(h-heights[1]);
		}
		
		if (vel.y > 0) {
			vel.y += acceleration*(h-heights[3]);
		}
		else {
			vel.y -= acceleration*(h-heights[0]);
		}
		
		if (h < mn) break;
		
		vel *= drag;
		
		float len = length(vel);
		if (len == 0.0) break;
		
		vec2 norm = vel/len;
		if (len > maxVel) {
			len = maxVel;
			vel = norm * maxVel;
		}

		if (interpolate) {
			ivec2 corner = ivec2(pos-vec2(0.5,0.5));
			vec2 npos = pos - vec2(0.5,0.5) - vec2(corner);
			
			float sxy = imageLoad(flow, corner).x;
			float factor = strength * (1-npos.x) * (1-npos.y);
			imageStore(flow, corner, vec4(sxy * (1-factor) + factor));
			
			float sXy = imageLoad(flow, corner + ivec2(1,0)).x;
			factor = strength * npos.x * (1-npos.y);
			imageStore(flow, corner + ivec2(1,0), vec4(sXy * (1-factor) + factor));

			float sxY = imageLoad(flow, corner + ivec2(0,1)).x;
			factor = strength * (1-npos.x) * npos.y;
			imageStore(flow, corner + ivec2(0,1), vec4(sxY * (1-factor) + factor));
			
			float sXY = imageLoad(flow, corner + ivec2(1,1)).x;
			factor = strength * npos.x * npos.y;
			imageStore(flow, corner + ivec2(1,1), vec4(sXY * (1-factor) + factor));
		}
		else {
			vec4 vl = imageLoad(flow, ipos);
			vl.x = vl.x*(1-strength) + strength;
			imageStore(flow, ipos, vl);
		}
		
		pos += norm;
		ipos = ivec2(pos);
	}
}
