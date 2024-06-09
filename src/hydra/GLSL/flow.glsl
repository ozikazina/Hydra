#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D height_sampler;
layout (r32f) uniform image2D flow;

uniform int squareSize = 16;
uniform ivec2 off;

uniform int lifetime = 50;
uniform float acceleration = 0.5;
uniform float max_velocity = 2.0;
uniform float drag = 0.8;
uniform float strength = 0.10;

void add_flow(vec2 pos) {
	pos -= vec2(0.5,0.5);
	vec2 factor = pos - floor(pos);
	ivec2 corner = ivec2(floor(pos));
	
	//X Y
	float f = strength * (1-factor.x) * (1-factor.y);
	float surf = imageLoad(flow, corner).x;
	imageStore(flow, corner, vec4(surf * (1-f) + f));
	
	//X+1 Y
	f = strength * factor.x * (1-factor.y);
	surf = imageLoad(flow, corner + ivec2(1,0)).x;
	imageStore(flow, corner + ivec2(1,0), vec4(surf * (1-f) + f));

	//X Y+1
	f = strength * (1-factor.x) * factor.y;
	surf = imageLoad(flow, corner + ivec2(0,1)).x;
	imageStore(flow, corner + ivec2(0,1), vec4(surf * (1-f) + f));
	
	//X+1 Y+1
	f = strength * factor.x * factor.y;
	surf = imageLoad(flow, corner + ivec2(1,1)).x;
	imageStore(flow, corner + ivec2(1,1), vec4(surf * (1-f) + f));
}

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy)*squareSize + off;
	vec2 vel = vec2(0,0);
	vec2 pos = vec2(base) + vec2(0.5,0.5);
	ivec2 ipos = base;
	
	float heights[] = float[4](0,0,0,0);
	
	for (int i = 0; i < lifetime; ++i) {

		heights[0] = imageLoad(height_sampler, ipos + ivec2(0,-1)).x;
		heights[1] = imageLoad(height_sampler, ipos + ivec2(-1,0)).x;
		heights[2] = imageLoad(height_sampler, ipos + ivec2(1,0)).x;
		heights[3] = imageLoad(height_sampler, ipos + ivec2(0,1)).x;
		
		float mn = min(min(heights[0],heights[1]), min(heights[2],heights[3]));
		
		float h = imageLoad(height_sampler, ipos).x;
		
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
		if (len > max_velocity) {
			len = max_velocity;
			vel = norm * max_velocity;
		}

		add_flow(pos);
		
		pos += norm;
		ipos = ivec2(pos);
	}
}
