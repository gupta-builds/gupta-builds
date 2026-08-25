#!/usr/bin/env python3
"""Render the ASCII-portrait SVG with a one-shot typewriter reveal.

The ASCII art itself is baked in below (converted once from a source photo
via a standard 70-level luminance ramp, background thresholded to blank).
Re-derive it from a new photo by regenerating ASCII_ART with the same ramp
and re-pasting here - no image processing happens at build time.
"""
import os

ASCII_ART = r'''
                                                     `  `` ````^:Iil^
                                                 `,,`                ``
                                              `^^`                        `
                                           ^``^^^                           ``
                                      `""""^  ^ ^
                                    ^,^  ^"^^"^""^
                                  ^",^  ^                                       `
                                  `^`^:":  ^                                    ^
                                  `  `^":::,"^"                   "^            ,
                                   ^ `'^`,,,,,,"    ^      :;:;:,:,"^           ^
                                   `^^   ^,,"","^"  "l"    l!I:I;;:II;::,^^""^`^
                                    `;` `":,,l;""^",:II`^"^~[?~>>iii!l:,"   ^^^^
                                      ^`'",",:,"^ ,;:^:I>]?}[]]~>>!i<ii~--<I  "
                                       ;:IiI:^`^":i<ii>?}}11}[?~<<<_?][()j({+`
                                        i]][?~>;:+-+~+?{{{{{{{}?__-[}_-|/[1][^
                                        i1}[[]_<i~_?[{1\\)111{[?~<_[{_}|)??[I
                                       ,}1){{1{[]?[1(\tf\(1{[?_~>>+?]_]1[}?:
                                      "}{1111)11)((|/ttt|1[?--+>>~~>]1(1?>"
                                      ,{)1)|1]][1((|||(1{}[]??+<~~!i++~!;,
                                        ;i<~~~_++]{{[[[]??][]?_~<i!~+>IIl:
                                          IIli~>lIi+-----?][]?_<!i+-+il!!I
                                          ,<!i><++~+----???_~>!!>_-_<ll>!l"
                                           +<~~_-????--+~~i!l!>~-??_>I!<>;+i
                                      ";!>+~<+_??-+<iIII;;I>+_--]}[_>I!<<l]cl
                               "I>_?}1))(|)?<i!l:,li[r>;l!<_??-?[}]+ili><i+L{~iI
                        ^:Ii+]})(((()(1{{)(|//\1}[)\Jow-i~<-?-_?[}?<!li<~;|m)?-{)[+>!;^
                ^;!>~-][{1)(|)(((((((){}}{)\/t/\/\\\rmap[>+~~+-]}}->ll>~~iqU)[--}//({[?+i;"
            ^<~?{11)))11)))())(|||/\t|)1[})((\\|\||/|Jd#a)i_++-?]?+il!>+!Xar([?]][)||)11[]]-~i;^
            [({]{1()))(||||\|\\/\//frt/t\1(||/|\\\\t|vphW*\i__++??<l!i<>\*Z/|}]][}[{(\||({[}}}[]-<I^
           >)1)1{\|(||\\\\\\|///\\\tftt//\|/|/|\\//ttrqa#&#j~]?+??l!~_i{hkC\\)}[}{1111)((|(1111{{{}]+i:
           +)1|\)\\\\\////t\\//\\\\ftft////ft\\\///\/two#MM*X}]+?_l~?~-qowJ/|1{[[})()){1||/|\\\|(()1{{}?~i
           [11|/\)tt/ttttffttt/\||\ttft//\\|/|\\\/\//tQa##*b*qf+[~<-~?w#bZYt|}}}})(/|\))\(|\\///\\\()))1{)}
          l({{)tj\trjjfffrfffttt/\//tfft\///ft///////|Yp*%Wbq*#\[[[?\mhhpZLx|}}}}{1|(|(1())\|////\\/||\|(1|l
          }))))(tjtfrjjffjtttttt/\t\/ffjf/tttf///////)cbka#WWMU)1))rkwpbaakQ1}{{{{{)))(1)))\\/ttt/\\|||\|)(;
         -()((|\\fx|fjrjjffftfjft//\///tt\|\\t/t/////(vaMakbkv[))|1v#koMapZv)1{{1))|))))((|\t/ftttt\/\\({|{
        <()((|\ft\rt(tfjrjfttffjff//\//tt/|(\/tttttt/|ndpa*#c}|((((1uqmOZOYu()1))))|)))1()||t/tttt/\/\{[(|l
       ,))(|\\tr/ttj|(\jnjfffffffftt//////\11(/\/tttt\jkmOpC})()(((1]{/JqCJC())))))|1)11(||\//\ttt/\|}-((-I'
       ~|)|\//tjf|///|1/xrjjjjjjjjffftt///f\{[{(\/ttt//Cqmqj1())1{1/uQwmLUCY||(|||\|)(1)|\\//f/tttt(}_||]-l'
       -()\\t\/ff\(|\\1)ffjrrjjjxrrjrrrrjjxf|{[}{)|//\(XJZdt{((1tzCmpbpmmmw0|||(|\\||({(|(|||/\\//|}-|([{?>`
       }))|\/\///\())){]/fjjjjjjrjffjjjjjrrjt(}[[[}(\\|QCJOwj11fmqwmwddppqmL\|||||\\\)(/\\\\\\t\\/1-\\}(1}?:'
'''.strip("\n").split("\n")

