from __future__ import annotations

import json
import re
from typing import Dict, Iterable, Optional, Tuple

from .llm import Extraction


_NON_CODE_CHARS = re.compile(r"[^a-z0-9]")


def _normalise_token(value: str) -> str:
    return _NON_CODE_CHARS.sub("", value.lower())


def normalise_item(page_text: str, item: Extraction) -> Optional[Tuple[str, str]]:
    """Validate an extracted item against the page text.

    The LLM may occasionally hallucinate codes or URLs. We only accept an item when
    both the URL and the item code can be located in the source text (ignoring
    punctuation differences) and the description is non-empty.
    """

    if not item.url or not item.item_code:
        return None

    text_normalised = _normalise_token(page_text)
    if _normalise_token(item.url) not in text_normalised:
        return None

    item_code = item.item_code.strip()
    if not item_code:
        return None
    if _normalise_token(item_code) not in text_normalised:
        return None

    description = item.description.strip()
    if not description:
        return None
    return item_code, description


def _serialise_room_data(room_data: Dict[str, Dict[str, Dict]]) -> Dict[str, Dict[str, Iterable[Dict[str, object]]]]:
    serialised: Dict[str, Dict[str, Iterable[Dict[str, object]]]] = {}
    for room, categories in room_data.items():
        serialised[room] = {}
        for category, items in categories.items():
            entries = []
            for (item_code, url), record in sorted(items.items(), key=lambda x: x[0][0]):
                entries.append(
                    {
                        "item_code": item_code,
                        "description": record["description"],
                        "sources": sorted(record["sources"]),
                        "url": url,
                    }
                )
            if entries:
                serialised[room][category] = entries
    return serialised


