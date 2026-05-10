from __future__ import annotations

import igraph as ig

from model import Conversation

NodeKey = tuple[str, int]  # ("start", id), ("entry", id), or ("reply", id)


def layout_conversation(
    conv: Conversation,
    *,
    node_width: float = 240.0,
    node_height: float = 64.0,
    x_spacing: float = 80.0,
    y_spacing: float = 120.0,
) -> dict[NodeKey, tuple[float, float]]:
    """Compute (x, y) positions for start, entry, and reply nodes using igraph Sugiyama."""

    g = ig.Graph(directed=True)

    # Node order: starts, then entries, then replies
    start_count = len(conv.starts)
    entry_count = len(conv.entries)
    reply_count = len(conv.replies)
    total = start_count + entry_count + reply_count

    if total == 0:
        return {}

    g.add_vertices(total)

    # Add edges
    for s in conv.starts:
        if s.target_entry_id is not None:
            src = s.id
            dst = start_count + s.target_entry_id
            if 0 <= src < total and 0 <= dst < total:
                g.add_edge(src, dst)

    for e in conv.entries:
        src = start_count + e.id
        for rid in e.reply_links:
            dst = start_count + entry_count + rid
            if 0 <= src < total and 0 <= dst < total:
                g.add_edge(src, dst)

    for r in conv.replies:
        if r.target_entry_id is not None:
            src = start_count + entry_count + r.id
            dst = start_count + r.target_entry_id
            if 0 <= src < total and 0 <= dst < total:
                g.add_edge(src, dst)

    # Compute layout
    try:
        layout = g.layout_sugiyama()
    except Exception:
        layout = g.layout_reingold_tilford()

    # Map back to NodeKey positions
    positions: dict[NodeKey, tuple[float, float]] = {}

    # Normalize and scale
    xs = [p[0] for p in layout]
    ys = [p[1] for p in layout]
    if not xs or not ys:
        return {}

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    x_range = max_x - min_x or 1.0
    y_range = max_y - min_y or 1.0

    for i in range(start_count):
        x = (layout[i][0] - min_x) / x_range * x_spacing * max(1, (entry_count + reply_count) / 4)
        y = (layout[i][1] - min_y) / y_range * y_spacing * max(1, (entry_count + reply_count) / 4)
        x -= (max_x - min_x) / x_range * x_spacing * max(1, (entry_count + reply_count) / 4) / 2
        positions[("start", conv.starts[i].id)] = (x, y)

    for i, e in enumerate(conv.entries):
        idx = start_count + i
        x = (layout[idx][0] - min_x) / x_range * x_spacing * max(1, (entry_count + reply_count) / 4)
        y = (layout[idx][1] - min_y) / y_range * y_spacing * max(1, (entry_count + reply_count) / 4)
        x -= (max_x - min_x) / x_range * x_spacing * max(1, (entry_count + reply_count) / 4) / 2
        positions[("entry", e.id)] = (x, y)

    for i, r in enumerate(conv.replies):
        idx = start_count + entry_count + i
        x = (layout[idx][0] - min_x) / x_range * x_spacing * max(1, (entry_count + reply_count) / 4)
        y = (layout[idx][1] - min_y) / y_range * y_spacing * max(1, (entry_count + reply_count) / 4)
        x -= (max_x - min_x) / x_range * x_spacing * max(1, (entry_count + reply_count) / 4) / 2
        positions[("reply", r.id)] = (x, y)

    # Apply node dimensions spacing
    result: dict[NodeKey, tuple[float, float]] = {}
    for key, (x, y) in positions.items():
        result[key] = (x, y)  # positions are in canvas coordinates, spacing handled by caller

    return result
