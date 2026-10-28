"""Snow Temple material constants, shared by authoring and runtime; no engine."""

SNOW_HEX = dict(top='EFF5F8',variation='849AAA',frost='A8CCDF',bevel='FFFFFF',
    side='334D63',underside='203448',seam='455E73',wear='CADCE9')
SNOW_PALETTE = {key:(*tuple(int(color[i:i+2],16)/255 for i in (0,2,4)),1.)
                for key,color in SNOW_HEX.items()}
SNOW_COVERAGE_TARGET = .80
