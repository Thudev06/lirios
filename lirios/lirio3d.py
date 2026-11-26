"""
Lirio del valle 3D en ASCII (pygame + numpy).

La planta (hojas, tallo arqueado y campanitas colgantes) es una nube de
puntos 3D. Cada frame se rota, se proyecta en perspectiva, se resuelve la
profundidad por celda (z-buffer) y se ilumina con Lambert. El brillo de cada
celda se traduce en un carácter ASCII.

Ciclo: punto -> crece -> florece -> gira -> el viento se lleva los pétalos -> punto.

Controles: ESPACIO pausa, R reinicia, ESC sale.
Uso:  python lirio3d.py            (ventana)
      python lirio3d.py --record out_dir [segundos]   (guarda PNGs, sin ventana)
"""
import math
import os
import sys

import numpy as np
import pygame

W, H = 1280, 900
FPS = 30
CYCLE = 18.0                       # segundos por ciclo completo
RAMP = " .,:;-=+*cox%#&@"          # de oscuro a brillante
LEVELS = len(RAMP)

# Materiales: color base (RGB)
MAT_BELL = 0
MAT_STEM = 1
MAT_LEAF = 2
MAT_BUD = 3
MAT_INNER = 4
MAT_COLORS = np.array([
    (245, 245, 235),   # campana blanca
    (110, 170, 70),    # tallo
    (45, 125, 55),     # hoja
    (215, 235, 195),   # botón verdoso
    (120, 125, 110),   # interior de la campana (sombra)
], dtype=np.float32)

AMBIENT = np.array([0.45, 0.25, 0.22, 0.35, 0.15], dtype=np.float32)

rng = np.random.default_rng(7)


# ----------------------------------------------------------------- geometría
def frame_from(d):
    """Dos vectores perpendiculares a d (unitario)."""
    a = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(d, a)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    return u, v


def bezier(p0, p1, p2, t):
    t = t[:, None]
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


def bezier_d(p0, p1, p2, t):
    t = t[:, None]
    return 2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1)


STEM = (np.array([0.0, -1.9, 0.0]), np.array([0.0, 1.9, 0.0]), np.array([1.8, 1.2, 0.15]))


