#version 120
uniform sampler2D p3d_Texture0;
uniform sampler2D normal_roughness_map;
uniform vec4 p3d_ColorScale;
uniform vec4 quality_settings[1];
uniform vec4 snow_variation;
uniform vec4 frost_color;
uniform vec4 seam_color;
varying vec2 uv;
varying vec3 world_position;
varying vec3 normal_world;
varying vec3 local_position;
varying vec4 tint;
vec3 stone_normal(vec3 base,vec3 sampled) {
    vec3 dp1=dFdx(world_position),dp2=dFdy(world_position);
    vec2 duv1=dFdx(uv),duv2=dFdy(uv);
    vec3 a=cross(dp2,base),b=cross(base,dp1);
    vec3 t=a*duv1.x+b*duv2.x;
    vec3 bt=a*duv1.y+b*duv2.y;
    float length2=max(dot(t,t),dot(bt,bt));
    if(length2<.00000001)return base;
    float scale=inversesqrt(length2);
    sampled.xy*=quality_settings[0].x*.7;
    return normalize(t*scale*sampled.x+bt*scale*sampled.y+base*sampled.z);
}
void main() {
    vec4 stone=texture2D(p3d_Texture0,uv);
    vec4 detail=texture2D(normal_roughness_map,uv);
    vec3 geometric=normalize(normal_world);
    vec3 n=stone_normal(geometric,detail.rgb*2.-1.);
    vec3 key_direction=normalize(vec3(-.55,-.4,1.));
    float key=max(dot(n,key_direction),0.);
    float fill=max(dot(n,normalize(vec3(.6,.2,.8))),0.);
    vec3 lighting=vec3(.49,.49,.47)+vec3(.37,.41,.47)*key+vec3(.22,.21,.18)*fill;
    vec3 albedo=stone.rgb*tint.rgb*snow_variation.x;
    float top=smoothstep(.35,.9,geometric.z);
    float edge=.48-max(abs(local_position.x),abs(local_position.y));
    float border=1.-smoothstep(.018,.085,edge);
    float frost=top*border*smoothstep(.30,.76,stone.a)*snow_variation.y;
    albedo=mix(albedo,frost_color.rgb,frost*.78);
    float seam=top*(1.-smoothstep(.014,.030,edge))*(1.-frost*.6);
    albedo=mix(albedo,seam_color.rgb,seam*.38);
    float side=1.-smoothstep(.25,.75,abs(geometric.z));
    float strata=sin(local_position.z*96.+stone.r*4.);
    albedo*=1.+side*strata*.07;
    float spec=pow(max(dot(n,normalize(key_direction+normalize(vec3(.3,-.5,1.)))),0.),
                   mix(18.,6.,detail.a));
    vec3 color=albedo*lighting+vec3(.035,.04,.045)*spec*(1.-detail.a)*top;
    gl_FragColor=vec4(color*p3d_ColorScale.rgb,tint.a*p3d_ColorScale.a);
}
