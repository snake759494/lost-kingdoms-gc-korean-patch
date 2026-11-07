"""Korean glyph atlas builder (IA4, 28px pitch, glyph body inside [2,26))."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PITCH = 32
COLS = 32
ATLAS_W = 1024
FONT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace(chr(92), '/') + '/SeoulHangangEB.ttf'
SS = 4  # supersample


def render_glyph(ch, font_path=FONT, size=28, body=30, outline=1.4, yoff=0):
    """returns (alpha, intensity) float arrays PITCH x PITCH in 0..1"""
    S = PITCH * SS
    f = ImageFont.truetype(font_path, size * SS)
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    # centre the glyph's ink box on the cell centre (use reference box of '한' for vertical)
    l, t, r, bt = d.textbbox((0, 0), ch, font=f)
    rl, rt, rr, rb = d.textbbox((0, 0), '한', font=f)
    x = (S - (r - l)) / 2 - l
    y = (S - (rb - rt)) / 2 - rt + yoff * SS
    d.text((x, y), ch, fill=255, font=f)
    fill = np.asarray(im, np.float32) / 255.0
    # outline by dilation (disc)
    rad = int(round(outline * SS))
    yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    disc = (xx * xx + yy * yy) <= rad * rad + 1
    pad = np.pad(fill, rad)
    dil = np.zeros_like(fill)
    for dy, dx in zip(*np.nonzero(disc)):
        dil = np.maximum(dil, pad[dy:dy + S, dx:dx + S])
    # downsample
    def ds(a): return a.reshape(PITCH, SS, PITCH, SS).mean(axis=(1, 3))
    alpha = ds(dil)
    fillds = ds(fill)
    inten = np.where(alpha > 0, np.clip(fillds / np.maximum(alpha, 1e-6), 0, 1), 0)
    return alpha, inten


def build_atlas(chars, **kw):
    n = len(chars)
    rows = (n + COLS - 1) // COLS
    H = rows * PITCH
    A = np.zeros((H, ATLAS_W), np.float32)
    I = np.zeros((H, ATLAS_W), np.float32)
    for k, ch in enumerate(chars):
        a, i = render_glyph(ch, **kw)
        a = a.copy(); i = i.copy()
        a[:1] = 0; a[31:] = 0; a[:, :1] = 0; a[:, 31:] = 0
        i[a == 0] = 0
        y = (k // COLS) * PITCH; x = (k % COLS) * PITCH
        A[y:y + PITCH, x:x + PITCH] = a
        I[y:y + PITCH, x:x + PITCH] = i
    return A, I, H


def to_ia4(A, I):
    H, W = A.shape
    a4 = np.clip(np.round(A * 15), 0, 15).astype(np.uint8)
    i4 = np.clip(np.round(I * 15), 0, 15).astype(np.uint8)
    i4[a4 == 0] = 0
    px = (a4 << 4) | i4
    out = bytearray()
    for by in range(0, H, 4):
        for bx in range(0, W, 8):
            out += px[by:by + 4, bx:bx + 8].tobytes()
    return bytes(out)


def preview(A, I, path):
    rgba = np.zeros(A.shape + (4,), np.uint8)
    v = (I * 255).astype(np.uint8)
    rgba[..., 0] = v; rgba[..., 1] = v; rgba[..., 2] = v
    rgba[..., 3] = (A * 255).astype(np.uint8)
    bg = Image.new('RGBA', (A.shape[1], A.shape[0]), (60, 90, 140, 255))
    bg.alpha_composite(Image.fromarray(rgba))
    bg.save(path)