def build_mindmap_html(room_data: Dict[str, Dict[str, Dict]]) -> str:
    """Create an interactive SVG mind-map visualisation.

    The output keeps every room as an isolated mind-map: a central node with four
    branches (Floor, Walls, Ceiling, Furniture). Clicking a branch toggles its
    leaves. No external libraries or network calls are required.
    """

    serialised = _serialise_room_data(room_data)
    data_json = json.dumps(serialised)

    template = """<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>Room Inventory Mind Map</title>
<style>
body {
    font-family: 'Segoe UI', Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    margin: 0;
    padding: 2rem;
}
h1 {
    text-align: center;
    margin-bottom: 2rem;
}
.room-container {
    margin: 0 auto 3rem auto;
    max-width: 960px;
    background: rgba(15, 23, 42, 0.45);
    border: 1px solid rgba(148, 163, 184, 0.4);
    border-radius: 18px;
    padding: 1.5rem;
    box-shadow: 0 35px 60px rgba(15, 23, 42, 0.45);
}
.room-title {
    text-align: center;
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 1rem;
}
.mindmap {
    width: 100%;
    height: 520px;
}
.legend {
    margin-top: 1.5rem;
    font-size: 0.85rem;
    color: #cbd5f5;
}
svg {
    width: 100%;
    height: 100%;
}
.node text {
    font-size: 0.85rem;
    pointer-events: none;
}
.node circle {
    fill: #1d4ed8;
    stroke: #60a5fa;
    stroke-width: 2;
    cursor: pointer;
}
.leaf circle {
    fill: #10b981;
    stroke: #6ee7b7;
}
.leaf text {
    fill: #ecfeff;
}
.branch circle {
    fill: #9333ea;
    stroke: #c084fc;
}
.branch text {
    fill: #f5f3ff;
}
.room circle {
    fill: #fbbf24;
    stroke: #fde68a;
}
.room text {
    fill: #0f172a;
    font-weight: 600;
}
.hidden {
    display: none;
}
.tooltip {
    position: absolute;
    background: rgba(15, 23, 42, 0.92);
    color: #f8fafc;
    padding: 0.45rem 0.65rem;
    border-radius: 8px;
    font-size: 0.8rem;
    pointer-events: none;
    max-width: 260px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.45);
    z-index: 10;
}
.tooltip a {
    color: #60a5fa;
}
</style>
</head>
<body>
<h1>Room Inventory Mind Maps</h1>
<div id=\"container\"></div>
<div class=\"tooltip hidden\" id=\"tooltip\"></div>
<script>
const data = __ROOM_DATA__;

const CATEGORY_ANGLES = {
    'Floor': -Math.PI / 2,
    'Walls': -Math.PI / 6,
    'Ceiling': Math.PI / 6,
    'Furniture': Math.PI / 2,
};

const CATEGORY_COLORS = {
    'Floor': '#38bdf8',
    'Walls': '#f472b6',
    'Ceiling': '#facc15',
    'Furniture': '#34d399'
};

function polarToCartesian(cx, cy, radius, angle) {
    return [
        cx + radius * Math.cos(angle),
        cy + radius * Math.sin(angle)
    ];
}

function createRoom(section, room, categories) {
    const wrapper = document.createElement('div');
    wrapper.className = 'room-container';

    const title = document.createElement('div');
    title.className = 'room-title';
    title.textContent = room;
    wrapper.appendChild(title);

    const mindmap = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    mindmap.classList.add('mindmap');
    wrapper.appendChild(mindmap);

    const tooltip = document.getElementById('tooltip');

    const width = mindmap.clientWidth || 900;
    const height = mindmap.clientHeight || 520;
    const centre = [width / 2, height / 2];
    const branchRadius = Math.min(width, height) / 3.5;

    function addCircle(x, y, radius, cls, label) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('node');
        if (cls) g.classList.add(cls);

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', x);
        circle.setAttribute('cy', y);
        circle.setAttribute('r', radius);
        g.appendChild(circle);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x);
        text.setAttribute('y', y + 4);
        text.setAttribute('text-anchor', 'middle');
        text.textContent = label;
        g.appendChild(text);

        mindmap.appendChild(g);
        return g;
    }

    function addLine(x1, y1, x2, y2, color, width = 2) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('stroke', color);
        line.setAttribute('stroke-width', width);
        mindmap.appendChild(line);
        return line;
    }

    const [cx, cy] = centre;
    addCircle(cx, cy, 40, 'room', room);

    const orderedCategories = ['Floor', 'Walls', 'Ceiling', 'Furniture'];
    orderedCategories.forEach((category) => {
        const entries = categories[category] || [];
        if (!entries.length) return;

        const angle = CATEGORY_ANGLES[category] ?? Math.random() * 2 * Math.PI;
        const [bx, by] = polarToCartesian(cx, cy, branchRadius, angle);
        addLine(cx, cy, bx, by, CATEGORY_COLORS[category] || '#94a3b8', 3);
        const branchNode = addCircle(bx, by, 26, 'branch', category);

        branchNode.querySelector('circle').style.fill = CATEGORY_COLORS[category] || '#94a3b8';

        let expanded = false;
        const leafLines = [];
        const leafNodes = [];

        const perLeafSpacing = 56;
        const startRadius = branchRadius + 60;

        entries.forEach((entry, index) => {
            const leafRadius = startRadius + perLeafSpacing * index;
            const [lx, ly] = polarToCartesian(cx, cy, leafRadius, angle);
            const line = addLine(bx, by, lx, ly, CATEGORY_COLORS[category] || '#94a3b8', 1.8);
            const leaf = addCircle(lx, ly, 18, 'leaf', entry.item_code);
            leaf.classList.add('hidden');
            line.classList.add('hidden');

            leafLines.push(line);
            leafNodes.push({ leaf, entry });

            leaf.addEventListener('mouseover', (event) => {
                tooltip.classList.remove('hidden');
                const [px, py] = [event.pageX + 12, event.pageY + 12];
                tooltip.style.left = px + 'px';
                tooltip.style.top = py + 'px';
                tooltip.innerHTML = `
                    <strong>${entry.item_code}</strong><br />
                    ${entry.description}<br />
                    <em>${entry.sources.join(', ')}</em><br />
                    <a href="${entry.url}" target="_blank">${entry.url}</a>
                `;
            });

            leaf.addEventListener('mouseout', () => {
                tooltip.classList.add('hidden');
            });
        });

        const toggleLeaves = () => {
            expanded = !expanded;
            leafLines.forEach(line => line.classList.toggle('hidden', !expanded));
            leafNodes.forEach(({ leaf, entry }) => {
                leaf.classList.toggle('hidden', !expanded);
                const circle = leaf.querySelector('circle');
                const text = leaf.querySelector('text');
                if (circle) circle.style.fill = CATEGORY_COLORS[category] || '#38bdf8';
                if (text) text.textContent = entry.item_code;
            });
        };

        branchNode.addEventListener('click', toggleLeaves);
    });

    const legend = document.createElement('div');
    legend.className = 'legend';
    legend.textContent = 'Click a branch to reveal item leaves. Hover a leaf to view description, sources, and product link.';
    wrapper.appendChild(legend);

    section.appendChild(wrapper);
}

const container = document.getElementById('container');
Object.entries(data).forEach(([room, categories]) => {
    if (!Object.keys(categories).length) return;
    createRoom(container, room, categories);
});

if (!container.children.length) {
    const empty = document.createElement('p');
    empty.textContent = 'No qualifying items were extracted.';
    container.appendChild(empty);
}
</script>
</body>
</html>
"""

    return template.replace("__ROOM_DATA__", data_json)


__all__ = ["build_mindmap_html", "normalise_item"]
