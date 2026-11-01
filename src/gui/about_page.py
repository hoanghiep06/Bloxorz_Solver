"""About content for the existing Screen owner; no window, event or game state.

Configure DEMO_YOUTUBE_URL with the final YouTube video URL when available.
"""
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import logging,re,threading,webbrowser
from panda3d.core import DynamicTextFont,Filename,TextNode
from src.gui import ui_theme as ui,icons

DEMO_YOUTUBE_URL = 'https://youtu.be/a9fYH07MTgY'
TITLE = 'BLOXORZ SOLVER'
SUBTITLE = '3D Puzzle Game & AI Search'
DESCRIPTION = ('Bloxorz Solver is a 3D puzzle game where players roll a rectangular block '
    'across challenging platforms and special tiles to reach the goal. The game '
    'also features six AI search algorithms: BFS, DFS, IDS, UCS, Greedy, and A*.')
TEAM = (
    ('24122015','Mai Hoàng Hiệp'),
    ('24122022','Nguyễn Hoài Phước'),
    ('24122035','Phan Nguyễn Gia Huy'),
    ('24122009','Phan Thế Phong'),
    ('24122051','Nguyễn Đức Tài'),
)


def valid_demo_url(url):
    """Accept HTTPS video links on YouTube itself, not lookalike hosts."""
    if not isinstance(url,str) or any(c.isspace() for c in url):return False
    try:
        parts=urlsplit(url)
        if parts.scheme!='https' or parts.username or parts.password or parts.port not in (None,443):return False
        host=parts.hostname
        path=parts.path.strip('/').split('/')
        if host in ('youtu.be','www.youtu.be') and len(path)==1:video=path[0]
        elif host in ('youtube.com','www.youtube.com','m.youtube.com'):
            if parts.path=='/watch':video=parse_qs(parts.query).get('v',[''])[0]
            elif len(path)==2 and path[0] in ('shorts','live','embed'):video=path[1]
            else:return False
        else:return False
        return re.fullmatch(r'[A-Za-z0-9_-]{11}',video) is not None
    except (ValueError,TypeError):return False


def open_demo(url):
    """The browser launch may block on some OSes; never run it on Panda's thread."""
    if not valid_demo_url(url):return None
    def launch():
        try:webbrowser.open(url,new=2)
        except Exception:logging.getLogger(__name__).exception('Could not open gameplay demo.')
    worker=threading.Thread(target=launch,name='AboutDemoBrowser',daemon=True)
    worker.start()
    return worker


@lru_cache(maxsize=2)
def about_font(semibold=False):
    path=Path(__file__).resolve().parents[2]/'assets/fonts/DejaVuSans.ttf'
    font=DynamicTextFont(Filename.fromOsSpecific(str(path)))
    if not font.isValid():raise RuntimeError('Missing About page font: DejaVuSans.ttf')
    font.setPixelsPerUnit(64);font.setScaleFactor(2)
    if semibold:font.setOutline((1,1,1,1),.08,.1)
    return font


def build_about(screen,width,height):
    """Build into the existing Screen so resize/retirement/dispose stay shared."""
    left=int(width*screen.flow.LEFT_SHARE)
    screen.card(-2,-2,left+2,height+4,alpha=1)
    content=min(520,left-48);x=(left-content)/2;cx=left/2
    top=max(16,(height-650)/2)
    labels=[]
    def label(text,size,xx,baseline,*,bold=False,center=False,color=None):
        widget=screen.label(text,size,xx,baseline,color=color or ui.INK,
                            align='center' if center else 'left')
        widget['text_font']=about_font(bold)
        widget['text_shadow']=(0,0,0,0)
        labels.append(widget);return widget
    label(TITLE,26,cx,top+34,bold=True,center=True)
    label(SUBTITLE,15,cx,top+62,center=True)
    body=label(DESCRIPTION,14,x,top+100)
    body['text_wordwrap']=content/14
    rows=body.component('text0').textNode.getNumRows()
    team_y=top+100+rows*17+27
    label('Development Team',17,x,team_y,bold=True,color=ui.GOLD)
    label('Student ID',12,x,team_y+27,color=ui.MUTED)
    label('Full Name',12,x+100,team_y+27,color=ui.MUTED)
    team_labels=[]
    for i,(student,name) in enumerate(TEAM):
        y=team_y+55+i*28
        team_labels.append((label(student,15,x,y),label(name,15,x+100,y)))
    demo_y=team_y+55+4*28+44
    badge=screen.own(ui.rounded_rect(30,21,5,(.9,.1,.14,1)))
    badge.reparentTo(screen.root);badge.setPos(x,0,-demo_y+16)
    play=screen.own(icons.make_icon('play'));play.reparentTo(badge)
    play.setPos(14,-.01,-10.5);play.setScale(7);play.setColor(1,1,1,1)
    label('Gameplay Demo',17,x+42,demo_y,bold=True)
    available=valid_demo_url(DEMO_YOUTUBE_URL)
    status=label('Open in your browser' if available else 'Coming soon',13,x,demo_y+27,color=ui.MUTED)
    watch=screen.button('Watch Demo',x,demo_y+43,content,40,
                        lambda:open_demo(DEMO_YOUTUBE_URL),enabled=available,size=18)
    back=screen.button('Back',cx-100,demo_y+105,200,46,
                       lambda:screen.flow.show('main'),primary=True,size=20)
    return dict(labels=labels,team=team_labels,watch=watch,back=back,status=status,
                left=left,content_width=content,bottom=demo_y+151)
