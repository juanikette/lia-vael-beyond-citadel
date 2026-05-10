from __future__ import annotations

from pathlib import Path

from imgui_bundle import hello_imgui as hi
from imgui_bundle import imgui
from imgui_bundle import portable_file_dialogs as pfd

from pcc import PccFormatError, read_pcc
from pcc.reader import COMPRESSED_FLAG
from dialogue import parse_all_bioconversation_stubs_resilient
from tlk import build_tlk_resolver, resolve_conversations_tlk, TlkFormatError

from .state import AppState
from gui.graph import layout_conversation

GAMES = ("me1", "me2", "me3", "le1", "le2", "le3")


def _main_gui(state: AppState) -> None:
    _draw_main_menu(state)
    _status_bar(state)

    if state.show_about:
        _about_window(state)

    viewport = imgui.get_main_viewport()
    menu_h = 20.0
    status_h = 24.0
    avail_w = viewport.size.x
    avail_h = viewport.size.y - menu_h - status_h

    tabs_h = 30.0
    content_y = menu_h + tabs_h
    content_h = avail_h - tabs_h

    # Tab bar — directly in main viewport without a wrapper window
    imgui.set_next_window_pos(imgui.ImVec2(0, menu_h))
    imgui.set_next_window_size(imgui.ImVec2(avail_w, tabs_h))
    tb_flags = (
        imgui.WindowFlags_.no_title_bar
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_scrollbar
        | imgui.WindowFlags_.no_saved_settings
    )
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.begin("##tab_bar_window", False, tb_flags)

    tab_flags = imgui.TabBarFlags_.reorderable | imgui.TabBarFlags_.auto_select_new_tabs

    if imgui.begin_tab_bar("##main_tabs", tab_flags):
        pkg_opened = imgui.begin_tab_item("Package Editor")[0]
        if pkg_opened:
            state.active_tab = 0
            imgui.end_tab_item()

        tlk_opened = imgui.begin_tab_item("TLK Editor")[0]
        if tlk_opened:
            state.active_tab = 1
            imgui.end_tab_item()

        de_opened = imgui.begin_tab_item("Dialog Explorer")[0]
        if de_opened:
            state.active_tab = 2
            imgui.end_tab_item()

        imgui.end_tab_bar()
    imgui.end()
    imgui.pop_style_var(2)

    # Render content based on active tab
    if state.active_tab == 2:
        _dialog_explorer_tab(state, avail_w, content_h, content_y)
    else:
        _render_placeholder_center(content_y, content_h)


def _render_placeholder_center(y: float, h: float) -> None:
    vp = imgui.get_main_viewport()
    text = "Placeholder"
    size = imgui.calc_text_size(text)
    x = (vp.size.x - size.x) / 2
    cy = y + (h - size.y) / 2
    imgui.get_window_draw_list().add_text(
        imgui.ImVec2(x, cy),
        imgui.IM_COL32(120, 120, 130, 255),
        text,
    )


def _dialog_explorer_tab(state: AppState, avail_w: float, avail_h: float, y_off: float) -> None:
    left_w = avail_w / 4
    right_w = avail_w - left_w - 8
    panel_h = avail_h / 3

    imgui.set_next_window_size(imgui.ImVec2(left_w - 4, panel_h - 4), imgui.Cond_.once)
    imgui.set_next_window_pos(imgui.ImVec2(0, y_off), imgui.Cond_.once)
    _panel_file_loader(state)

    imgui.set_next_window_size(imgui.ImVec2(left_w - 4, panel_h - 4), imgui.Cond_.once)
    imgui.set_next_window_pos(imgui.ImVec2(0, y_off + panel_h), imgui.Cond_.once)
    _panel_detail(state)

    imgui.set_next_window_size(imgui.ImVec2(left_w - 4, panel_h - 4), imgui.Cond_.once)
    imgui.set_next_window_pos(imgui.ImVec2(0, y_off + panel_h * 2), imgui.Cond_.once)
    _panel_conversation_list(state)

    imgui.set_next_window_size(imgui.ImVec2(right_w, avail_h), imgui.Cond_.once)
    imgui.set_next_window_pos(imgui.ImVec2(left_w, y_off), imgui.Cond_.once)
    _panel_graph_view(state)