def build_plant():
    P, N, M, G, D, A = [], [], [], [], [], []   # posición, normal, material, t de aparición, grupo, anclaje

    # --- tallo (tubo a lo largo de una Bézier)
    ts = np.linspace(0, 1, 260)
    c = bezier(*STEM, ts)
    dc = bezier_d(*STEM, ts)
    ang = np.linspace(0, 2 * np.pi, 10, endpoint=False)
    for i, t in enumerate(ts):
        d = dc[i] / np.linalg.norm(dc[i])
        u, v = frame_from(d)
        r = 0.035 * (1 - 0.5 * t)
        for a in ang:
            n = math.cos(a) * u + math.sin(a) * v
            P.append(c[i] + r * n); N.append(n); M.append(MAT_STEM)
            G.append(0.08 + 0.35 * t); D.append(1); A.append(P[-1])

    # --- flores: campanas colgantes en un lado del racimo
    n_fl = 7
    for k in range(n_fl):
        t = 0.34 + 0.64 * k / (n_fl - 1)
        base = bezier(*STEM, np.array([t]))[0]
        size = 0.24 * (1 - 0.5 * k / (n_fl - 1))
        side = np.array([0.04, 0.0, 0.30 * (1 if k % 2 else -1) * (1 - 0.4 * k / n_fl)])
        # pedicelo: arco corto hacia afuera y abajo
        tip = base + side + np.array([0.03, -0.12 - 0.6 * size, 0.0])
        mid = base + side * 0.9 + np.array([0.0, 0.05, 0.0])
        pts = np.linspace(0, 1, 26)
        pc = bezier(base, mid, tip, pts)
        for p in pc:
            for a in ang[::2]:
                n = np.array([math.cos(a), 0.0, math.sin(a)])
                P.append(p + 0.012 * n); N.append(n); M.append(MAT_STEM)
                G.append(0.35 + 0.05 * k); D.append(1); A.append(base)
        appear = 0.40 + 0.055 * k
        if k >= n_fl - 2:     # los últimos son botones cerrados
            m = 420
            v = rng.normal(size=(m, 3)); v /= np.linalg.norm(v, axis=1)[:, None]
            for n in v:
                P.append(tip + np.array([0, -size * 0.6, 0]) + n * size * np.array([0.55, 0.7, 0.55]))
                N.append(n); M.append(MAT_BUD); G.append(appear); D.append(2); A.append(tip)
            continue
        # campana: perfil r(h) con 6 lóbulos curvados hacia afuera en el borde.
        # Dos capas: exterior blanca e interior en sombra, para que se lea la boca.
        Hb = size * 1.1
        hs = np.linspace(0, 1, 40)
        th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        for layer, mat_l, shrink in ((0, MAT_BELL, 1.0), (1, MAT_INNER, 0.9)):
            for h in hs:
                if layer == 1 and h < 0.25:
                    continue
                r = size * (0.30 + 0.70 * math.sin(min(h / 0.8, 1.0) * math.pi / 2) ** 0.6) * shrink
                for a in th:
                    lobe = max(0.0, math.cos(3 * a)) ** 2          # 6 puntas
                    flare = max(0.0, h - 0.72) / 0.28
                    rr = r * (1 + 0.55 * flare ** 1.6 * (0.25 + 0.75 * lobe))
                    # festón: entre lóbulos el borde se recoge
                    hh = h * (1 - 0.10 * (1 - lobe) * flare)
                    y = -Hb * hh + 0.45 * size * flare ** 2 * lobe      # puntas curvadas hacia arriba
                    n = np.array([math.cos(a), 0.45 - 1.1 * flare * lobe, math.sin(a)])
                    n /= np.linalg.norm(n)
                    P.append(tip + np.array([rr * math.cos(a), y, rr * math.sin(a)]))
                    N.append(n); M.append(mat_l); G.append(appear); D.append(2); A.append(tip)
        # pistilo amarillento asomando
        for s in np.linspace(0, 1, 12):
            P.append(tip + np.array([0, -Hb * (0.5 + 0.55 * s), 0])); N.append(np.array([0, -1.0, 0]))
            M.append(MAT_BUD); G.append(appear); D.append(2); A.append(tip)

    # --- hojas: dos hojas lanceoladas que abrazan la base
    for j, (rot, lean, length) in enumerate([(-0.4, 0.75, 2.4), (2.6, 0.6, 2.1)]):
        us = np.linspace(0, 1, 120)
        vs = np.linspace(-1, 1, 54)
        ca, sa = math.cos(rot), math.sin(rot)
        out = np.array([ca, 0, sa])          # hacia donde se inclina
        across = np.array([-sa, 0, ca])
        for u in us:
            w = 0.36 * math.sin(math.pi * u) ** 0.75 * (1 - 0.25 * u)
            # nervio central: sube y se curva hacia afuera
            y = -1.95 + length * u
            o = lean * u ** 1.8 + 0.08
            for v in vs:
                cup = 0.18 * w * v * v               # hoja cóncava
                p = out * (o + cup) + across * (w * v) + np.array([0, y - 0.15 * u * u * length * 0.2, 0])
                vein = 0.55 * math.sin(v * 9 * math.pi)          # nervaduras paralelas
                n = out * 1.0 - across * (2 * 0.18 * w * v + vein) + np.array([0, -lean * 0.6, 0])
                n /= np.linalg.norm(n)
                P.append(p); N.append(n); M.append(MAT_LEAF)
                G.append(0.02 + 0.03 * j); D.append(0); A.append(np.array([0, -1.95, 0]))

    P = np.array(P, dtype=np.float32)
    off = -(P.min(0) + P.max(0)) / 2                 # centrar en el eje de giro
    P = P + off
    A = np.array(A, dtype=np.float32) + off
    return (P, np.array(N, dtype=np.float32), np.array(M), np.array(G, dtype=np.float32),
            np.array(D), A)


