#!/usr/bin/env python3
"""Render the ASCII-portrait SVG with a one-shot typewriter reveal.

The ASCII art itself is baked in below (converted once from a source photo,
crop (0,0,502,379)):
  - Base shading: PIL ImageFilter.UnsharpMask(radius=4, percent=300,
    threshold=2) on full-res grayscale, downsampled to a 260-col grid,
    mapped through a 70-level luminance ramp.
  - Contour overlay: skimage.feature.canny(sigma=1.8, low_threshold=0.065,
    high_threshold=0.15) on the full-res grayscale (not downsampled) finds
    jaw/nose/eyebrow/eye/ear/collar/plaid edges that don't separate by raw
    brightness alone. The mustache is masked out of the edge map (pixel
    box (187,236)x(192,214) in the 502x379 crop) so only the true, subtler
    mouth line remains - the raw mustache edge read as an exaggerated wide
    smile. Edges get one round of 2x2 dilation for a crisper/thicker line.
    Each grid cell touching an edge pixel picks a line-drawing glyph
    (-\\|/) from the dominant local gradient direction; cells with locally
    incoherent edge directions (tight detail like ear cartilage) fall back
    to a dense ramp glyph instead of a misleading single-direction stroke.
  - Background thresholded to blank at max(R,G,B) < 16.
Re-derive it from a new photo with the same pipeline and re-paste here - no
image processing happens at build time.
"""
import os

