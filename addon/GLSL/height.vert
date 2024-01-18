#version 430

layout (location=0) in vec3 position;
uniform mat4 resize_matrix = mat4(1.0);

out vec4 pos;

void main(void) {
	vec4 npos = vec4(position, 1.0) * resize_matrix;
	pos = npos;
	gl_Position = npos;
}