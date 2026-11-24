layout(location = 0) in vec3 position;

uniform mat4 light_clip;
uniform mat4 model;

void main() {
    gl_Position = light_clip * model * vec4(position, 1.0);
}