def _draw_main_menu(state: AppState) -> None:
    if imgui.begin_main_menu_bar():
        if imgui.begin_menu("File"):
            clicked, _ = imgui.menu_item("Open .pcc...", "Ctrl+O", False, True)
            if clicked:
                state.pending_file_open = True
            imgui.separator()
            clicked, _ = imgui.menu_item("Exit", "Alt+F4", False, True)
            if clicked:
                hi.get_runner_params().app_shall_exit = True
            imgui.end_menu()
        if imgui.begin_menu("View"):
            imgui.menu_item("File Loader", "", True, False)
            imgui.menu_item("Conversations", "", True, False)
            imgui.menu_item("Graph View", "", True, False)
            imgui.menu_item("Detail Panel", "", True, False)
            imgui.end_menu()
        if imgui.begin_menu("Help"):
            clicked, _ = imgui.menu_item("About", "", False, True)
            if clicked:
                state.show_about = True
            imgui.end_menu()
        imgui.end_main_menu_bar()

    if state.pending_file_open:
        state.pending_file_open = False
        dialog = pfd.open_file("Select .pcc file", str(Path.cwd()), ["PCC Files (*.pcc)"])
        if files := dialog.result():
            state.pcc_path = files[0]
            state.status_message = f"Selected: {files[0]}"


def _about_window(state: AppState) -> None:
    imgui.set_next_window_size(imgui.ImVec2(380, 210), imgui.Cond_.appearing)
    imgui.set_next_window_pos(
        imgui.ImVec2(imgui.get_main_viewport().size.x / 2 - 190, imgui.get_main_viewport().size.y / 2 - 105),
        imgui.Cond_.appearing,
    )
    flags = imgui.WindowFlags_.no_resize | imgui.WindowFlags_.no_docking
    imgui.begin("About PCC Dialog Viewer", True, flags)
    imgui.text("PCC Dialog Viewer")
    imgui.separator()
    imgui.text("Browse Mass Effect dialogue conversations from .pcc files.")
    imgui.spacing()
    imgui.text("Built with Dear ImGui via imgui-bundle.")
    imgui.text("Powered by pcc-dialog-toolkit.")
    imgui.spacing()
    imgui.text("Version: 0.2.0-gui-dev")
    imgui.spacing()
    if imgui.button("Close", imgui.ImVec2(120, 0)):
        state.show_about = False
    imgui.end()


def _status_bar(state: AppState) -> None:
    viewport = imgui.get_main_viewport()
    status_height = 24.0
    imgui.set_next_window_pos(
        imgui.ImVec2(viewport.pos.x, viewport.pos.y + viewport.size.y - status_height)
    )
    imgui.set_next_window_size(imgui.ImVec2(viewport.size.x, status_height))
    flags = (
        imgui.WindowFlags_.no_title_bar
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_scrollbar
        | imgui.WindowFlags_.no_saved_settings
    )
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(8, 4))
    imgui.begin("##statusbar", False, flags)
    if state.error_message:
        imgui.text_colored(imgui.ImVec4(1.0, 0.3, 0.3, 1.0), state.error_message)
    else:
        imgui.text(state.status_message)
    imgui.end()
    imgui.pop_style_var(2)


