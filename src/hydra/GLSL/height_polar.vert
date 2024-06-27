#version 430

layout (location=0) in vec3 position;
uniform mat4 resize_matrix = mat4(1.0);

out vec4 pos;

uniform float scale = 1;

#define CAMERA_POS vec3(0, 0, -1);

void main(void) {
	vec4 npos = vec4(position, 1.0) * resize_matrix;

    vec3 dif = normalize(npos.xyz) - CAMERA_POS;
    dif /= dif.z;

    float h = length(npos.xyz);

    pos = vec4(dif.x, dif.y, -h, 1.0);

	gl_Position = vec4(dif.x, dif.y, 0.1 * h, 1.0);
}