# ------------------------------------------------------------------ helpers
def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float32)


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("dejavusansmono,consolas,menlo,monospace", 8, bold=True)
        cw, ch = self.font.size("@")
        self.cw, self.ch = cw, ch - 1
        self.cols, self.rows = W // self.cw, H // self.ch
        # glifos pre-renderizados: [material][nivel]
        self.glyphs = []
        for base in MAT_COLORS:
            row = []
            for lv in range(LEVELS):
                f = 0.45 + 0.55 * lv / (LEVELS - 1)
                col = tuple(int(min(255, c * f)) for c in base)
                row.append(self.font.render(RAMP[lv], True, col))
            self.glyphs.append(row)
        self.glow = pygame.Surface((W // 4, H // 4))

    def draw(self, pts, nrm, mat, alpha):
        scr = self.screen
        scr.fill((4, 4, 8))
        if len(pts) == 0:
            return
        cam = 6.0
        z = pts[:, 2] + cam
        ok = z > 0.5
        pts, nrm, mat, alpha, z = pts[ok], nrm[ok], mat[ok], alpha[ok], z[ok]
        f = 1220.0
        sx = W / 2 + f * pts[:, 0] / z
        sy = H / 2 - f * pts[:, 1] / z
        cx = (sx / self.cw).astype(np.int32)
        cy = (sy / self.ch).astype(np.int32)
        ok = (cx >= 0) & (cx < self.cols) & (cy >= 0) & (cy < self.rows)
        cx, cy, z, nrm, mat, alpha = cx[ok], cy[ok], z[ok], nrm[ok], mat[ok], alpha[ok]
        # iluminación (doble cara) + atenuación por profundidad
        light = np.array([-0.5, 0.7, -0.6], dtype=np.float32)
        light /= np.linalg.norm(light)
        lam = np.abs(nrm @ light)
        amb = AMBIENT[mat]
        b = (amb + (1 - amb) * lam ** 0.8) * alpha * np.clip(1.0 - (z - cam) * 0.10, 0.65, 1.1)
        lv = np.clip((b * (LEVELS - 1)).astype(np.int32), 0, LEVELS - 1)
        # z-buffer: ordenar de lejos a cerca, la última escritura gana
        order = np.argsort(-z, kind="stable")
        idx = cy[order] * self.cols + cx[order]
        cell_lv = np.full(self.cols * self.rows, -1, np.int32)
        cell_mat = np.zeros(self.cols * self.rows, np.int32)
        cell_lv[idx] = lv[order]
        cell_mat[idx] = mat[order]
        filled = np.nonzero(cell_lv > 0)[0]
        g = self.glyphs
        cols, cw, ch = self.cols, self.cw, self.ch
        scr.blits([(g[cell_mat[i]][cell_lv[i]], ((i % cols) * cw, (i // cols) * ch)) for i in filled], False)
        # brillo suave (bloom barato)
        pygame.transform.smoothscale(scr, (W // 4, H // 4), self.glow)
        self.glow.fill((90, 90, 90), special_flags=pygame.BLEND_MULT)
        scr.blit(pygame.transform.smoothscale(self.glow, (W, H)), (0, 0), special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------- animación
class Lily:
    def __init__(self):
        self.P, self.N, self.M, self.G, self.D, self.A = build_plant()
        n = len(self.P)
        # viento: hacia +x con turbulencia; los pétalos vuelan más
        self.vel = rng.normal(0, 0.25, (n, 3)).astype(np.float32)
        self.vel[:, 0] += 0.9 + 0.5 * rng.random(n)
        self.vel[:, 1] += 0.35
        self.delay = rng.uniform(0, 1.2, n).astype(np.float32)
        # el viento empieza por la punta del racimo
        self.delay += np.where(self.D == 2, 0.0, 0.8 + 0.6 * rng.random(n)).astype(np.float32)
        self.seed = rng.uniform(0, 6.28, (n, 3)).astype(np.float32)
        self.keep = rng.random(n) < 0.3

    def state(self, t):
        """Devuelve puntos, normales, material y alpha en el instante t (0..CYCLE)."""
        P, N = self.P.copy(), self.N.copy()
        alpha = np.ones(len(P), np.float32)
        # fase 0-1s: solo un punto; 1-8s: crecer
        grow = (t - 1.0) / 7.0
        g = smooth((grow - self.G) / 0.12)                    # 0..1 por punto
        # cada órgano escala desde su anclaje (tallo: aparece; hojas: desde la base; flores: desde el pedicelo)
        P = self.A + (P - self.A) * g[:, None] ** 0.7
        alpha *= (g > 0.01)
        # viento / dispersión: 12.5s..16.5s. Se devuelve aparte porque el viento
        # sopla en coordenadas de pantalla (no gira con la planta).
        petal = (self.D == 2)
        wt = t - 12.5 - self.delay
        w = (np.maximum(wt, 0) * petal)[:, None]
        wind = (self.vel * w + 0.55 * w * w * np.array([1.0, 0.25, 0.0], np.float32)
                + 0.12 * np.sin(self.seed + w * 4.0) * np.minimum(w, 1.0))
        # solo una parte de los puntos de cada pétalo viaja como partícula
        alpha *= np.where(petal & (wt > 0) & ~self.keep, 0.0, 1.0)
        alpha *= np.where(petal, np.clip(1.0 - np.maximum(wt, 0) / 2.6, 0, 1), 1.0)
        # hojas y tallo se marchitan: se recogen hacia su anclaje y se apagan
        wither = smooth((t - 13.6) / 2.6)
        if wither > 0:
            k = (~petal)[:, None] * wither
            P = P + (self.A - P) * k * 0.85
            P[:, 1] -= (~petal) * wither * 0.4
            alpha *= np.where(petal, 1.0, 1.0 - wither)
        # balanceo suave
        sway = 0.06 * math.sin(t * 1.3)
        P[:, 0] += sway * np.clip(P[:, 1] + 1.6, 0, None) ** 2 * 0.25
        return P, N, self.M, alpha, wind


def main():
    record = None
    duration = CYCLE
    if "--record" in sys.argv:
        i = sys.argv.index("--record")
        record = sys.argv[i + 1]
        if len(sys.argv) > i + 2:
            duration = float(sys.argv[i + 2])
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.makedirs(record, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("lirio3d.py")
    clock = pygame.time.Clock()
    rend = Renderer(screen)
    lily = Lily()
    t, paused, frame = 0.0, False, 0
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit(); return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                paused = not paused
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r:
                t = 0.0
        ct = t % CYCLE
        if ct < 1.0 or ct > 16.8:                              # el "punto" inicial/final
            pts = np.array([[0, 0, 0]], np.float32)
            rend.draw(pts, np.array([[0, 0, -1]], np.float32), np.array([MAT_BELL]), np.array([1.0], np.float32))
        else:
            P, N, M, A, wind = lily.state(ct)
            R = rot_x(0.18) @ rot_y(0.35 * t - 0.6)
            rend.draw(P @ R.T + wind, N @ R.T, M, A)
        pygame.display.flip()
        if record:
            pygame.image.save(screen, os.path.join(record, f"f{frame:05d}.png"))
            frame += 1
            t += 1.0 / FPS
            if t >= duration:
                pygame.quit(); return
        else:
            dt = clock.tick(FPS) / 1000.0
            if not paused:
                t += dt


if __name__ == "__main__":
    main()
