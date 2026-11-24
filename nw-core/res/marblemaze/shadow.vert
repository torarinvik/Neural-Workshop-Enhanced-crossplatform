#version 330 core
in vec3 position;
uniform mat4 light_clip;
uniform mat4 model;
out vec3 v_local;
void main() {
    v_local = position;
    gl_Position = light_clip * model * vec4(position, 1.0);
}
