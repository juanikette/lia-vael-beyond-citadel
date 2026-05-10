# PCC Dialog Viewer

Interactive GUI for browsing Mass Effect dialogue conversations extracted from `.pcc` package files.

Built with Python + [Dear ImGui](https://github.com/ocornut/imgui) via [imgui-bundle](https://github.com/pthom/imgui_bundle).

## Quickstart

```bash
# From tools/pcc-dialog-toolkit/
pip install -e ".[gui]"
pcc_dialog_viewer
```

## Panels

| Panel | Location | Purpose |
|---|---|---|
| **File Loader** | Top-left | Open `.pcc` / `.tlk` files, select game profile, load package |
| **Conversations** | Bottom-left | Filterable list of BioConversation exports; click to select |
| **Graph View** | Center | Interactive node graph of the selected conversation |
| **Detail** | Right | Full info for the selected entry/reply node, or conversation overview |

## Loading a file

1. Click **Browse...** next to _PCC File_ and select a `.pcc` file (ME2 OT or LE2).
2. Optionally set the **TLK File** and **DLC Dir** for StrRef text resolution (not yet wired to the viewer).
3. Click **Load PCC**. The package is parsed and all BioConversations are extracted.

## Navigating conversations

- Use the **Conversations** panel to browse all detected conversations.
- Type in the filter field to search by conversation name, speaker tag, or line text.
- Click a conversation to load its graph in the center panel.

## Graph view controls

| Action | Input |
|---|---|
| Zoom | Mouse wheel |
| Pan | Right-click + drag |
| Select node | Left-click |
| Deselect | Left-click empty space |

- **Blue nodes** = Entry nodes (speaker dialogue lines)
- **Orange nodes** = Reply nodes (player response choices)
- **Arrows** = Dialogue flow direction
- Hover over a conversation in the list to see entry/reply/speaker counts

## Detail panel

When a node is selected in the graph:

- **Entry node**: speaker tag, listener tag, StrRef, resolved text, linked replies
- **Reply node**: StrRef, target entry, resolved text, condition refs

When no node is selected, the panel shows conversation metadata and the speaker list.

## Supported games

- ME2 (original, verified)
- LE2 (Legendary Edition, supported via PCC reader)
- ME1/ME3/LE1/LE3 (selectable, may have limited coverage)

## Requirements

- Python 3.11+
- `imgui-bundle >= 1.90`
- `lzallright >= 0.2.6` (LZO decompression for ME2 OT)

## Entry points

| Command | Purpose |
|---|---|
| `pcc_dialog_viewer` | Launch the GUI |
| `pcc_dialog_extract` | CLI extraction tool (separate) |