FONT_SIZE = 9
CELL_W = FONT_SIZE * 0.6
CELL_H = FONT_SIZE * 1.18
PAD = 14
DUR = 9  # seconds for the full reveal
STEPS_PER_ROW = 3


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def staircase_points(fw, ch, row, frac):
    y0 = row * ch
    y1 = (row + 1) * ch
    x = frac * fw
    pts = [(0, 0), (fw, 0), (fw, y0), (x, y0), (x, y1), (0, y1)]
    return " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)


def build_reveal_animation(rows, fw, ch):
    values, key_times = [], []
    frames = []
    for r in range(rows):
        for step in range(STEPS_PER_ROW):
            frames.append((r, step / STEPS_PER_ROW))
    frames.append((rows - 1, 1.0))
    n = len(frames)
    for i, (r, f) in enumerate(frames):
        values.append(staircase_points(fw, ch, r, f))
        key_times.append(f"{i / (n - 1):.4f}")
    return ";".join(values), ";".join(key_times)


def render():
    rows = len(ASCII_ART)
    cols = max(len(line) for line in ASCII_ART)
    fw, fh = cols * CELL_W, rows * CELL_H
    width, height = fw + PAD * 2, fh + PAD * 2

    text_rows = "\n".join(
        f"    <text x='0' y='{(i + 1) * CELL_H - 2:.2f}' xml:space='preserve'>{escape(line)}</text>"
        for i, line in enumerate(ASCII_ART)
    )
    values, key_times = build_reveal_animation(rows, fw, CELL_H)

    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width:.0f}' height='{height:.0f}'
     viewBox='0 0 {width:.0f} {height:.0f}'>
  <rect width='{width:.0f}' height='{height:.0f}' rx='6' fill='#0d1117'/>
  <defs>
    <clipPath id='reveal'>
      <polygon points='0,0'>
        <animate attributeName='points' dur='{DUR}s' repeatCount='1' fill='freeze'
                 calcMode='linear' keyTimes='{key_times}' values='{values}'/>
      </polygon>
    </clipPath>
  </defs>
  <g transform='translate({PAD:.0f} {PAD:.0f})' clip-path='url(#reveal)'
     font-family='"JetBrains Mono", ui-monospace, monospace' font-size='{FONT_SIZE}px' fill='#a78bfa'>
{text_rows}
  </g>
</svg>"""


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "ascii-face.svg"), "w") as f:
        f.write(render())


if __name__ == "__main__":
    main()
