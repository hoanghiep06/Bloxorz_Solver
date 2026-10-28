#version 130
uniform sampler2D scene_color;
uniform vec2 pixel_size;

uniform vec2 scene_size;
varying vec2 uv;
vec3 hot(vec2 p) {
    vec3 c=texture2D(scene_color,p*scene_size/vec2(textureSize(scene_color,0))).rgb;
    float orange=smoothstep(.12,.42,c.r-c.g)*smoothstep(.6,.95,c.r);
    return c*orange;
}
void main(){
    vec3 glow=hot(uv)*.20;
    glow+=(hot(uv+pixel_size*vec2(3,0))+hot(uv-pixel_size*vec2(3,0)))*.12;
    glow+=(hot(uv+pixel_size*vec2(0,3))+hot(uv-pixel_size*vec2(0,3)))*.12;
    glow+=(hot(uv+pixel_size*vec2(2,2))+hot(uv-pixel_size*vec2(2,2)))*.08;
    glow+=(hot(uv+pixel_size*vec2(-2,2))+hot(uv-pixel_size*vec2(-2,2)))*.08;
    gl_FragColor=vec4(glow,1.);
}