def _panel_file_loader(state: AppState) -> None:
    imgui.begin("File Loader", True)

    # --- PCC file picker ---
    imgui.text("PCC File:")
    imgui.same_line()
    pcc_label = Path(state.pcc_path).name if state.pcc_path else "(none)"
    imgui.text_disabled(pcc_label)
    imgui.same_line()
    if imgui.small_button("Browse..."):
        dialog = pfd.open_file("Select .pcc file", str(Path.cwd()), ["PCC Files (*.pcc)"])
        if files := dialog.result():
            state.pcc_path = files[0]
            state.status_message = f"Selected: {files[0]}"

    # --- Game ---
    imgui.spacing()
    imgui.text("Game:")
    imgui.same_line()
    current_idx = GAMES.index(state.game) if state.game in GAMES else 1
    changed, new_idx = imgui.combo("##game_combo", current_idx, GAMES)
    if changed:
        state.game = GAMES[new_idx]

    # --- TLK path ---
    imgui.spacing()
    imgui.text("TLK File:")
    imgui.same_line()
    tlk_label = Path(state.tlk_path).name if state.tlk_path else "(none)"
    imgui.text_disabled(tlk_label)
    imgui.same_line()
    if imgui.small_button("Browse##tlk"):
        dialog = pfd.open_file("Select TLK file", str(Path.cwd()), ["TLK Files (*.tlk)"])
        if files := dialog.result():
            state.tlk_path = files[0]

    # --- DLC dir ---
    imgui.text("DLC Dir:")
    imgui.same_line()
    dlc_label = Path(state.dlc_dir).name if state.dlc_dir else "(none)"
    imgui.text_disabled(dlc_label)
    imgui.same_line()
    if imgui.small_button("Browse##dlc"):
        dialog = pfd.select_folder("Select DLC directory", str(Path.cwd()))
        if folder := dialog.result():
            state.dlc_dir = folder

    # --- Load button ---
    imgui.spacing()
    imgui.separator()
    if state.is_loading:
        imgui.text("Loading...")
    elif imgui.button("Load PCC", imgui.ImVec2(-1, 0)):
        if state.pcc_path:
            _load_pcc(state)
        else:
            state.error_message = "Select a .pcc file first."

    # --- Package info ---
    if state.pcc_package is not None:
        imgui.spacing()
        imgui.separator()
        pkg = state.pcc_package
        bis = [e for e in pkg.exports if e.class_name == "BioConversation"]
        imgui.text(f"Exports: {len(pkg.exports)}")
        imgui.text(f"BioConversations: {len(bis)}")
        imgui.text(f"Names: {pkg.header.name_count}")
        imgui.text(f"Imports: {pkg.header.import_count}")
        profile = pkg.infer_game_profile()
        imgui.text(f"Profile: {profile}")
        if pkg.header.flags & COMPRESSED_FLAG:
            imgui.text_colored(imgui.ImVec4(1.0, 0.8, 0.2, 1.0), "Compressed")

    imgui.end()


def _load_pcc(state: AppState) -> None:
    state.error_message = None
    state.status_message = "Loading..."
    state.is_loading = True
    try:
        pkg = read_pcc(state.pcc_path)
        state.clear_data()
        state.pcc_package = pkg
        state.game = pkg.infer_game_profile()

        convs, parse_errors = parse_all_bioconversation_stubs_resilient(pkg)
        state.conversations = convs

        # --- TLK resolution ---
        tlk_resolved = 0
        if state.tlk_path:
            try:
                resolver = build_tlk_resolver(
                    base_tlk_path=state.tlk_path,
                    dlc_dir=state.dlc_dir,
                )
                state.tlk_resolver = resolver
                state.conversations = resolve_conversations_tlk(convs, resolver)
                tlk_resolved = sum(
                    1 for c in convs
                    for e in c.entries
                    if e.line_text is not None
                )
                tlk_resolved += sum(
                    1 for c in convs
                    for r in c.replies
                    if r.line_text is not None
                )
            except TlkFormatError as exc:
                state.status_message += f" (TLK error: {exc})"

        bioconv_count = len([e for e in pkg.exports if e.class_name == "BioConversation"])
        msg = (
            f"Loaded {Path(state.pcc_path).name}: "
            f"{len(pkg.exports)} exports, {bioconv_count} BioConversations, "
            f"{len(convs)} parsed"
        )
        if tlk_resolved:
            msg += f", {tlk_resolved} strings resolved"
        if parse_errors:
            msg += f", {len(parse_errors)} parse errors"
        state.status_message = msg
    except PccFormatError as exc:
        state.error_message = f"Parse error: {exc}"
    except OSError as exc:
        state.error_message = f"File error: {exc}"
    finally:
        state.is_loading = False


