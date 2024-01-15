#version 460

out vec4 FragColor;
in vec4 pos;

void main(void) {
	FragColor = vec4(1-pos.z);
}