#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D height_map;
layout (rgba32f) uniform image2D color_map;

uniform int square_size = 4;

uniform float erosion_strength = 0.25;

uniform float acceleration = 0.5;
uniform float max_velocity = 2.0;
uniform int lifetime = 25;
uniform int iterations = 10;
uniform float drag = 0.8;

uniform float color_strength = 0.8;

void colorize(vec2 pos, vec4 col, float strength) {
	pos -= vec2(0.5,0.5);
	vec2 factor = pos - floor(pos);
	ivec2 corner = ivec2(floor(pos)); //has to have floor

	//X Y
	float f = strength * (1-factor.x) * (1-factor.y);
	vec4 surf_color = imageLoad(color_map, corner);
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, corner, surf_color);

	//X+1 Y
	f = strength * factor.x * (1-factor.y);
	surf_color = imageLoad(color_map, corner + ivec2(1,0));
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, corner + ivec2(1,0), surf_color);
	
	//X Y+1
	f = strength * (1-factor.x) * factor.y;
	surf_color = imageLoad(color_map, corner + ivec2(0,1));
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, corner + ivec2(0,1), surf_color);
	
	//X+1 Y+1
	f = strength * factor.x * factor.y;
	surf_color = imageLoad(color_map, corner + ivec2(1,1));
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, corner + ivec2(1,1), surf_color);
}

void erode(int x, int y) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy) * square_size + ivec2(x, y);
	
	vec2 vel = vec2(0, 0);
	vec2 pos = vec2(base) + vec2(0.5, 0.5);
	vec2 dir = vec2(1, 0);
	float capacity = 0.0;
	float saturation = 0;

	ivec2 ipos = base;
	vec4 col = imageLoad(color_map, ipos);
	
	for (int i = 0; i < lifetime; ++i) {
		float h = imageLoad(height_map, ipos).x;
		ivec2 npos = ivec2(pos + dir);
		float height_vel = imageLoad(height_map, npos).x;

		npos = ivec2(pos + vec2(-dir.y, dir.x));
		float height_dir = imageLoad(height_map, npos).x;

		vel += acceleration * (
			(h - height_vel) * dir +
			(h - height_dir) * vec2(-dir.y, dir.x)
		);

		float len = min(length(vel), max_velocity);
		dir = normalize(vel);
		vel = dir * len;

		float dif = len-saturation;
		
		dif *= dif > 0 ? erosion_strength : 1.0;
		saturation += dif;
		col = mix(col, imageLoad(color_map, ipos), (1 - color_strength) * float(dif > 0));
		
        // branching is faster than writing every time
		if (dif <= 0) {
			colorize(pos, col, color_strength);
		}

		pos += dir;
		ipos = ivec2(pos);

		vel *= drag;
	}//lifetime loop
}

void main(void) {
	for (int i = 0; i < iterations; ++i) {
		for (int y = 0; y < square_size; ++y) {
			for (int x = 0; x < square_size; ++x) {
				erode(x, y);		
			}
		}
	}
}