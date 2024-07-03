#version 430

layout (location=0) in vec3 position;
uniform mat4 resize_matrix = mat4(1.0);

out vec4 pos;

uniform float offset_x = 0;

#define PI 3.14159265

void main(void) {
	vec4 npos = vec4(position, 1.0) * resize_matrix;

    vec3 dir = normalize(npos.xyz);

    float x = atan(dir.y, dir.x) / PI;
    float y = 2 * acos(-dir.z) / PI - 1;

    float h = length(npos.xyz);

    pos = vec4(h, 0, 0, 0);

	gl_Position = vec4(x + offset_x, y, -0.5 * h - float(abs(x) > 0.9), 1.0);
}