def _panel_conversation_list(state: AppState) -> None:
    imgui.begin("Conversations", True)

    if state.pcc_package is None:
        imgui.text_disabled("No file loaded.")
        imgui.end()
        return

    if state.is_loading:
        imgui.text("Parsing conversations...")
        imgui.end()
        return

    convs = state.conversations
    if not convs:
        imgui.text_disabled("No BioConversations found.")
        imgui.end()
        return

    # --- filter ---
    imgui.text(f"{len(convs)} conversations")
    _, state.conv_filter = imgui.input_text("##conv_filter", state.conv_filter, 64)
    filter_lower = state.conv_filter.strip().casefold()

    imgui.separator()

    # --- scrollable list ---
    list_height = imgui.get_content_region_avail().y - 40
    imgui.begin_child("##conv_list", imgui.ImVec2(0, list_height), True)

    for idx, conv in enumerate(convs):
        if filter_lower and not _conv_matches_filter(conv, filter_lower):
            continue

        label = conv.id or f"Export_{conv.export_index}"
        entry_count = len(conv.entries)
        reply_count = len(conv.replies)

        is_selected = state.selected_conversation_index == idx
        flags = imgui.TreeNodeFlags_.leaf
        if is_selected:
            flags |= imgui.TreeNodeFlags_.selected

        opened = imgui.tree_node_ex(f"{label}##{idx}", flags)
        if imgui.is_item_clicked():
            state.selected_conversation_index = idx
            state.selected_node_id = None
        if is_selected and imgui.is_item_activated():
            state.selected_conversation_index = idx
        if opened:
            imgui.tree_pop()

        # preview tooltip
        if imgui.is_item_hovered():
            imgui.begin_tooltip()
            imgui.text(f"ID: {conv.id}")
            imgui.text(f"Entries: {entry_count}  Replies: {reply_count}  Speakers: {len(conv.speakers)}")
            imgui.text(f"Parse mode: {conv.parse_mode}")
            if conv.warnings:
                imgui.text_colored(imgui.ImVec4(1.0, 0.8, 0.2, 1.0), f"Warnings: {len(conv.warnings)}")
            imgui.end_tooltip()

    imgui.end_child()

    # --- quick info below list ---
    imgui.separator()
    if state.selected_conversation_index is not None and 0 <= state.selected_conversation_index < len(convs):
        c = convs[state.selected_conversation_index]
        imgui.text(f"Selected: {c.id}")
        imgui.text(f"E:{len(c.entries)} R:{len(c.replies)} S:{len(c.speakers)}")

    imgui.end()


def _conv_matches_filter(conv, filter_lower: str) -> bool:
    if filter_lower in conv.id.casefold():
        return True
    for entry in conv.entries:
        if entry.speaker_tag and filter_lower in entry.speaker_tag.casefold():
            return True
        if entry.line_text and filter_lower in entry.line_text.casefold():
            return True
    for reply in conv.replies:
        if reply.line_text and filter_lower in reply.line_text.casefold():
            return True
    for speaker in conv.speakers:
        if speaker.tag and filter_lower in speaker.tag.casefold():
            return True
        if speaker.display_name and filter_lower in speaker.display_name.casefold():
            return True
    return False


