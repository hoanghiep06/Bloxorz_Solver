#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_TextureMatrix[1];
uniform vec4 quality_settings[1];
uniform vec4 motion_parameters;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Color;
attribute vec2 p3d_MultiTexCoord0;
varying vec2 uv;
varying vec3 normal_world;
varying vec4 tint;
void main() {
    vec4 position=p3d_Vertex;
    if (motion_parameters.w>.5) {
        float u=clamp((position.x-motion_parameters.x)/motion_parameters.y,0.,1.);
        position.y+=motion_parameters.z*sin(quality_settings[0].y*2.+u*6.)*u*u;
    }
    gl_Position = p3d_ModelViewProjectionMatrix * position;
    normal_world = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
    uv = (p3d_TextureMatrix[0] * vec4(p3d_MultiTexCoord0, 0.0, 1.0)).xy;
    tint = p3d_Color;
}
