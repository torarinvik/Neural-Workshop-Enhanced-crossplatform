#version 330 core
in vec3 v_local;
uniform int hole_count;
uniform vec4 holes[96];
uniform int cut_holes;
void main() {
    if (cut_holes == 1) {
        for (int i = 0; i < 96; ++i) {
            if (i >= hole_count) break;
            if (length(v_local.xz - holes[i].xy) < holes[i].z) discard;
        }
    }
}