def _panel_graph_view(state: AppState) -> None:
    flags = imgui.WindowFlags_.no_scrollbar | imgui.WindowFlags_.no_scroll_with_mouse
    imgui.begin("Graph View", True, flags)

    conv = state.selected_conversation
    if conv is None:
        imgui.text_disabled("Select a conversation to view its graph.")
        imgui.end()
        return

    # --- recompute layout when conversation changes ---
    conv_key = f"{conv.id}:{conv.export_index}"
    cached_key = state.graph_layout.pop("__conv_key__", None) if "__conv_key__" in state.graph_layout else None
    if conv_key != cached_key:
        state.graph_layout = layout_conversation(conv)
        state.graph_layout["__conv_key__"] = conv_key
        state.graph_view_offset = (0.0, 0.0)
        state.graph_view_zoom = 0.5

    # --- input handling ---
    io = imgui.get_io()
    canvas_p0 = imgui.get_cursor_screen_pos()
    canvas_size = imgui.get_content_region_avail()
    canvas_p1 = imgui.ImVec2(canvas_p0.x + canvas_size.x, canvas_p0.y + canvas_size.y)

    # dummy invisible item to make the child region interactive
    imgui.invisible_button("##graph_canvas", canvas_size)
    is_hovered = imgui.is_item_hovered()

    if is_hovered:
        # zoom with mouse wheel
        if io.mouse_wheel != 0:
            state.graph_view_zoom = max(0.15, min(3.0, state.graph_view_zoom + io.mouse_wheel * 0.1))
        # pan with right mouse drag
        if imgui.is_mouse_dragging(imgui.MouseButton_.right):
            delta = imgui.get_mouse_drag_delta(imgui.MouseButton_.right)
            state.graph_view_offset = (
                state.graph_view_offset[0] + delta.x / state.graph_view_zoom,
                state.graph_view_offset[1] + delta.y / state.graph_view_zoom,
            )
            imgui.reset_mouse_drag_delta(imgui.MouseButton_.right)

    # --- coordinate transforms ---
    cx = canvas_p0.x + canvas_size.x / 2
    cy = canvas_p0.y + canvas_size.y / 2
    ox, oy = state.graph_view_offset
    z = state.graph_view_zoom

    def to_screen(cx_val: float, cy_val: float) -> imgui.ImVec2:
        return imgui.ImVec2((cx_val + ox) * z + cx, (cy_val + oy) * z + cy)

    def to_canvas(sx: float, sy: float) -> tuple[float, float]:
        return ((sx - cx) / z - ox, (sy - cy) / z - oy)

    draw_list = imgui.get_window_draw_list()

    # clip
    draw_list.push_clip_rect(canvas_p0, canvas_p1)

    # --- grid ---
    grid_color = imgui.IM_COL32(50, 50, 55, 255)
    grid_spacing = 150.0
    grid_left, grid_top = to_canvas(canvas_p0.x, canvas_p0.y)
    grid_right, grid_bottom = to_canvas(canvas_p1.x, canvas_p1.y)
    x_start = (grid_left // grid_spacing) * grid_spacing
    y_start = (grid_top // grid_spacing) * grid_spacing
    x = x_start
    while x <= grid_right:
        p1 = to_screen(x, grid_top)
        p2 = to_screen(x, grid_bottom)
        draw_list.add_line(p1, p2, grid_color, 1.0)
        x += grid_spacing
    y = y_start
    while y <= grid_bottom:
        p1 = to_screen(grid_left, y)
        p2 = to_screen(grid_right, y)
        draw_list.add_line(p1, p2, grid_color, 1.0)
        y += grid_spacing

    # --- build node info map ---
    entry_map = {e.id: e for e in conv.entries}
    reply_map = {r.id: r for r in conv.replies}

    NODE_W = 240.0
    NODE_H = 64.0
    half_w = NODE_W / 2
    half_h = NODE_H / 2

    # --- draw edges (bezier curves with category colors) ---
    default_edge = imgui.IM_COL32(120, 120, 130, 200)
    category_colors = {
        "REPLY_CATEGORY_PARAGON_INTERRUPT": imgui.IM_COL32(60, 120, 255, 220),
        "REPLY_CATEGORY_RENEGADE_INTERRUPT": imgui.IM_COL32(255, 60, 60, 220),
        "REPLY_CATEGORY_AGREE": imgui.IM_COL32(60, 180, 255, 220),
        "REPLY_CATEGORY_DISAGREE": imgui.IM_COL32(255, 100, 70, 220),
        "REPLY_CATEGORY_FRIENDLY": imgui.IM_COL32(30, 30, 140, 220),
        "REPLY_CATEGORY_HOSTILE": imgui.IM_COL32(140, 30, 30, 220),
    }

    def _edge_color(reply):
        return category_colors.get(reply.category or "", default_edge)

    # Start → Entry edges
    start_fill = imgui.IM_COL32(40, 140, 60, 255)
    start_stroke = imgui.IM_COL32(80, 200, 120, 255)
    start_edge = imgui.IM_COL32(60, 160, 80, 220)
    for start in conv.starts:
        skey = ("start", start.id)
        if skey not in state.graph_layout:
            continue
        if start.target_entry_id is None:
            continue
        ekey = ("entry", start.target_entry_id)
        if ekey not in state.graph_layout:
            continue
        sx, sy = state.graph_layout[skey]
        ex, ey = state.graph_layout[ekey]
        _draw_bezier_edge(draw_list, to_screen, sx, sy + half_h, ex, ey - half_h, start_edge)

    # Entry → Reply edges
    for entry in conv.entries:
        ekey = ("entry", entry.id)
        if ekey not in state.graph_layout:
            continue
        ex, ey = state.graph_layout[ekey]
        for rid in entry.reply_links:
            rkey = ("reply", rid)
            if rkey not in state.graph_layout:
                continue
            reply = reply_map.get(rid)
            color = _edge_color(reply) if reply else default_edge
            rx, ry = state.graph_layout[rkey]
            _draw_bezier_edge(draw_list, to_screen, ex, ey + half_h, rx, ry - half_h, color)

    # Reply → Entry edges
    for reply in conv.replies:
        if reply.target_entry_id is None:
            continue
        rkey = ("reply", reply.id)
        ekey = ("entry", reply.target_entry_id)
        if rkey not in state.graph_layout or ekey not in state.graph_layout:
            continue
        rx, ry = state.graph_layout[rkey]
        ex, ey = state.graph_layout[ekey]
        color = _edge_color(reply)
        _draw_bezier_edge(draw_list, to_screen, rx, ry + half_h, ex, ey - half_h, color)

    # --- category color map for reply nodes ---
    reply_category_fills = {
        "REPLY_CATEGORY_PARAGON_INTERRUPT": imgui.IM_COL32(50, 80, 200, 255),
        "REPLY_CATEGORY_RENEGADE_INTERRUPT": imgui.IM_COL32(200, 50, 50, 255),
        "REPLY_CATEGORY_AGREE": imgui.IM_COL32(50, 120, 200, 255),
        "REPLY_CATEGORY_DISAGREE": imgui.IM_COL32(200, 80, 50, 255),
        "REPLY_CATEGORY_FRIENDLY": imgui.IM_COL32(20, 20, 100, 255),
        "REPLY_CATEGORY_HOSTILE": imgui.IM_COL32(100, 20, 20, 255),
    }

    # --- draw start nodes ---
    for start in conv.starts:
        skey = ("start", start.id)
        if skey not in state.graph_layout:
            continue
        nx, ny = state.graph_layout[skey]
        p_min = to_screen(nx - half_w, ny - half_h)
        p_max = to_screen(nx + half_w, ny + half_h)
        draw_list.add_rect_filled(p_min, p_max, start_fill, 6.0)
        draw_list.add_rect(p_min, p_max, start_stroke, 6.0, 0, 2.0)
        label = f"Start {start.id}" + (f" -> E{start.target_entry_id}" if start.target_entry_id is not None else "")
        _draw_node_text(draw_list, p_min, p_max, z, label, "", text_color)

    # --- draw nodes ---
    entry_fill = imgui.IM_COL32(40, 80, 140, 255)
    entry_fill_sel = imgui.IM_COL32(60, 120, 200, 255)
    reply_fill_default = imgui.IM_COL32(160, 100, 30, 255)
    reply_fill_sel = imgui.IM_COL32(220, 140, 40, 255)
    text_color = imgui.IM_COL32(255, 255, 255, 255)

    for is_entry in (True, False):
        items = conv.entries if is_entry else conv.replies
        for node in items:
            ntype = "entry" if is_entry else "reply"
            key = (ntype, node.id)
            if key not in state.graph_layout:
                continue
            nx, ny = state.graph_layout[key]
            p_min = to_screen(nx - half_w, ny - half_h)
            p_max = to_screen(nx + half_w, ny + half_h)

            sel = state.selected_node_id == node.id and state.selected_node_type == ntype
            if is_entry:
                fill = entry_fill_sel if sel else entry_fill
            else:
                default = reply_category_fills.get(node.category or "", reply_fill_default)
                fill = reply_fill_sel if sel else default

            draw_list.add_rect_filled(p_min, p_max, fill, 6.0)
            draw_list.add_rect(p_min, p_max, imgui.IM_COL32(200, 200, 210, 255), 6.0, 0, 1.5)

            if is_entry:
                speaker = node.speaker_tag or f"Entry {node.id}"
                line = _truncate(node.line_text, 50) if node.line_text else ""
                _draw_node_text(draw_list, p_min, p_max, z, speaker, line, text_color)
            else:
                line = _truncate(node.line_text, 50) if node.line_text else f"Reply {node.id}"
                _draw_node_text(draw_list, p_min, p_max, z, line, "", text_color)

    # --- click detection on nodes ---
    if is_hovered:
        for button in (imgui.MouseButton_.left,):
            if imgui.is_mouse_clicked(button) and not imgui.is_mouse_dragging(button, 3.0):
                mx, my = imgui.get_mouse_pos()
                cx_val, cy_val = to_canvas(mx, my)
                clicked = False
                for ntype, items in (("start", conv.starts), ("entry", conv.entries), ("reply", conv.replies)):
                    for node in items:
                        nid = node.id if hasattr(node, 'line_strref') else node.id
                        key = (ntype, nid)
                        if key not in state.graph_layout:
                            continue
                        nx, ny = state.graph_layout[key]
                        if abs(cx_val - nx) <= half_w and abs(cy_val - ny) <= half_h:
                            state.selected_node_id = nid
                            state.selected_node_type = ntype
                            clicked = True
                            break
                    if clicked:
                        break
                if not clicked:
                    state.selected_node_id = None
                    state.selected_node_type = None

    draw_list.pop_clip_rect()

    # --- legend ---
    imgui.set_cursor_screen_pos(imgui.ImVec2(canvas_p0.x + 8, canvas_p0.y + 8))
    imgui.begin_group()
    draw_legend = imgui.get_window_draw_list()
    draw_legend.add_rect_filled(
        imgui.get_cursor_screen_pos(),
        imgui.ImVec2(imgui.get_cursor_screen_pos().x + 14, imgui.get_cursor_screen_pos().y + 14),
        start_fill, 3.0,
    )
    imgui.same_line()
    imgui.dummy(imgui.ImVec2(20, 14))
    imgui.same_line()
    imgui.text("Start")
    imgui.same_line()
    imgui.dummy(imgui.ImVec2(16, 14))
    imgui.same_line()
    draw_legend.add_rect_filled(
        imgui.get_cursor_screen_pos(),
        imgui.ImVec2(imgui.get_cursor_screen_pos().x + 14, imgui.get_cursor_screen_pos().y + 14),
        entry_fill, 3.0,
    )
    imgui.same_line()
    imgui.dummy(imgui.ImVec2(20, 14))
    imgui.same_line()
    imgui.text("Entry")
    imgui.same_line()
    imgui.dummy(imgui.ImVec2(16, 14))
    imgui.same_line()
    draw_legend.add_rect_filled(
        imgui.get_cursor_screen_pos(),
        imgui.ImVec2(imgui.get_cursor_screen_pos().x + 14, imgui.get_cursor_screen_pos().y + 14),
        reply_fill_default, 3.0,
    )
    imgui.same_line()
    imgui.dummy(imgui.ImVec2(20, 14))
    imgui.same_line()
    imgui.text("Reply")
    imgui.end_group()

    imgui.end()


def _draw_node_text(
    dl: imgui.ImDrawList,
    p_min: imgui.ImVec2,
    p_max: imgui.ImVec2,
    zoom: float,
    primary: str,
    secondary: str,
    color: int,
) -> None:
    w = p_max.x - p_min.x

    if primary:
        size = imgui.calc_text_size(primary)
        tx = p_min.x + (w - size.x) / 2
        ty = p_min.y + 6 * zoom
        dl.add_text(imgui.ImVec2(tx, ty), color, primary)

    if secondary:
        sec_color = imgui.IM_COL32(200, 200, 210, 255)
        size = imgui.calc_text_size(secondary)
        tx = p_min.x + (w - size.x) / 2
        ty = p_max.y - size.y - 6 * zoom
        dl.add_text(imgui.ImVec2(tx, ty), sec_color, secondary)


def _draw_bezier_edge(
    dl: imgui.ImDrawList,
    to_screen,
    x1: float, y1: float,
    x2: float, y2: float,
    color: int,
) -> None:
    """Draw a cubic bezier edge between two points with LEX-style control points."""
    dx = abs(x2 - x1)
    ctrl = max(60.0, min(300.0, dx * 0.5))

    p1 = to_screen(x1, y1)
    p4 = to_screen(x2, y2)
    cp1 = to_screen(x1 + ctrl, y1)
    cp2 = to_screen(x2 - ctrl, y2)

    dl.add_bezier_cubic(p1, cp1, cp2, p4, color, 2.0)
    _draw_arrowhead(dl, cp2, p4, color, 8.0)


def _draw_arrowhead(
    dl: imgui.ImDrawList, p1: imgui.ImVec2, p2: imgui.ImVec2, color: int, size: float
) -> None:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1.0:
        return
    ux = dx / length
    uy = dy / length

    perp_x = -uy
    perp_y = ux

    tip_x = p2.x
    tip_y = p2.y

    back_x = tip_x - ux * size * 1.5
    back_y = tip_y - uy * size * 1.5

    left_x = back_x + perp_x * size * 0.6
    left_y = back_y + perp_y * size * 0.6
    right_x = back_x - perp_x * size * 0.6
    right_y = back_y - perp_y * size * 0.6

    dl.add_triangle_filled(
        imgui.ImVec2(tip_x, tip_y),
        imgui.ImVec2(left_x, left_y),
        imgui.ImVec2(right_x, right_y),
        color,
    )


def _panel_detail(state: AppState) -> None:
    imgui.begin("Detail", True)

    conv = state.selected_conversation
    if conv is None:
        imgui.text_disabled("No conversation selected.")
        imgui.end()
        return

    if state.selected_node_id is not None and state.selected_node_type is not None:
        _detail_selected_node(state, conv)
    else:
        _detail_conversation_overview(conv)

    imgui.end()


def _detail_conversation_overview(conv) -> None:
    imgui.text_colored(imgui.ImVec4(0.5, 0.8, 1.0, 1.0), conv.id or "(unnamed)")
    imgui.separator()
    imgui.text(f"Export index: {conv.export_index}")
    imgui.text(f"Parse mode: {conv.parse_mode}")
    imgui.text(f"Entries: {len(conv.entries)}")
    imgui.text(f"Replies: {len(conv.replies)}")
    imgui.text(f"Speakers: {len(conv.speakers)}")

    if conv.speakers:
        imgui.spacing()
        imgui.separator()
        imgui.text("Speakers:")
        for s in conv.speakers:
            tag = s.tag or f"Speaker_{s.id}"
            name = s.display_name or "-"
            imgui.bullet_text(f"[{s.id}] {tag}: {name}")

    if conv.warnings:
        imgui.spacing()
        imgui.separator()
        imgui.text_colored(imgui.ImVec4(1.0, 0.8, 0.2, 1.0), f"Warnings ({len(conv.warnings)}):")
        for w in conv.warnings:
            imgui.bullet_text(w)


def _detail_selected_node(state, conv) -> None:
    node_id = state.selected_node_id
    node_type = state.selected_node_type

    if node_type == "entry":
        node = next((e for e in conv.entries if e.id == node_id), None)
        if node is None:
            imgui.text_disabled(f"Entry {node_id} not found.")
            return
        imgui.text_colored(imgui.ImVec2(0.4, 0.7, 1.0, 1.0), f"Entry {node.id}")
        imgui.separator()

        _labeled("Speaker", node.speaker_tag or f"ID:{node.speaker_id}" if node.speaker_id is not None else "-")
        _labeled("Listener", node.listener_tag or "-")
        _labeled("StrRef", str(node.line_strref) if node.line_strref is not None else "-")

        if node.line_text:
            imgui.spacing()
            imgui.text("Text:")
            imgui.push_text_wrap_pos()
            imgui.text_wrapped(node.line_text)
            imgui.pop_text_wrap_pos()
        elif node.line_strref is not None:
            imgui.text_colored(imgui.ImVec4(1.0, 0.5, 0.3, 1.0), f"[Unresolved StrRef: {node.line_strref}]")

        imgui.spacing()
        imgui.separator()
        imgui.text(f"Reply links ({len(node.reply_links)}):")
        for rid in node.reply_links:
            reply = next((r for r in conv.replies if r.id == rid), None)
            preview = _truncate(reply.line_text, 40) if reply and reply.line_text else f"Reply {rid}"
            imgui.bullet_text(f"[{rid}] {preview}")

    else:
        node = next((r for r in conv.replies if r.id == node_id), None)
        if node is None:
            imgui.text_disabled(f"Reply {node_id} not found.")
            return
        imgui.text_colored(imgui.ImVec2(0.9, 0.6, 0.2, 1.0), f"Reply {node.id}")
        imgui.separator()

        _labeled("StrRef", str(node.line_strref) if node.line_strref is not None else "-")
        _labeled("Target Entry", str(node.target_entry_id) if node.target_entry_id is not None else "(terminal)")

        if node.line_text:
            imgui.spacing()
            imgui.text("Text:")
            imgui.push_text_wrap_pos()
            imgui.text_wrapped(node.line_text)
            imgui.pop_text_wrap_pos()
        elif node.line_strref is not None:
            imgui.text_colored(imgui.ImVec4(1.0, 0.5, 0.3, 1.0), f"[Unresolved StrRef: {node.line_strref}]")

        if node.condition_refs:
            imgui.spacing()
            imgui.separator()
            imgui.text(f"Conditions ({len(node.condition_refs)}):")
            for c in node.condition_refs:
                imgui.bullet_text(c)


def _labeled(label: str, value: str) -> None:
    imgui.columns(2, f"##{label}", False)
    imgui.text(label)
    imgui.next_column()
    imgui.text(value)
    imgui.columns(1)


def _truncate(text: str | None, max_len: int) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


def _build_runner_params(state: AppState) -> hi.RunnerParams:
    rp = hi.RunnerParams()

    rp.app_window_params.window_title = "PCC Dialog Viewer"
    rp.app_window_params.window_geometry.size = (1280, 800)
    rp.app_window_params.restore_previous_geometry = True

    rp.imgui_window_params.show_status_bar = False

    rp.callbacks.show_gui = lambda: _main_gui(state)

    return rp


def main() -> None:
    state = AppState()
    runner_params = _build_runner_params(state)
    hi.run(runner_params)


if __name__ == "__main__":
    main()
