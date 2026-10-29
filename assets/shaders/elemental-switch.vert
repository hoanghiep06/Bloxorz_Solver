#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Color;
varying vec3 surface;
varying vec3 normal_world;
varying vec4 tint;
void main() {
    gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;
    surface=p3d_Vertex.xyz;
    normal_world=normalize(mat3(p3d_ModelMatrix)*p3d_Normal);
    tint=p3d_Color;
}
