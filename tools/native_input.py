"""Small Linux/X11 QA driver. Sends real XTest key/button events to Panda3D.

Only used by optional native smoke tools, never imported by the game.
"""
import ctypes
import time


class NativeInput:
    def __init__(self, app):
        self.app = app
        self.on_step = None
        self.x = ctypes.CDLL('libX11.so.6')
        self.xt = ctypes.CDLL('libXtst.so.6')
        self.x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x.XOpenDisplay.restype = ctypes.c_void_p
        self.display = self.x.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError('Native QA needs an X11 display (xvfb-run is supported).')
        self.x.XFlush.argtypes = [ctypes.c_void_p]
        self.x.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.x.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x.XStringToKeysym.restype = ctypes.c_ulong
        self.x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x.XKeysymToKeycode.restype = ctypes.c_uint
        self.xt.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
        self.xt.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]

    def step(self, n=1):
        for _ in range(n):
            self.app.taskMgr.step()
            if self.on_step is not None:self.on_step()
            time.sleep(.004)

    def wait(self, predicate, timeout=12):
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.step()
            if predicate():
                return
        raise AssertionError('Timed out waiting for native UI state.')

    def pointer(self, x, y):
        target = (2*x/self.app.win.getXSize()-1,1-2*y/self.app.win.getYSize())
        for _ in range(100):
            self.app.win.movePointer(0,round(x),round(y));self.step(2)
            watcher=self.app.mouseWatcherNode
            if watcher.hasMouse() and max(abs(watcher.getMouse()[i]-target[i]) for i in (0,1))<.006:
                return
        raise AssertionError(f'Native pointer motion not delivered at {(x,y)}.')

    def click(self):
        for pressed in (True,False):
            self.xt.XTestFakeButtonEvent(self.display,1,pressed,0)
            self.x.XFlush(self.display);self.step(4)

    def click_widget(self, widget):
        from panda3d.core import Point3
        left,right,bottom,top=widget['frameSize']
        p=self.app.pixel2d.getRelativePoint(widget,Point3((left+right)/2,0,(bottom+top)/2))
        self.pointer(p.x,-p.z);self.click()

    def key(self, name):
        key=self.x.XKeysymToKeycode(self.display,self.x.XStringToKeysym(name.encode()))
        if not key:
            raise ValueError(f'Unknown X11 key: {name}')
        for pressed in (True,False):
            self.xt.XTestFakeKeyEvent(self.display,key,pressed,0)
            self.x.XFlush(self.display);self.step(3)

    def close(self):
        if self.display:
            self.x.XCloseDisplay(self.display)
            self.display=None
