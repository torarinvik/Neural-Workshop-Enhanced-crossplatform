#version 330 core
in vec3 v_world;
in vec3 v_normal;
in vec3 v_local;
uniform vec3 eye;
uniform vec3 light_direction;
uniform vec3 light_colour;
uniform vec3 sky_colour;
uniform vec3 ground_colour;
uniform vec3 tint;
uniform int material;
uniform mat4 model;
uniform int cut_holes;
uniform int hole_count;
uniform vec4 holes[96];
uniform float grain_seed;
uniform sampler2D shadow_map;
uniform sampler2D marble_colour;
uniform sampler2D marble_rough;
uniform sampler2D marble_normal;
uniform float shadow_texel;
uniform int shadows;
in vec4 v_shadow;
out vec4 frag;

float hash3(vec3 p) {
    return fract(sin(dot(p, vec3(17.13, 91.7, 47.31))) * 43758.5453);
}
float value_noise(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    f *= f * (3.0 - 2.0 * f);
    float a = mix(hash3(i), hash3(i + vec3(1,0,0)), f.x);
    float b = mix(hash3(i + vec3(0,1,0)), hash3(i + vec3(1,1,0)), f.x);
    float c = mix(hash3(i + vec3(0,0,1)), hash3(i + vec3(1,0,1)), f.x);
    float d = mix(hash3(i + vec3(0,1,1)), hash3(i + vec3(1,1,1)), f.x);
    return mix(mix(a,b,f.y), mix(c,d,f.y), f.z);
}
float fbm(vec3 p) {
    return 0.5*value_noise(p) + 0.25*value_noise(p*2.03)
         + 0.155*value_noise(p*4.01) + 0.075*value_noise(p*8.05);
}
float shadowed(vec3 n, vec3 l) {
    if (shadows == 0 || v_shadow.w <= 0.0) return 1.0;
    vec3 c = v_shadow.xyz / v_shadow.w;
    if (c.x < 0.0 || c.x > 1.0 || c.y < 0.0 || c.y > 1.0 || c.z > 1.0) return 1.0;
    float slope = clamp(1.0 - dot(n, l), 0.0, 1.0);
    float bias = 0.0009 + 0.0042 * slope * slope;
    float lit = 0.0;
    for (int j = -1; j <= 1; ++j) {
        for (int i = -1; i <= 1; ++i) {
            float nearest = texture(shadow_map, c.xy + vec2(float(i), float(j)) * shadow_texel).r;
            lit += (c.z - bias <= nearest) ? 1.0 : 0.0;
        }
    }
    return lit / 9.0;
}
void main() {
    float coverage = 1.0;
    if (cut_holes == 1) {
        float edge = 1e9;
        for (int i = 0; i < 96; ++i) {
            if (i >= hole_count) break;
            edge = min(edge, length(v_local.xz - holes[i].xy) - holes[i].z);
        }
        float fade = max(fwidth(edge), 1e-6);
        coverage = clamp(edge / fade + 0.5, 0.0, 1.0);
        if (coverage <= 0.0) discard;
    }
    vec3 n = normalize(v_normal);
    if (!gl_FrontFacing) n = -n;
    vec3 l = normalize(light_direction);
    vec3 view = normalize(eye - v_world);
    float diffuse = max(dot(n,l), 0.0);
    float lit = shadowed(n, l);
    vec3 ambient = mix(ground_colour, sky_colour,
                       n.y*0.5+0.5);
    vec3 base = tint;
    float specular = 0.10;
    float gloss = 24.0;
    float ambient_strength = 0.42;
    if (material == 0 || material == 1) {
        vec3 p = v_local;
        vec2 about = vec2(p.x + 0.16 + grain_seed*0.05, p.y + 0.19);
        float rings = length(about)*190.0
            + 9.0*fbm(p*vec3(4.0,4.0,1.6))
            + 2.2*fbm(p*vec3(17.0,17.0,6.0));
        float band = fract(rings);
        float grain = smoothstep(0.24,0.44,band)*(1.0-smoothstep(0.52,0.80,band));
        float blotch = fbm(p*vec3(9.0,9.0,3.5))-0.5;
        float fibre = fbm(p*vec3(380.0,380.0,30.0))-0.5;
        vec3 dark = tint * (material == 0 ? vec3(0.55,0.44,0.34)
                                          : vec3(0.42,0.36,0.32));
        base = clamp(mix(tint, dark,
                    clamp(grain*0.52+blotch*0.24+0.09,0.0,1.0))
                    *(1.0+fibre*0.12),0.0,1.0);
        gloss = material == 0 ? 40.0 : 28.0;
        specular = material == 0 ? 0.16 : 0.11;
    } else if (material == 2) {
        vec3 ball = normalize(v_local), bumped = n, shine = tint;
        float polish = 1.0;
        vec2 uv = vec2(atan(ball.z,ball.x)*0.1591549+0.5,
                       acos(clamp(ball.y,-1.0,1.0))*0.3183099);
        float grain = dot(texture(marble_colour,uv).rgb,vec3(0.299,0.587,0.114));
        shine = tint*(0.70+0.88*grain);
        polish = 1.0-texture(marble_rough,uv).g;
        vec3 across = normalize(vec3(-ball.z,0.0,ball.x)+vec3(1e-6,0.0,0.0));
        vec3 down = cross(ball,across);
        vec3 bump = texture(marble_normal,uv).xyz*2.0-1.0;
        vec3 local = normalize(across*bump.x+down*bump.y+ball*bump.z);
        bumped = normalize(mat3(model)*mix(ball,local,0.22));
        vec3 bounce = reflect(-view,bumped);
        float tight = mix(26.0,190.0,polish);
        float lamp = pow(max(dot(bounce,l),0.0),tight);
        float sheen = pow(max(dot(bounce,l),0.0),9.0);
        float fresnel = 0.05+0.95*pow(1.0-max(dot(bumped,view),0.0),5.0);
        vec3 above = mix(sky_colour*0.28,sky_colour*0.78,
                         clamp(bounce.y*1.8,0.0,1.0));
        vec3 below = ground_colour*(0.20+0.58*clamp(-bounce.y*2.4,0.0,1.0));
        vec3 environment = mix(below,above,smoothstep(-0.035,0.035,bounce.y));
        vec3 colour = shine*environment*(0.34+0.66*lit)
            +light_colour*lamp*2.8*lit+light_colour*sheen*0.14*lit
            +sky_colour*fresnel*0.16;
        frag = vec4(clamp(colour,0.0,1.0),coverage);
        return;
    } else if (material == 3) {
        float depth = clamp(1.0+v_local.y*26.0,0.0,1.0);
        frag = vec4(clamp(tint*(0.05+0.10*ambient+0.92*diffuse*lit)*depth*depth,0.0,1.0),coverage);
        return;
    } else if (material == 4) {
        gloss = 60.0;
        specular = 0.22;
        ambient_strength = 0.5;
    }
    float shine = pow(max(dot(n,normalize(l+view)),0.0),gloss)*specular;
    frag = vec4(clamp(base*(ambient*ambient_strength+light_colour*diffuse*lit*0.85)
                      + light_colour*shine*lit,0.0,1.0),coverage);
}
