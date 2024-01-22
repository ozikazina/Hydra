#version 430

//location set in enity code
layout (location=0) in vec3 position;
out vec2 uv;

void main(void) {
	gl_Position = vec4(position, 1.0);
	uv = 0.5*position.xy + vec2(0.5); //-1..1 to 0..1
}