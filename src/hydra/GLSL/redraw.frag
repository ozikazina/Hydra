#version 430

uniform sampler2D source; 
uniform bool linearize = false;

in vec2 uv;
out vec4 FragColor;

float toLinear(float C) {
	if (C <= 0.04045)
		return C / 12.92;
	else
		return pow(((C + 0.055) / 1.055), 2.4);
}

void main(void) {
	FragColor = texture(source, uv);
	if (linearize) {
		FragColor.x = toLinear(FragColor.x);
		FragColor.y = toLinear(FragColor.y);
		FragColor.z = toLinear(FragColor.z);
	}
}