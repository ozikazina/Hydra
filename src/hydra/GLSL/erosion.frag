#version 430

// layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

in vec4 gl_FragCoord;
out vec4 FragColor;

layout (r32f) uniform image2D img;
layout (r32f) uniform image2D depth;
layout (r32f) uniform image2D sediment;
layout (rgba32f) uniform image2D color;

uniform int square_size = 16;
uniform bool use_color = false;
uniform bool use_side_data = false;

uniform bool interpolate = true;
uniform bool interpolate_color = true;

uniform ivec2 off;

uniform int iterations = 50;
uniform float acceleration = 0.5;
uniform float erosion_strength = 0.25;
uniform float deposition_strength = 0.5;
uniform float max_velocity = 2.0;
uniform float drag = 0.8;
uniform float capacity_factor = 1e-2;

uniform float contrast_erode = 20.0;
uniform float contrast_deposit = 40.0;
uniform float color_strength = 0.8;

uniform float max_jump = 0.02;

float erode(vec2 pos, float amt, float h) {
	pos -= vec2(0.5,0.5);
	ivec2 corner = ivec2(pos);
	vec2 factor = pos - vec2(corner);
	float ret = 0;

	float sxy = imageLoad(img, corner).x;
	float f = float(sxy > h) * (1-factor.x) * (1-factor.y);
	imageStore(img, corner, vec4(sxy - amt * f));
	ret += f;
	
	float sXy = imageLoad(img, corner + ivec2(1,0)).x;
	f = float(sXy > h) * factor.x * (1-factor.y);
	imageStore(img, corner + ivec2(1,0), vec4(sXy - amt * f));
	ret += f;
	
	float sxY = imageLoad(img, corner + ivec2(0,1)).x;
	f = float(sxY > h) * (1-factor.x) * factor.y;
	imageStore(img, corner + ivec2(0,1), vec4(sxY - amt * f));
	ret += f;
	
	float sXY = imageLoad(img, corner + ivec2(1,1)).x;
	f = float(sXY > h) * factor.x * factor.y;
	imageStore(img, corner + ivec2(1,1), vec4(sXY - amt * f));
	ret += f;

	return amt * ret;
}

void colorize(vec2 pos, vec4 col) {
	pos -= vec2(0.5,0.5);
	ivec2 corner = ivec2(pos);
	vec2 factor = pos - vec2(corner);
	
	vec4 sxy = imageLoad(color, corner);
	float f = color_strength * (1-factor.x) * (1-factor.y);
	imageStore(color, corner, sxy * (1-f) + col * f);
	
	vec4 sXy = imageLoad(color, corner + ivec2(1,0));
	f = color_strength * factor.x * (1-factor.y);
	imageStore(color, corner + ivec2(1,0), sXy * (1-f) + col * f);
	
	vec4 sxY = imageLoad(color, corner + ivec2(0,1));
	f = color_strength * (1-factor.x) * factor.y;
	imageStore(color, corner + ivec2(0,1), sxY * (1-f) + col * f);
	
	vec4 sXY = imageLoad(color, corner + ivec2(1,1));
	f = color_strength * factor.x * factor.y;
	imageStore(color, corner + ivec2(1,1), sXY * (1-f) + col * f);
}

void main(void) {
	float heights[] = float[4](0,0,0,0);
	ivec2 base = ivec2(gl_FragCoord.xy) * square_size + off;
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
		float mn = min(min(heights[0],heights[1]), min(heights[2],heights[3]));
		
		float h = imageLoad(img, ipos).x;
		
		float hdif = vel.x > 0 ? h-heights[2] : heights[1]-h;
		vel.x += acceleration * hdif * float(abs(hdif) <= max_jump);
		
		hdif = vel.y > 0 ? h-heights[3] : heights[0]-h;
		vel.y += acceleration * hdif * float(abs(hdif) <= max_jump);

		vel *= float(h >= mn);
		vel *= drag;
		
		float len = length(vel);
		vec2 norm = len == 0 ? vel : vel/len;
		len = min(len, max_velocity);
		vel = norm * len;

		capacity = capacity_factor * len;

		float dif = capacity-saturation;
		
		float mx = max(max(heights[0],heights[1]), max(heights[2],heights[3]));

		if (dif > 0) {	//erode
			dif *= erosion_strength;
			
			if (h > mn) {
				add = min(dif, h-mn);
				if (interpolate)
					add = erode(pos, add, mn);
				else {
					h -= add;	//Otherwise done in interpolated erode function
					imageStore(img, ipos, vec4(max(h,0),0,0,1));
				}
				saturation += add;
				if (use_color) {
					col = color_strength * imageLoad(color, ipos) + (1 - color_strength)*col;
				}
				if (use_side_data) {
					vec4 dp = imageLoad(depth, ipos);
					imageStore(depth, ipos, dp + contrast_erode*add);
				}
			}
		}
		else if (h < mx) {	//deposit
			dif *= deposition_strength;
			
			add = min(-dif, mx-h);
			h += add;
			imageStore(img, ipos, vec4(h,0,0,1));
			saturation -= add;
			
			if (use_color) {
				if (interpolate_color) {
					colorize(pos, col);
				}
				else {
					vec4 ncol = (1 - color_strength) * imageLoad(color, ipos) + color_strength * col;
					imageStore(color, ipos, ncol);
				}
			}
			if (use_side_data) {
				vec4 sed = imageLoad(sediment, ipos);
				imageStore(sediment, ipos, sed + contrast_deposit*add);
			}
		}
		pos += norm;
		ipos = ivec2(pos);
		
		if (pos.x <= 0 || pos.y <= 0) break;
	}//i loop

	FragColor = vec4(0, 0, 0, 1);
}//main
