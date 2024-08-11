#version 430

out vec4 FragColor;
in vec4 pos;

uniform bool logarithmic = true;

void main(void) {
	FragColor = vec4(logarithmic ? log(pos.x) / 3.14159265 + 1 : pos.x, 0, 0, 1.0);
}