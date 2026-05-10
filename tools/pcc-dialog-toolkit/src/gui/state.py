from __future__ import annotations

from dataclasses import dataclass, field

from model import Conversation
from pcc import PccPackage
from tlk import TlkResolver


@dataclass
class AppState:
    """Shared mutable state across all GUI panels."""

    # ---- file configuration ----
    pcc_path: str | None = None
    game: str = "me2"
    tlk_path: str | None = None
    dlc_dir: str | None = None

    # ---- loaded data ----
    pcc_package: PccPackage | None = None
    conversations: list[Conversation] = field(default_factory=list)
    tlk_resolver: TlkResolver | None = None

    # ---- selection state ----
    selected_conversation_index: int | None = None
    selected_node_id: int | None = None
    selected_node_type: str | None = None  # "entry" or "reply"
    selected_export_index: int | None = None

    # ---- graph layout (populated by layout engine) ----
    graph_layout: dict[int, tuple[float, float]] = field(default_factory=dict)
    graph_view_offset: tuple[float, float] = (0.0, 0.0)
    graph_view_zoom: float = 1.0

    # ---- status ----
    status_message: str = "Ready"
    is_loading: bool = False
    error_message: str | None = None

    # ---- UI state ----
    conv_filter: str = ""
    tlk_search: str = ""
    show_about: bool = False
    pending_file_open: bool = False
    active_tab: int = 2  # 0=Package Editor, 1=TLK Editor, 2=Dialog Explorer

    @property
    def selected_conversation(self) -> Conversation | None:
        idx = self.selected_conversation_index
        if idx is not None and 0 <= idx < len(self.conversations):
            return self.conversations[idx]
        return None

    def clear_data(self) -> None:
        self.pcc_package = None
        self.conversations.clear()
        self.tlk_resolver = None
        self.selected_conversation_index = None
        self.selected_node_id = None
        self.selected_node_type = None
        self.selected_export_index = None
        self.graph_layout.clear()
