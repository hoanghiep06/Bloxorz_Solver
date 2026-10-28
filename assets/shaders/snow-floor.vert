#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_TextureMatrix[1];
uniform float floor_pitch;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Color;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 uv;
varying vec3 world_position;
varying vec3 normal_world;
varying vec3 local_position;
varying vec4 tint;
void main() {
    gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;
    world_position=(p3d_ModelMatrix*p3d_Vertex).xyz;
    normal_world=normalize(mat3(p3d_ModelMatrix)*p3d_Normal);
    local_position=p3d_Vertex.xyz/floor_pitch;
    uv=(p3d_TextureMatrix[0]*vec4(p3d_MultiTexCoord0,0.,1.)).xy;
    tint=p3d_Color;
}
