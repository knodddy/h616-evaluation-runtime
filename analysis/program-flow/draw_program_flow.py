from pathlib import Path
from xml.etree import ElementTree as ET
import json

import pymupdf

HERE = Path(__file__).resolve().parent
WIDTH = 183 * 72 / 25.4
PURPLE = "#70449C"
INK = "#292333"
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def element(parent, tag, **attributes):
    return ET.SubElement(parent, f"{{{SVG}}}{tag}", {
        name.replace("_", "-"): str(value) for name, value in attributes.items()
    })


def text(parent, x, y, value, size=10, bold=False, mono=False, anchor="start", color=INK):
    node = element(parent, "text", x=x, y=y, font_size=size,
                   font_family="Courier New" if mono else "Helvetica, Arial, sans-serif",
                   font_weight="bold" if bold else "normal", text_anchor=anchor, fill=color)
    node.text = value
    return node


def canvas(height, title):
    root = ET.Element(f"{{{SVG}}}svg", {
        "width": f"{WIDTH}pt", "height": f"{height}pt", "viewBox": f"0 0 {WIDTH} {height}"
    })
    element(root, "title").text = title
    element(root, "rect", x=0, y=0, width=WIDTH, height=height, fill="white")
    return root


def arrow(root, points, name, color="#766C83", width=1.25):
    group = element(root, "g", id=f"edge-{name}")
    end_x, end_y = points[-1]
    prev_x, prev_y = points[-2]
    if end_x == prev_x and end_y > prev_y:
        tip = [(end_x, end_y), (end_x-3.2, end_y-5.2), (end_x+3.2, end_y-5.2)]
        stop = (end_x, end_y-3.5)
    elif end_y == prev_y and end_x > prev_x:
        tip = [(end_x, end_y), (end_x-5.2, end_y-3.2), (end_x-5.2, end_y+3.2)]
        stop = (end_x-3.5, end_y)
    elif end_y == prev_y and end_x < prev_x:
        tip = [(end_x, end_y), (end_x+5.2, end_y-3.2), (end_x+5.2, end_y+3.2)]
        stop = (end_x+3.5, end_y)
    else:
        raise ValueError("Arrow endpoints must be orthogonal")
    path = "M " + " L ".join(f"{x},{y}" for x, y in [*points[:-1], stop])
    element(group, "path", d=path, fill="none", stroke=color, stroke_width=width,
            stroke_linejoin="round")
    element(group, "polygon", points=" ".join(f"{x},{y}" for x, y in tip), fill=color)


def box(root, name, x, y, width, height, title, color=PURPLE, opacity=.1,
        code=(), bullets=(), title_size=10, code_size=7.5):
    group = element(root, "g", id=f"node-{name}")
    element(group, "rect", x=x, y=y, width=width, height=height, rx=5,
            fill=color, fill_opacity=opacity, stroke=color, stroke_width=1.3)
    font = pymupdf.Font("hebo")
    assert font.text_length(title, fontsize=title_size) <= width-20, (name, title)
    title_y = y+17 if code or bullets else y+height/2+title_size*.35
    text(group, x+width/2, title_y, title, size=title_size, bold=True, anchor="middle")
    baseline = y+32
    if code:
        mono = pymupdf.Font("cour")
        longest = max(mono.text_length(line, fontsize=code_size) for line in code)
        assert longest <= width-24, (name, longest, width)
        left = x+(width-longest)/2
        for line in code:
            spaces = len(line)-len(line.lstrip())
            text(group, left+spaces*mono.text_length(" ", fontsize=code_size), baseline,
                 line.lstrip(), size=code_size, mono=True)
            baseline += 10.5
        assert baseline-10.5 <= y+height-8, name
    for item in bullets:
        assert pymupdf.Font("helv").text_length(item, fontsize=8.3) <= width-34
        element(group, "circle", cx=x+14, cy=baseline-3, r=1.2, fill=INK)
        text(group, x+22, baseline, item, size=8.3)
        baseline += 13
    if bullets:
        assert baseline-13 <= y+height-8, name
    return group


def export(root, name):
    svg = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    (HERE/f"{name}.svg").write_bytes(svg)
    with pymupdf.open(stream=svg, filetype="svg") as document:
        with pymupdf.open(stream=document.convert_to_pdf(), filetype="pdf") as pdf:
            assert pdf[0].get_text().strip()
            pdf.save(HERE/f"{name}.pdf")
            pdf[0].get_pixmap(dpi=240, alpha=False).save(HERE/f"{name}.png")


