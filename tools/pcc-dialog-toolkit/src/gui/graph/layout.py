from __future__ import annotations

from collections import defaultdict

from model import Conversation

NodeKey = tuple[str, int]  # ("entry", id) or ("reply", id)


def layout_conversation(
    conv: Conversation,
    *,
    node_width: float = 200.0,
    node_height: float = 60.0,
    x_spacing: float = 60.0,
    y_spacing: float = 100.0,
) -> dict[NodeKey, tuple[float, float]]:
    """Compute (x, y) positions for every entry and reply node.

    Uses a simplified Sugiyama-style layered layout:
    1. Assign layers via BFS from root entries.
    2. Reorder nodes within layers (barycenter) to reduce crossings.
    3. Place nodes with uniform spacing.
    """

    entry_ids = {e.id for e in conv.entries}
    reply_ids = {r.id for r in conv.replies}

    # --- adjacency ---
    entry_to_replies: dict[int, list[int]] = {}
    reply_to_entry: dict[int, int | None] = {}
    reply_in_degree: dict[int, int] = defaultdict(int)

    for e in conv.entries:
        entry_to_replies[e.id] = list(e.reply_links)
        for rid in e.reply_links:
            reply_in_degree[rid] += 1

    for r in conv.replies:
        reply_to_entry[r.id] = r.target_entry_id

    # --- root entries (no incoming reply edges) ---
    entry_in_degree: dict[int, int] = defaultdict(int)
    for r in conv.replies:
        if r.target_entry_id is not None:
            entry_in_degree[r.target_entry_id] += 1

    root_entries = [eid for eid in entry_ids if entry_in_degree.get(eid, 0) == 0]

    # --- BFS layer assignment ---
    layer: dict[NodeKey, int] = {}
    layer_queues: dict[int, list[NodeKey]] = defaultdict(list)

    for eid in root_entries:
        key: NodeKey = ("entry", eid)
        layer[key] = 0
        layer_queues[0].append(key)

    queue = list(root_entries)  # entry IDs to process
    visited_entries = set(root_entries)

    while queue:
        eid = queue.pop(0)
        current_layer = layer.get(("entry", eid), 0)
        next_layer = current_layer + 1

        for rid in entry_to_replies.get(eid, []):
            rkey: NodeKey = ("reply", rid)
            if rkey not in layer:
                layer[rkey] = next_layer
                layer_queues[next_layer].append(rkey)

            target_eid = reply_to_entry.get(rid)
            if target_eid is not None and target_eid in entry_ids and target_eid not in visited_entries:
                visited_entries.add(target_eid)
                ekey: NodeKey = ("entry", target_eid)
                tgt_layer = next_layer + 1
                layer[ekey] = tgt_layer
                layer_queues[tgt_layer].append(ekey)
                queue.append(target_eid)

    # --- handle unreachable nodes ---
    max_layer = max(layer.values()) if layer else 0
    for eid in entry_ids:
        key = ("entry", eid)
        if key not in layer:
            max_layer += 1
            layer[key] = max_layer
            layer_queues[max_layer].append(key)
    for rid in reply_ids:
        key = ("reply", rid)
        if key not in layer:
            max_layer += 1
            layer[key] = max_layer
            layer_queues[max_layer].append(key)

    # --- barycenter reordering within layers ---
    sorted_layers = sorted(layer_queues.keys())
    for _ in range(3):  # few iterations are enough
        for li in range(1, len(sorted_layers)):
            l = sorted_layers[li]
            nodes = list(layer_queues[l])

            def barycenter(key: NodeKey) -> float:
                ntype, nid = key
                neighbors: list[NodeKey] = []
                if ntype == "entry":
                    for r in conv.replies:
                        if r.target_entry_id == nid:
                            neighbors.append(("reply", r.id))
                else:
                    for e in conv.entries:
                        if nid in e.reply_links:
                            neighbors.append(("entry", e.id))

                positions = [layer.get(n, -1) for n in neighbors if n in layer]
                if not positions:
                    return float("inf")
                return sum(positions) / len(positions)

            nodes.sort(key=barycenter)
            layer_queues[l] = nodes

    # --- assign coordinates ---
    positions: dict[NodeKey, tuple[float, float]] = {}
    for l in sorted_layers:
        nodes = layer_queues[l]
        total_w = len(nodes) * (node_width + x_spacing) - x_spacing
        start_x = -total_w / 2.0
        for i, key in enumerate(nodes):
            x = start_x + i * (node_width + x_spacing)
            y = l * (node_height + y_spacing)
            positions[key] = (x, y)

    return positions
