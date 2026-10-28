#version 120
uniform sampler2D p3d_Texture0;
uniform sampler2D detail_map;
uniform vec4 p3d_ColorScale;
uniform float emission_strength;
uniform float emission_color_mode;
uniform float detail_strength;
uniform float night_material;
uniform float ice_mode;
uniform vec4 quality_settings[1];
varying vec2 uv;
varying vec3 normal_world;
varying vec4 tint;

// ---- Chỉnh độ sáng băng tại đây (chỉ ảnh hưởng vật liệu ice) ----
const float ICE_BODY_BRIGHTNESS = 0.8;  // độ sáng thân băng   (1.0 = như cũ)
const float ICE_SPECULAR        = 0.2;  // độ bóng              (cũ: 0.45)
const float ICE_EMISSION_SCALE  = 0.4;  // độ phát sáng vết nứt (1.0 = như cũ)

void main() {
    vec4 tex = texture2D(p3d_Texture0, uv);
    vec3 n = normalize(normal_world);
    if (quality_settings[0].x > .01 && detail_strength > 0.) {
        vec2 d = vec2(1.0/512.0,0.0);
        float gx=texture2D(detail_map,uv+d.xy).r-texture2D(detail_map,uv-d.xy).r;
        float gy=texture2D(detail_map,uv+d.yx).r-texture2D(detail_map,uv-d.yx).r;
        vec3 tangent=normalize(cross(abs(n.z)>.9?vec3(0,1,0):vec3(0,0,1),n));
        vec3 bitangent=cross(n,tangent);
        n=normalize(n-detail_strength*quality_settings[0].x*(gx*tangent+gy*bitangent));
    }
    float key = max(dot(n,normalize(vec3(-.55,-.4,1.0))),0.0);
    float fill = max(dot(n,normalize(vec3(.7,.3,.5))),0.0);
    vec3 ambient = mix(vec3(.49,.52,.43),vec3(.26,.36,.56),night_material);
    vec3 sun = mix(vec3(.67,.61,.45),vec3(.43,.56,.82),night_material);
    vec3 lit = tex.rgb * tint.rgb * (ambient+sun*key+vec3(.10,.13,.16)*fill);
    // Băng: giảm độ sáng thân, rồi cộng ánh bóng nhẹ.
    lit *= mix(1.0, ICE_BODY_BRIGHTNESS, ice_mode);
    lit += ice_mode * vec3(.55,.75,1.0) * pow(key, 24.0) * ICE_SPECULAR;
    vec3 emission=vec3(0.0);
    if (emission_strength > 0.0) {
        float halo=0.0;
        if (quality_settings[0].x>.8) {
            halo=texture2D(p3d_Texture0,uv+vec2(.008,0)).a;
            halo+=texture2D(p3d_Texture0,uv-vec2(.008,0)).a;
        }
        vec3 hot=mix(mix(vec3(1,.12,.005),vec3(1,.8,.2),tex.a*tex.a),tint.rgb,emission_color_mode);
        // Băng: phát sáng xanh lạnh thay vì cam.
        hot=mix(hot,mix(vec3(.30,.65,1.0),vec3(.85,.97,1.0),tex.a*tex.a),ice_mode);
        vec3 halo_col=mix(vec3(.13,.025,.001),vec3(.02,.07,.14),ice_mode);
        emission=emission_strength*(hot*tex.a+halo_col*halo);
        emission*=mix(1.0, ICE_EMISSION_SCALE, ice_mode);
    }
    gl_FragColor = vec4((lit+emission)*p3d_ColorScale.rgb,tint.a*p3d_ColorScale.a);
}