flow = canvas(490, "H616 boot and runtime execution")
margin, width = 14, 150
gap = (WIDTH-2*margin-3*width)/2
center = margin+2*(width+gap)+width/2
stages = [
    ("boot-rom", "Boot ROM", "#247653"),
    ("spl", "U-Boot SPL", "#286CA8"),
    ("tf-a", "TF-A (BL31)", "#BB741F"),
]
for i, (name, title, color) in enumerate(stages):
    x = margin+i*(width+gap)
    box(flow, name, x, 14, width, 40, title, color=color, opacity=.11)
    if i < len(stages)-1:
        arrow(flow, [(x+width+2, 34), (x+width+gap-2, 34)], f"boot-{i+1}")

runtime = element(flow, "g", id="runtime-section")
frame_left = 160
element(runtime, "rect", x=frame_left, y=84, width=WIDTH-frame_left-2, height=392, rx=8,
        fill=PURPLE, fill_opacity=.025, stroke="#B7A1D0", stroke_width=.85)
x = center-width/2
states = [
    ("select", 98, 40, "Determine test to run", .12, []),
    ("prepare", 166, 104, "Prepare test", .20,
     ["Load selected loop", "Disable UART", "Quiet peripherals", "Set operands and flags", "Enable instruction cache"]),
]
for i, (name, y, height, title, opacity, bullets) in enumerate(states):
    box(runtime, name, x, y, width, height, title, opacity=opacity, bullets=bullets)
    if i:
        previous = states[i-1]
        arrow(runtime, [(center, previous[1]+previous[2]+2), (center, y-2)], f"runtime-{i}", color=PURPLE)

arrow(flow, [(center, 56), (center, 96)], "enter-runtime")

left = margin+width+gap
right = x
terminal_height = 82
box(runtime, "instruction-loop", left, 308, width, terminal_height,
    "Instruction loop (ADD)", opacity=.28,
    code=["1:  .rept 128", "      add x0, x1, x2", "      add x0, x1, x3", "    .endr", "    b 1b"], code_size=8.1)
box(runtime, "idle-loop", right, 382, width, terminal_height,
    "IDLE (WFE)", opacity=.28,
    code=["1:  .rept 256", "      wfe", "    .endr", "    b 1b"], code_size=8.1)
arrow(runtime, [(x-2, 218), (left+width/2, 218), (left+width/2, 306)], "select-active", color=PURPLE)
arrow(runtime, [(center, 272), (center, 380)], "select-idle", color=PURPLE)
text(runtime, left+width/2-10, 270, "Non-idle test selected", size=8, anchor="end", color=PURPLE)
text(runtime, center-10, 329, "Idle test selected", size=8, anchor="end", color=PURPLE)
export(flow, "execution-flow")

manifest = {
    "scope": "Combined normal microSD boot and simplified runtime execution on the primary core.",
    "boot_chain": ["Boot ROM", "U-Boot SPL", "TF-A (BL31)", "runtime test selection"],
    "runtime_order": [state[0] for state in states] + ["instruction-loop or idle-loop"],
    "snippets": "Only the final instruction and idle loops contain code. Each example contains 256 workload instructions followed by a branch, matching the source macros.",
    "omitted_paths": "UART initialization, handshaking, acknowledgement and disconnect delay are abstracted into test selection/preparation. Startup checks, platform checks, errors and exception halts are omitted.",
    "loop_semantics": "A single destination is selected before execution. WFE can wait for an event. No automatic workload sequence or return to provisioning.",
    "timing": "Disconnect grace is 240000000 counter ticks at a checked 24 MHz: 10 seconds.",
    "source_files": ["boot/h616.its", "src/startup.S", "src/main.c", "src/provision.c", "src/platform.c", "src/workload.c", "src/workloads.S", "include/workload.h"],
    "fonts": "Helvetica/Arial sans-serif labels; Courier New code. SVG text is editable.",
    "style": "Horizontal green/blue/orange boot stages; purple runtime descends under TF-A with staggered terminal states. All execution blocks are 150 pt wide. Preparation uses short bullets; extended branch arrows carry purple selection conditions. No overall title, caption or subtitles.",
}
(HERE/"figure-notes.json").write_text(json.dumps(manifest, indent=2)+"\n")