ASCII_ART = [
'                                                                                                                                    ,-~,``",""^```````\\|d--dd\\\\\\',
'                                                                                                                           d--II"^^^  \'``    .\'\'\'\'\'\'.. \'. \\-d\\\\\\d\\\\\\',
'                                                                                                                        //i;"`\'`                               ---d\\\\\\\\',
'                                                                                                                    //-/-_l^                                         d\\\\\\\\',
'                                                                                                                ///;;,i_>I                                               d',
'                                                                                                              /;," ^^^                                                        d\\',
'                                                                                                           -/I:"",I:                                                          |\\\\-',
'                                                                                                      ///!,:^ ^  ^                                                              \\-I!\\\\',
'                                                                                                  d /?l`      ^,,:::::                                                             ,,,-\\',
'                                                                                              //-I:`        ^:I"`""^"                                                                  ^\\\\',
'                                                                                            //?:`",,:^       "^                                                                           \\',
'                                                                                        d//<!"  `^":IlI,`                                                                                  +\\',
'                                                                                      //l:"^     `"I;:`^^``^Il!il<-?-//                                                                     i\\',
'                                                                                   //`,I"`^     ":;;"   ^|\\--------                                                                          +\\',
'                                                                                  /`^!li,^      :"                                                                                           ,|',
"                                                                                />^'IlIl,                                                                                                     !|",
'                                                                                /^"",":` `"^   !!,     ;;                                                                                     ^/',
'                                                                               |^\'","^.  I}I``!i"                                                                                            \';d',
'                                                                                |"^     ^I?I ;i>l\' \',:,^                                                                                    "l_|',
'                                                                                |""`    ^"I`\'^:I~,,I:,""`     I                                              d--                            !;]|',
'                                                                                 ":"     ,``",:l:\'i_``,:I;  "!l                             /-             /d|]|                       I;   ll)',
'                                                                                 \\,, ,  ^\'\'^^:;^\':<l::I!>l::+l""`          l:               \\-///\\d/\\/| d//il</                        !     ,\\',
"                                                                                 |I   ` `..`^,,' ;-<`^^,,^^;ll;!;^                          //-!I;Ill--\\|_<,,,/d\\                      :     ,}",
'                                                                                  \\~:^```\'      \'"".\'^^`^\'"l",::I`  "I     ^:;d             |[[i\'"l!;!_!^`^^  `!iI:|--,`      ,^ ^^ ",,      <|',
'                                                                                   \\I"`\',:        `l:,,"",,^.`^"``  i;     `^d|\\|          |~!l\'^^`I;l" ."I".`:;+I!;:;,IIIl:"^""^^^^^^^^^^ ,`-',
'                                                                                    \\I.`<~      ` ;I,ii,"\'\'^lI,\'`I".<i^   \'!:d|||          |?/--\\d| :`,>ii_l:Il!Il!lII^,!ll,"^^^^""""^`,,",`!|',
'                                                                                     \\-,",    ``\'":":>!\' .`>?i,.`;^ "I,^^^ ;_,/t|\\..       \\d//f\\-d\\-i<<>!!>i><~<lI!>i:\',::"       "I:,\'^,"^-',
'                                                                                       \\\\d`.  ``.:;;;;^.^,;+]~^.^I^`"`",":;\'";d|d|`. d-\\  .//rt|){)\\\\\\<+-~!Ii<<!li!><!l;^\'^`         ,;^`^\'i|',
'                                                                                        |||\'.\'``.":,,"\'^;i__<<\'.,:"^\' \'~:;+~>`\'-/^`  .|d\\\\d|/({}11}1\\/ii>_-ii>~++\\\\\\I:^  |------     `^^",id',
'                                                                                         \\\\^`\'`\'."/,:,l;,!i:^"":`.,`   ^. llI.  ">^\'/d|cur(1)1[[[]?}]|ii,!~-II+<-?\\\\|-/-//------\\\\\\      l|',
'                                                                                          |\\^ .  ||<I":"\'  .`:~`.^,"" ||--\\\\ ``\'I!\'|d\\|\\))|)){}[[[[}||>>!<,:;:I.///d\\-//[|dv---\\\\f\\\\\\    \\|',
'                                                                                            d\\\\\\ ||>;^.  `".^,. ":  //d|)||\\d-:`,//|f/)}})()1{}}[[[[|/I>l|d-I"-d//-(1(-|ddd|||\\\\[jx-\\\\  !|',
'                                                                                             \\\\--//---\\--I,\'  .",--//|-l~-]-\\-dddd|)(1}[}11)11{}}[}{|Ii~i--\\d///\\|1[??!|d||{|O&|\\l(uC|| d',
"                                                                                              \\://\\/----\\-\\^  ^`'\\\\d~<>>i>>l|d\\\\\\(11}}[[{1))111{{1()|<~____]-]1{{}??]-,/d-d\\d--\\\\|!tu||.",
'                                                                                              |d|p\\-|-\\-\\-\\\\\\--\\d\\|\\|dd-ddd--"\\\\\\|/1){{1{11{111{{)||\\\\\\__+-+_-??]1-|;<;\\d--\\| \\\\\\|+(c||',
'                                                                                                dddd|(\\((vz|)t//\\/-||--/--?\\d----//|f//1{{{11111)(\\)1|\\|>~i,+][}|j\\\\ ^;-d\\\\-\\\\\\d|}?\\C||',
'                                                                                                |j|)1]~+-]-+<-\\\\\\\\--/:Ii<-]?(t\\((|/xnnr(}[111))11)){1|||l<l"?][}|tCd.]|/dd\\/d//||?}J//',
'                                                                                               /uj\\()|\\\\\\----\\-!~__~~~~~-][[)|)))|frrf|(11))((111////-/|II!l-?-||1dd<_|\\d/d//>d/}{Q//',
'                                                                                              |zvj/\\||1{---t---\\-\\~_-_-]/}{())1)|tnnf\\/|()))1{/////--+-!;iiI<]-||||\\d/ ///1}}}{_j///',
'                                                                                             /|rr\\||1)1{1|\\/tft)-\\\\---+//))|\\\\|ruuunr/||111{}///?-___+>il;Ii--_\\||d-/-///x{[-[tu//',
'                                                                                            |/j/|11(((()))1(/|){{))1---d||||ttrnuuunf/|1{1}??????-?-_-;I;!>_-+~\\\\\\t({)rcx][{tYd//-',
'                                                                                           |/n|{}11(/t/({})\\|)11)(\\t\\||\\\\\\\\\\/tffrrnxff/11{]+-??--??<>>I>i~-[?+i`-|\\v/[{/f)f|/////',
"                                                                                           |Qj//-\\?-~+___-]((}[}(((\\|((\\\\\\\\ttttt/\\/\\|()1}}[[]????][<;;I>~+-??<`'I\\\\\\\\---///// ,|",
'                                                                                           |bu///\\d-----\\\\|~-[[[{)(\\\\||/t\\/////\\|(()1}}}}[[[]????[[+li>>++-->: ;?[_i----// ."">|',
'                                                                                           |\\\\Y--\\-------/d;;][--?1(\\/\\||((())(||1[{{}[[[[[[[[]??}]~i~~~+~__I.^!-[-_!:^"`^:Iil\\',
'                                                                                             \\\\\\}`-------/l+]][?_~-[{(|())111)))1}[[[[[[[[][[[]]?}[~i~~~~<+<^.i_-?_?+iiI",Ili;/',
'                                                                                               \\\\>;>!Ii-~_]}[}[]-_--]{|/\\|1-_-?-?[]??----??][[[[?][-i~+~<><i":+[-_-]>ll,^Ii<!I|',
'                                                                                                 ";!\'    \'^Ii++>l:I!!?}|(1[--??-_--__-+~+_]}[[[}?[[-~~~~<i,.,<-][[{~!l:,I<~+iid',
'                                                                                                  >\\{I:lllIlI;I:,.    ,~++-][???--?-----?][}[[]]]?-__~~!l,`,i-}{[?+iI",Ii>~<l:-|',
'                                                                                                   I\\1+>I;I:>rj]++~il^  .;~?-----??]]??][[{11[??[--_~//: ,<?]}}[]?+>:",Ii<~>Il<|',
'                                                                                                    |/}[[}}]}t[-_?}11[-~>+---------?][]???}}}]?]?//-///`;~-]}}[[?-+l"";!>+i<i!Id',
'                                                                                                     n/--------I>+_?]?}}?__----------------___/////-/^;I>-?__?][-~>l`,Ii~_i<il:~|',
'                                                                                                     |u\\\\-----dd~~~_-_--------------___]}[?/////\'.."Ii~+_-?]?--?_<l;`^;>-->>!!:`\\|',
'                                                                                                     |Q/)}---[-?-_++-~_---?]?]?-__--_++_-//d/.\'^I>>~+<+?-?[[[[}-~i!,^"I~-+ii!:. |\\\\',
'                                                                                                     |n[]?]11)){{1)))1]?]]]]?-?__-~~/--//-.`;l>~_]--?--_?[})){1]+>i"^:;+-_~<i,. |$\\\\',
'                                                                                                ----//+++~+?[][{(|(|(({]?[?_~~--/---//^"^,l>~+][]-_----?}1)|(1{?+>I^"^"~-__+>^  ||z\\\\',
'                                                                                       ----------UUz-\\|"><>~~~+[}]]?-_-_----/--//...\'\'^"^:l>~+-_++_---??][{)){[+~<l,",;>_+++<:  ||||\\\\\\',
'                                                                                /---/--uxvYcnxf\\1)|()\\d||.\'^`:!!;\\-//----   "-\\\\    `\'`;Il><+-?[]--??-?][{11}[}+>il:"Iii<~++~!` /|||x|\\\\\\',
'                                                                           /--/-XUUcnxjt\\rv()((\\fffft|\\\\\\--\\---        !\'`--d/d\\\\ \':l!>~~<_][}11[]????[[}1(1)}?+>iI":l!>>><+~!` ||$|1|,~|\\\\\\\\',
'                                                                     -----/QYunf\\1{1{}}1{n[}{}[?|trc//\\(txv----\\\\\\d---//d/-d/$@\\|\\ ^lii><>~-}){{}]?-+_-]}{1()[+~>;:,;!i~<<~~~,. ||||~||:!d\\\\w-\\\\\\--',
"                                                             d-------UXurf/)111111)))1)[xx])}[[{}}1{[}))txrnwtzCnn0Jx}fnvfI||B$@\\\\\\ `I!>>ll+{({[?_+<<_?}1)1{}-~>!l,,:!>~~+++>'  ||||[||:i>\\\\||vj\\-/------\\\\",
'                                                     d----d----cvj/rr}{{1(1))))))(|||((}n{})1{][{11(/t\\rcvr\\U(t\\\\ftjj/|//(!||W%$@\\\\\\\\`I~~<!l_[[]+~<>+_-[1{)()}+<iI:,;!i>~~~~;  d|$||-/|,~++i\\\\\\v-----\\{\\x\\\\\\-\\\\',
'                                           --d-d----czvxrjft\\||({[[n{))(||(((((||((|((1/|])}]?[}}11)11|jt\\\\|v\\\\|\\||\\\\)(|\\(]\\|\\M8$@$\\\\\\\'I~+~><~+~ii<<-}{1|\\/\\)]~ll;",Ii><+_+>\' |||$||}||I<?]]~\'|d-Ycudd\\\\<_[)\\/t--\\\\',
'                                     /d-/--Xcrfrrjt|()1{}}{{{1)))[xf1)1)((((||||\\||\\(|1U|-)}?]}}}11)11fjft/(U|)(\\\\\\/|{1|\\|1I||oh#$@$\\\\\\.:~+++~~~>+-?}}[}1)}}?_+il:,:!!><+-+I. ||@$|.f||!l<-?_-l\\\\\\tjrx\\\\\\\\-]d\\\\?1ft-\\\\\\-',
'                                //----xfj/({]1){{1{{{1111(()))))1(v})))(||||\\\\\\\\\\|\\|((r/|{11{1}}{{}{1(\\\\\\\\|1J}|||\\/t\\((\\tt|]||&hh8$$$\\\\\\ "!~++++++_--?[{}[{)[~~>:",Ii!>+-+!\' ||$$||.n||+i~[[-[[>\\\\-jfjnt\\\\\\\\-\\\\|l+?[)/r\\\\-\\\\-',
'                              ///n1-\\|ft\\()1/\\1)-\\/-------------}t{[{{11)))11)))|\\t\\f{J|d\\|((]+-}]~d/))))||(J1/|\\/\\\\\\\\|\\tt/):||ho*%$$$\\\\\\ ^i+++~~__--??[{{1[-||;,,:liii~+>^ |||@@|/^x||i<_[[][1}+\\\\\\((|((/|\\-(\\\\\\-???][{)|\\f\\-\\\\--',
'                             //Uu|}~/dd(({}[n}}|------------------d--------------dd\\dd/dd---|/-d/d/dt)[?]|)fv)/\\///\\\\(1)(|([:||W*||B$$@\\\\| `>-_++++__+_-[}[-+//,,:liii><>:./||@$8|!:v||~<+?---{){}\\|\\((//\\/\\|((t\\\\d????][}}[{1)/\\-\\\\\\\\',
"                            /|uc/}[[<||({{]/f][}1{})))))))()())[xf1((|\\/\\|\\\\\\/d----ddddd-\\/\\\\|--ddd\\-cj){?_fx{|((|\\\\|)(/rfj)_ |Bo||%$$$@|\\\\ `!+--++_+><-?[}1//,',Iii>><<l` ||@$@h|:+z||?__--?[}1[}}+\\\\\\t/\\\\\\t\\||||\\d[[}}[[[[[{[?{||(/r\\\\\\\\",
'                           ||uuj1)()1~|||()Y||||(1(|tt/\\\\\\\\\\\\\\\\{X)|\\\\\\/////\\//|/|({-d||d\\\\/t/t/r\\\\\\-\\d--\\c|Y\\})trf/nftttt{YJ~"|Bo||&%@$$@\\\\| \'l_--?_++~_}(|||l,`,!i><>!;` /|$@$WZ|.+z\\d\\~?[}[}])(})1]\\\\drtt\\\\/\\|\\}||d}{{{1{}}11]??][?{1||\\\\\\\\',
"                           |Ut|\\\\1)11?||f|vr-\\(||||/ft/\\\\\\\\\\\\\\1|X}\\\\\\//////\\)((///(d-|djffft\\/t/txu/ddd\\\\\\d||t|))(|||)1)t\\/O>,||o#*WW8$$$@\\\\| ^i+_--+>>~1//||```l>~+~!:' ||$@$8kQ|.-v)/|\\-[}[}}}|[?{1+\\-\\---1\\f}1()\\\\\\)}[[}{}{1){}[)\\{]?}1)|/\\\\\\\\",
"                          ||Yf))|\\|()\\+|||0](||((||\\\\///////|\\?Y()\\\\|/fftt/\\\\\\\\\\t((d|u(ftttt///\\)1)})(X|d-\\dd---xf///ttftf[Ct:||WM8WW8B@$$@\\\\\\ ----\\-i!!{n||^ .I<_][?i' |||@$%hOO| _n[dddd/<[{}}[r}|\\d-//\\--|[{\\()|{\\d---d-----/---}{t?]}[}[?1(\\\\\\\\\\",
"                          |UCj)1(|\\/|t1:|Yv[||\\|(|\\//////////|fU?/||(/tt////////t||dZ(tfffttt///\\\\f||)uJ(\\--\\\\\\dd\\\\//\\\\//t(}Ql||$8%MW%%&B$$$\\\\\\ ~(\\\\|>!l?v||' '+-?}[?I /||@$B*bwO|`]x|||}|d\\|+}[[[n-dd--d-)11~+ct/\\11dd1ft/fr------1{)u1)11)1}[}{(\\\\\\\\\\\\",
'                          |YJt){1|////u>|h|t//\\||\\//tt/////\\/1Xt(\\(\\\\////\\\\\\\\\\\\\\\\)d|U)fffftt/\\/ttrrr/\\fp(/tfrxf\\|\\///\\\\///t{fu ||@8WW%$$$$|\\\\$\\\\ I}(\\|;:[U||  "_}}{-!` /|@$$|/pZL|I}/||_1}}\\\\-]?}}{c/|!-{ff|[i-)|\\|\\1v\\d)(||/tt/\\||()})u}11}}}})11{}{\\/f\\\\',
"                          |Ju/{}d||\\/xx}|d1ftff////ttttt/t/t//C[t////////\\(||\\\\\\(1d|f\\ffrftt/\\/ttftf/\\}Uv|t/\\\\\\////////\\\\\\\\|<v<||$B88/--d----8B\\\\\\ i||,;(C| ',+][?~;' ||$$$|||qp||>]t/|]{}}}11)[?}][}c\\(\\\\t\\|~-n\\f/|/|||)/\\/t//t\\\\\\\\\\/(xz?t|11{}11){}?}{)h\\\\",
'                          |Juf)1{|/fjj/r?d|fjttttttttttttt/j|Xu[ftt///ttt///\\\\\\\\)|dL[fttfttttttt////|(]1C}||\\|\\\\\\\\//tttt///|]+t||%#/--/---d\\po$$\\\\\\\\ ":^|||.^>]?-<:. //$@$%||pwm||<[rd|}{}}}}->}()(\\{C||\\\\t|)_+n|/\\)){xt1t////t/\\///\\|\\[ut_\\())))))}{1}[?)C\\\\',
'                         |Jvt){][d|||(|t[||nurftfffftffffffjt0\\/jjjrxfffttt/|\\||(ddx{fttfftttj||/||\\\\|1-z|})\\\\//\\|\\|())))))((~u||&|\\d-/8@$-d/-\\\\$$\\\\\\\\ Ij||^I+--~;.-//$$$$8|mZm0U|}-X|!-[]}}}}-\\Xnjf)L(|\\\\ff|_-tt\\|(|}{C)\\||/t//\\ttft/\\|1X)/|((())/|\\1)111nY\\|',
'                         |Jvf({]?]\\d-dd-d\\||d--------------/|/d\\\\\\/ff\\//////\\\\\\\\|dQ-tttfjffjxx))\\\\\\\\|1{}[L[{()(\\\\(1|txftjuunf1[<|$d|d|B888|/-L\\\\|B@$|| ~)||>_?-~I.///$--d/||mOZQC||{/|[][++?[}{]-[1\\}C/|\\\\frf+<ft|((((>Yn|)\\tt///tt/\\/\\\\)|c|\\(|||/tt/|()1{rY0d',
"                        ||Yu\\11[?_\\\\xtjzdddd----------------dd-------rr----d-\\/{ddY?r/fffjrrxr/}1|\\\\/rt((Of|cnnrjjtt\\t|))|\\|1];;|$odOdd$$B\\\\\\\\-d/@BB$| !]\\\\d/[_>'///%C|d&dd|m\\\\|C\\\\[||}[[{}]}{]]?~?1?Y())|fnr<i/|((()|<\\u}||\\////\\\\////\\\\]uf1|||\\\\|t/\\t\\|}rcO|",
'                        |Lcf(11{}?/|f\\tn|\\-{tftft//\\|\\|||\\}\\/|---------d---------dd}\\\\/\\ttrt\\//)fxxrjuj\\))w]\\\\\\\\\\|\\\\\\\\\\////t|{~ |$bX||\\\\$$$$$8%B%$@$/| <]1{11)]"///Mv||%M||d/o\\-\\\\\\)_i-??]{1\\\\1)}-+[<f)?{)||f}<\\(||1}})-U{|\\//fttfjrtt///1(L}||)|\\\\|\\|\\/|}jxC|',
'                       ||cj|))))(}//d\\txuxd||juurjrxrrfffr(L|dttt|/ft/\\\\\\\\\\|-\\---dd-d------d----\\t/t/\\/t/[Qj}ftft////////////)? |@kd/0\\\\\\\\\\$$$@8B@$d//i]1}{))[>|||WYd/bdm|///@$%8$\\|`<_?}{}{}}1|\\(()+rj?}1{{|}-\\))()1)|1Xv1\\/tfrffjj//t/j/?cr[|||\\\\\\\\\\td|1ujC|',
'                       |Jrt|(((()|)]\\\\dd|dC|||uuuxrrrrrrrf//|frffjrftjxrjjfft/|]|||(1///--------/{|11)///)|Y}ft//////////////|]"||8$--\\\\X\\\\\\\\-\\$$||/ >[1()1(}+ ||B*0|\\qwd//%$%|||h/|;i+-[{1111{11{1|-rx}(rttn[_\\)))(|((|\\L[t/tfffftt//|\\/|1-C{1((||\\/t/d/|zup|',
'                      |mnt\\(|((((((\\\\/)||ddo|\\(rjjnxrrrfx)Y||fftfffftfrjjjftt/|]U\\}\\/t//trt/txff|1\\/||jf/t||\\|/t//////t/ttt//(]:||a$$$|\\\\-\\\\U\\---//^_}1))(||}~ ||88oZ0d//$$/////hh||_+?]}}{11))11[1|>zf>}})\\t[+f|())1{{)+J){|\\\\/\\\\/tff\\\\tj/]/C]|\\t/\\|)//||vU||',
'                     /wut\\()(((||(|\\rv(||-|#||_/xrrrrrjju}Z|\\fjfffftfjfjjfffjf\\)m}((\\///tj/\\\\/jjft\\t1[(/\\\\|dX}ttttttt/tttfftt)-,||#|\\$$$8W\\-\\\\dd||:?1)))|||(}+`|||$%p///$////wOOw|dl?[}{){{{)))))(|\\+Uf-{1)|f[+ut((/jxfjtxLtnrvcvrrxccnnnux|?U\\\\-d--ddd\\|/rQ/',
'                    ||zj(||((|1/\\)(fcvx-?fd||d|+ttffjfjrfjY|rjjfft\\tfjjjjjfjrf{fC?f////////t//tttf\\t/1)\\t/|d|\\fjttttt\\/tttt//\\}I||$O\\\\-@@%8$$$|||I]((((((()()}+.\\\\\\$\\/|////LwpmO|d|-1]})1}}1)))))((|[C\\]))()\\?>\\111{{1))(?U{)//tr\\1)\\///||\\)-/|ddd/-]-||/-Ud|',
'                   |/ft\\)()(((1//(1jcuxt1}||||d\\?ttftffu||j\\rjfff\\)tfjjjjjjjft+O(1//t/)\\////tjfttfj/|)1/jttddX1ftttt//ttttt//|{>||$-|\\\\-\\\\$$@//|^_1(((((((((((}+"\\\\\\\\$$//o#OLmwd|-/|<]{())1)())))))|?L}[)))|(?]|(())11)|\\1uc-f/ttfffffjjf//t|}Q|d??}1^/|YU/| \'',
'                  |/cxf|(((||)1))1{xurf/ft/d|Y\\d|}tfftjd|d|nxxjff/\\fjjjjjjjjj||0?j/tjt|\\/////ff/t/jt\\}?]1|\\|dL[/tttttttttttt/\\1-||$-|||-\\-\\--||`>-1|(((((((((()}[+"\\\\----dpokOddd/$|l-]111))))))))))-J+{)))\\\\+{((|(|\\\\\\\\\\/)m?(//ttftttttt||\\\\[X||>>?/||c|//d `',
'                  /Lxn\\(|||t/|vt1//Yzf{1\\xf_d|f-|\\1\\//r||0txrjjjftfjjjjjjjjjj}vu{fttt\\////////////tt/t}+?)|/d|n(ttfjftfffttt\\|{_ |$B/||dbpkMd| >-[)|))))))(((()))1}~. ////8@8\\|/|//|l-]111)))))))))(1C+1)))|f_[()(|||||\\//)zn{t//tttttfffftft)r||i>/||C|/|}| "',
"                  |0j){((||\\|)x/(\\\\UYXu1(---/\\dnd\\i(){td|Uxnjfjffjffjjjjjjfff1L|tfttt//ttt/////////)z}|/!+}[-d\\?|)|t/\\|||||//|}?^|$$@d|jqh%$d|;_[)||()))))((()))}<^////-@$@//-|d/-/|l~_[}{)(||()1)){\\X~1)))|1<})(\\\\\\/\\\\\\/t/{L}/\\/ttt|/tfjf/\\t{\\/;!d||J||/~t| '",
"                 ||ux\\((||\\/((x/t(\\rrxn)-d\\--d|/cd|/[_]|Zxuuxrrrrrrrjjjjjfrn((Z[rfffffffftt/t/tttt|)p]|dd+[[[\\dj1ftffnrtruvrnnj)l|\\*h8|\\rah/| i-{(\\\\\\()))(())1[<:////WW---d/d[xvtf-|+|\\//((/\\(((|\\f1/n_((|)\\[~{((|||/////tt1Yu[t//tttffjxj()t|||:||o||||+-t|  '",
"                 |qcj\\(((|/\\1/u\\\\\\jxunnj|]/|d-t1)U-d+][dzffrjt/|\\fxrffjjrjrr[cv\\rrtffjffffftttfttt)uJv/f||<+_-dd-))\\//t|)(||()([,||UmkMdddMd| <[))))1}1)))))1_>{///&MB/d/|/fuzXv/-$|'][)\\t\\rnn\\)|\\t)vr_(|\\\\(_]/|||\\\\/\\/////\\\\L-f/ttffrjrxf(1//<,^/|/d/<)[_/|| `",
]

FONT_SIZE = 8
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
