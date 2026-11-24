#version 330 core
in vec3 position;
in vec3 normal;
uniform mat4 view_proj;
uniform mat4 model;
out vec3 v_world;
out vec3 v_normal;
out vec3 v_local;
out vec4 v_shadow;
uniform mat4 light_matrix;
void main() {
    vec4 world = model * vec4(position, 1.0);
    v_world = world.xyz;
    v_normal = mat3(model) * normal;
    v_local = position;
    v_shadow = light_matrix * world;
    gl_Position = view_proj * world;
}
