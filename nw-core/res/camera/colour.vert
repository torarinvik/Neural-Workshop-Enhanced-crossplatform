layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;

uniform mat4 view_proj;
uniform mat4 model;
uniform vec3 normal_scale;
uniform mat4 light_matrix;

out vec3 world_position;
out vec3 world_normal;
out vec4 shadow_position;

void main() {
    vec4 world = model * vec4(position, 1.0);
    world_position = world.xyz;
    world_normal = mat3(model) * (normal * normal_scale);
    shadow_position = light_matrix * world;
    gl_Position = view_proj * world;
}
