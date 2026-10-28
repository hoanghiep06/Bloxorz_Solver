#version 130
uniform sampler2D scene_color;
uniform sampler2D glow_color;


uniform vec2 scene_size;
varying vec2 uv;
void main(){
    vec4 c=texture2D(scene_color,uv*scene_size/vec2(textureSize(scene_color,0)));
    gl_FragColor=vec4(c.rgb+texture2D(glow_color,uv*floor(scene_size/2.0)/vec2(textureSize(glow_color,0))).rgb*.22,c.a);
}
