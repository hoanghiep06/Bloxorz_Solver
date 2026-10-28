#version 120
uniform sampler2D p3d_Texture0;
uniform sampler2D normal_roughness_map;
uniform vec4 p3d_ColorScale;
uniform vec4 quality_settings[1];
uniform vec4 snow_variation;
uniform vec4 frost_color;
uniform vec4 snow_color;
uniform vec4 seam_color;
varying vec2 uv;
varying vec3 world_position;
varying vec3 normal_world;
varying vec3 local_position;
varying vec4 tint;

// Derivative tangent frame follows per-tile UV rotations/offsets, including
// vertical faces. Normal data is really sampled, not just bound as an asset.
vec3 stone_normal(vec3 base,vec3 sampled) {
    vec3 dp1=dFdx(world_position),dp2=dFdy(world_position);
    vec2 duv1=dFdx(uv),duv2=dFdy(uv);
    vec3 a=cross(dp2,base),b=cross(base,dp1);
    vec3 t=a*duv1.x+b*duv2.x;
    vec3 bt=a*duv1.y+b*duv2.y;
    float length2=max(dot(t,t),dot(bt,bt));
    if(length2<.00000001)return base;
    float scale=inversesqrt(length2);
    sampled.xy*=quality_settings[0].x*.9;
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
    // Silver moonlight on soft powder; no emission and no global light edits.
    vec3 lighting=vec3(.50,.51,.52)+vec3(.40,.41,.43)*key+vec3(.19,.18,.17)*fill;
    vec3 albedo=stone.rgb*tint.rgb*snow_variation.x;
    float top=smoothstep(.35,.9,geometric.z);
    float edge=.48-max(abs(local_position.x),abs(local_position.y));
    // Texture RGB already layers stone and snow, alpha is coverage. Never
    // multiply coverage by per-instance density: mean coverage must stay ~80%.
    float snow=stone.a*top;
    float bank=4.*stone.a*(1.-stone.a)*top;
    albedo*=1.-bank*.025;
    // The existing side geometry is slate, not a continuation of the white
    // blanket. A thin frozen lip remains just below the snow contact plane.
    float side=1.-smoothstep(.25,.75,abs(geometric.z));
    // Flat top fragments need no wall/lip/strata work. Branches are coherent
    // across each face and retain exactly the same material on bevels/walls.
    if(side>.001) {
        vec3 slate=tint.rgb*(.70+.23*stone.g)*snow_variation.x;
        albedo=mix(albedo,slate,side);
        float frozen_lip=side*smoothstep(-.13,-.025,local_position.z)*stone.a;
        albedo=mix(albedo,mix(frost_color.rgb,snow_color.rgb,.75),frozen_lip*.85);
        float strata=sin(local_position.z*96.+stone.r*4.);
        albedo*=1.+side*strata*.09;
    }
    // Narrow dark cut at the real bevel; snow never bridges a puzzle seam.
    float seam=top*(1.-smoothstep(.014,.033,edge));
    albedo=mix(albedo,seam_color.rgb,seam*.56);
    // A faint compacted ice sheen, restricted to the bank, never glass/neon.
    float spec=pow(max(dot(n,normalize(key_direction+normalize(vec3(.3,-.5,1.)))),0.),
                   mix(18.,6.,detail.a));
    vec3 color=albedo*lighting+frost_color.rgb*spec*(1.-detail.a)*(snow*.035+bank*.07);
    color*=1.+top*(snow_variation.y-.7)*.018;
    gl_FragColor=vec4(color*p3d_ColorScale.rgb,tint.a*p3d_ColorScale.a);
}
