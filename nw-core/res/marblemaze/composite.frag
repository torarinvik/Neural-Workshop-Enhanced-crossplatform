#version 330 core
in vec2 v_uv;
uniform sampler2D scene_texture;
out vec4 frag;
void main() { frag = texture(scene_texture, v_uv); }
