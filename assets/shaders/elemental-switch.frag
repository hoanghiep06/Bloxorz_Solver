#version 120
uniform vec4 elemental_settings; // frozen family, material role, authoritative active, reserved
uniform vec4 elemental_pulse;    // presentation-only activation amplitude/phase
uniform vec4 p3d_ColorScale;
varying vec3 surface;
varying vec3 normal_world;
varying vec4 tint;
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
void main() {
    float ice=elemental_settings.x,role=elemental_settings.y;
    float active=elemental_settings.z,pulse=elemental_pulse.x;
    vec3 n=normalize(normal_world);
    float key=max(0.,dot(n,normalize(vec3(-.45,-.35,1.))));
    float grain=hash(floor(surface.xy*240.));
    float weather=hash(floor(surface.xy*27.));
    vec3 colour=tint.rgb;
    if (role<.5) {
        // Jungle: granular mineral wear and moss, not a blue-tinted ice plate.
        colour*=.80+.18*grain;
        colour=mix(colour,colour*vec3(.78,1.,.72), (1.-ice)*step(.73,weather)*.22);
        // Snow: frost speckle and frozen fissures on a dark slate plinth.
        float fissure=1.-smoothstep(.015,.05,abs(sin(surface.x*51.+surface.y*33.)));
        colour=mix(colour,vec3(.58,.83,.91),ice*(.12*grain+.15*fissure));
    }
    vec3 lit=colour*(.55+.40*key);
    if (role>1.5) {
        float facets=pow(key,10.);
        lit+=ice*vec3(.20,.36,.42)*facets;
        float strength=(role>2.5?.24:.09)+active*.28+pulse*.42;
        vec3 energy=mix(vec3(.12,.83,.61),vec3(.15,.76,1.),ice);
        lit+=energy*strength;
    } else if(role>.5) {
        lit+=mix(vec3(.13,.09,.025),vec3(.07,.15,.20),ice)*pow(key,12.);
    }
    gl_FragColor=vec4(lit*p3d_ColorScale.rgb,tint.a*p3d_ColorScale.a);
}
