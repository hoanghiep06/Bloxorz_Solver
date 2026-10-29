"""Presentation quality policy, independent of Core and graphics imports."""
import os

CHOICES = ('auto', 'high', 'balanced', 'low')
DETAIL = {'high': 1.0, 'balanced': .45, 'low': 0.0}
CURRENT = 'high'
EFFECTIVE = 'high'
RENDERER = ''


def resolve(choice, renderer=''):
    if choice not in CHOICES:
        raise ValueError('Quality must be auto, high, balanced or low.')
    if choice != 'auto':
        return choice
    software = any(name in renderer.lower() for name in ('llvmpipe','softpipe','software','swiftshader'))
    return 'balanced' if software else 'high'


def configure(gsg):
    global RENDERER
    RENDERER = gsg.getDriverRenderer() if gsg is not None and hasattr(gsg,'getDriverRenderer') else ''
    choice = os.environ.get('BLOXORZ_QUALITY','high')
    return choose(choice if choice in CHOICES else 'high')


def choose(choice):
    global CURRENT, EFFECTIVE
    EFFECTIVE = resolve(choice,RENDERER)
    CURRENT = choice
    return EFFECTIVE
