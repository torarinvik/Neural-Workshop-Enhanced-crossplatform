in vec3 world_position;
in vec3 world_normal;
in vec4 shadow_position;

uniform vec3 tint;
uniform vec3 eye;
uniform vec3 light_dir;
uniform vec3 light_colour;
uniform vec3 sky_colour;
uniform vec3 ground_colour;
uniform sampler2D shadow_map;
uniform float shadow_texel;

out vec4 frag;

float shadowed(vec3 n, vec3 l) {
    if (shadow_position.w <= 0.0) return 1.0;
    vec3 c = shadow_position.xyz / shadow_position.w;
    if (c.x < 0.0 || c.x > 1.0 || c.y < 0.0 || c.y > 1.0 || c.z > 1.0)
        return 1.0;

    float slope = clamp(1.0 - dot(n, l), 0.0, 1.0);
    float bias = 0.0009 + 0.0042 * slope * slope;
    float lit = 0.0;
    for (int y = -1; y <= 1; ++y) {
        for (int x = -1; x <= 1; ++x) {
            vec2 at = c.xy + vec2(float(x), float(y)) * shadow_texel;
            lit += c.z - bias <= texture(shadow_map, at).r ? 1.0 : 0.0;
        }
    }
    return lit / 9.0;
}

void main() {
    vec3 n = normalize(world_normal);
    if (!gl_FrontFacing) n = -n;
    vec3 l = normalize(light_dir);
    vec3 view = normalize(eye - world_position);
    vec3 half_way = normalize(l + view);
    float ndl = max(dot(n, l), 0.0);
    float lit = shadowed(n, l);
    vec3 ambient = mix(ground_colour, sky_colour, n.y * 0.5 + 0.5);
    float spec = pow(max(dot(n, half_way), 0.0), 24.0) * 0.10;
    vec3 colour = tint * (ambient * 0.42 + light_colour * ndl * lit * 0.85)
                + light_colour * spec * lit;
    frag = vec4(clamp(colour, 0.0, 1.0), 1.0);
}
