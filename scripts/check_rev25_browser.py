"""Browser QA for rev 25 — Féminin gallery hidden-until-backend.

Scenario A (bundled/static deployment, no API_BASE):
  -> #on-the-pitch stays hidden, no console errors, page flows correctly.

Scenario B (backend wired + photos published):
  -> mock API at /api/gallery/feminin/ with 5 photos
  -> section appears, 5 tiles built, lightbox opens, tiles have .in when
     scrolled into view; 0 console errors.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'site'
PORT_SITE = 8097
PORT_API = 8098
SHOTS = Path('/tmp/rev25-shots')
SHOTS.mkdir(exist_ok=True)


class SiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        p = ROOT / path.lstrip('/')
        if p.is_dir():
            p = p / 'index.html'
        if not p.is_file():
            self.send_error(404)
            return
        ctype = 'text/html' if p.suffix == '.html' else (
            'text/css' if p.suffix == '.css' else
            'application/javascript' if p.suffix == '.js' else
            'image/jpeg' if p.suffix in ('.jpg', '.jpeg') else
            'image/png' if p.suffix == '.png' else 'application/octet-stream')
        body = p.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class ApiHandler(BaseHTTPRequestHandler):
    photos = None  # set later

    def do_GET(self):
        body = json.dumps({
            'ok': True, 'count': len(self.photos), 'photos': self.photos,
        }).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def serve_forever(srv):
    threading.Thread(target=srv.serve_forever, daemon=True).start()


site_srv = HTTPServer(('127.0.0.1', PORT_SITE), SiteHandler)
api_srv = HTTPServer(('127.0.0.1', PORT_API), ApiHandler)
serve_forever(site_srv)
serve_forever(api_srv)

# mock photos reuse on-disk real training photos (public hero set)
HEROES = sorted((ROOT / 'assets/img/hero').glob('*.jpg'))[:5]
ApiHandler.photos = [
    {'image': f'http://127.0.0.1:{PORT_API}/{h.name}',  # not used directly
     'alt': 'alt text here', 'caption': c}
    for h, c in zip(HEROES, ['On the ball', 'Pass & move', 'The briefing',
                             'Practice days', 'The pathway'])
]
# point images at the real static files so they actually load
ApiHandler.photos = [
    {'image': f'http://127.0.0.1:{PORT_SITE}/assets/img/hero/{h.name}',
     'alt': f'Féminin training photo {i + 1}', 'caption': c}
    for i, (h, c) in enumerate(zip(HEROES, ['On the ball', 'Pass & move',
                                            'The briefing', 'Practice days',
                                            'The pathway']))
]

with sync_playwright() as pw:
    browser = pw.chromium.launch()

    def track(pg):
        bad = []
        pg.on('response', lambda r: bad.append(f'{r.status} {r.url}')
              if r.status >= 400 else None)
        return bad

    # ---------- Scenario A: no API_BASE ----------
    pg = browser.new_page(viewport={'width': 1440, 'height': 960})
    errors = []
    bad = track(pg)
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(f'http://127.0.0.1:{PORT_SITE}/feminin.html')
    pg.wait_for_timeout(1200)
    print('A0. HTTP >=400 responses:', *bad, sep='\n  ')
    hidden = pg.evaluate("document.getElementById('on-the-pitch').hidden")
    display = pg.evaluate(
        "getComputedStyle(document.getElementById('on-the-pitch')).display")
    assert hidden is True, 'section not hidden'
    assert display == 'none', f'display={display}'
    print('A1. section hidden (attr + computed display:none): OK')
    # gallery imgs never fetched
    imgs = pg.evaluate(
        "document.querySelectorAll('#on-the-pitch img').length")
    assert imgs == 0, imgs
    print('A2. zero tiles in DOM: OK')
    # page still scrolls to CTA fine
    pg.locator('#feminin-cta').scroll_into_view_if_needed()
    pg.wait_for_timeout(600)
    print('A3. CTA reachable, page flow OK')
    assert not [e for e in errors if 'favicon' in e], errors
    real_errors = [e for e in errors if 'favicon' not in e]
    assert not real_errors, real_errors
    print('A4. console errors: NONE')
    pg.screenshot(path=str(SHOTS / 'a-hidden-page.png'), full_page=False)
    pg.close()

    # ---------- Scenario B: backend wired + published photos ----------
    pg = browser.new_page(viewport={'width': 1440, 'height': 960})
    errors = []
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.goto(f'http://127.0.0.1:{PORT_SITE}/feminin.html')
    pg.evaluate(f"window.SP_CONFIG.API_BASE='http://127.0.0.1:{PORT_API}'")
    # re-run the module (it exited early on first load without API_BASE)
    pg.evaluate("""
      fetch(SP_CONFIG.API_BASE + '/api/gallery/feminin/').then(()=>{});
      const s = document.createElement('script');
      s.src = 'assets/js/shared/sp-feminin-gallery.js?v1';
      document.body.appendChild(s);
    """)
    pg.wait_for_timeout(2500)
    hidden = pg.evaluate("document.getElementById('on-the-pitch').hidden")
    tiles = pg.evaluate("document.querySelectorAll('#on-the-pitch .fg-tile').length")
    assert hidden is False, 'section still hidden'
    assert tiles == 5, f'tiles={tiles}'
    print('B1. section revealed with 5 tiles: OK')
    # scroll to gallery so the reveal observer fires + lazy images load
    pg.locator('#on-the-pitch').scroll_into_view_if_needed()
    pg.wait_for_timeout(2000)
    loaded = pg.evaluate(
        "Array.from(document.querySelectorAll('#on-the-pitch img'))"
        ".filter(i=>i.naturalWidth>0).length")
    assert loaded == 5, f'loaded={loaded}'
    print('B2. all 5 images load: OK')
    in_count = pg.evaluate(
        "document.querySelectorAll('#on-the-pitch [data-reveal].in').length")
    assert in_count >= 5, f'in={in_count}'
    print(f'B3. reveal animation applied ({in_count} elements .in): OK')
    pg.screenshot(path=str(SHOTS / 'b-revealed.png'))
    # lightbox opens on click
    pg.locator('#on-the-pitch .fg-tile').first.click()
    pg.wait_for_timeout(800)
    lb = pg.evaluate("""
      (() => { const r = document.querySelector('div[role="dialog"][aria-label="Photo viewer"]');
        return r ? getComputedStyle(r).display : 'missing'; })()
    """)
    assert lb == 'block', f'lightbox did not open (display={lb})'
    pg.screenshot(path=str(SHOTS / 'c-lightbox.png'))
    pg.keyboard.press('Escape')
    pg.wait_for_timeout(400)
    print('B4. lightbox opens from dynamic tile: OK')
    real_errors = [e for e in errors if 'favicon' not in e]
    assert not real_errors, real_errors
    print('B5. console errors: NONE')
    pg.close()

    # ---------- Scenario C: backend answers zero photos ----------
    ApiHandler.photos = []
    pg = browser.new_page(viewport={'width': 1440, 'height': 960})
    pg.goto(f'http://127.0.0.1:{PORT_SITE}/feminin.html')
    pg.evaluate(f"window.SP_CONFIG.API_BASE='http://127.0.0.1:{PORT_API}'")
    pg.evaluate("""
      const s = document.createElement('script');
      s.src = 'assets/js/shared/sp-feminin-gallery.js?v1';
      document.body.appendChild(s);
    """)
    pg.wait_for_timeout(1500)
    hidden = pg.evaluate("document.getElementById('on-the-pitch').hidden")
    assert hidden is True, 'section should stay hidden with 0 photos'
    print('C1. zero published photos -> stays hidden: OK')
    pg.close()

    browser.close()

print('ALL BROWSER CHECKS PASSED')
