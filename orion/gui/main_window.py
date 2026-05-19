from __future__ import annotations

import sys
import time
import requests

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt, QSize, Signal, QObject, QThread, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from orion.integrations.api_client import API_URL, get_apps
from orion.core.assistant import OrionAssistant
from orion.core.brain import detectar_hotword
import orion.config as config


ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"


def icon_path(name: str) -> str:
    return str(ICON_DIR / name)


def svg_pixmap(name: str, w: int, h: int) -> QPixmap:
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.transparent)

    renderer = QSvgRenderer(icon_path(name))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap


APP_STYLE = """
QMainWindow {
    background: #070b14;
    color: #f8fafc;
    font-family: "Segoe UI";
    font-size: 14px;
}

QWidget {
    color: #f8fafc;
    font-family: "Segoe UI";
    font-size: 14px;
    background: transparent;
}

QLabel {
    background: transparent;
    border: none;
}

QFrame#TopHeader {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #0b1220,
        stop:1 #0d1526
    );
    border: 1px solid #1a2740;
    border-radius: 0px;
}

QFrame#Sidebar {
    background: #08101d;
    border: 1px solid #16233a;
    border-radius: 18px;
}

QFrame#BrandCard {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #0d1730,
        stop:1 #0a1222
    );
    border: 1px solid #1f3050;
    border-radius: 16px;
}

QLabel#BrandTitle {
    font-size: 30px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 1px;
}

QLabel#BrandSubtitle {
    font-size: 13px;
    color: #b8c2d1;
}

QFrame#StatusMiniCard {
    background: #0b1424;
    border: 1px solid #1b2b47;
    border-radius: 16px;
}

QLabel#MiniCardTitle {
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#MiniCardText {
    font-size: 12px;
    color: #9fb0c8;
}

QPushButton#NavButton {
    background: #111b2f;
    color: #e6edf7;
    border: 1px solid #213250;
    border-radius: 16px;
    text-align: left;
    padding: 14px 18px;
    padding-left: 16px;
    font-size: 15px;
    font-weight: 600;
}

QPushButton#NavButton:hover {
    background: #162540;
    border: 1px solid #2f81f7;
}

QPushButton#NavButton:checked {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #173763,
        stop:1 #0f2747
    );
    border: 1px solid #2f81f7;
    color: #ffffff;
}

QFrame#StatusPill {
    background: #0d1628;
    border: 1px solid #243553;
    border-radius: 14px;
}

QLabel#PageTitle {
    font-size: 18px;
    font-weight: 800;
    color: #ffffff;
    background: transparent;
}

QLabel#MutedText {
    color: #8b9bb4;
    font-size: 12px;
    background: transparent;
}

QLabel#SectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
}

QFrame#Card {
    background: #0d1526;
    border: 1px solid #1b2a44;
    border-radius: 22px;
}

QLineEdit {
    background: #09111f;
    border: 1px solid #2f81f7;
    border-radius: 14px;
    padding: 14px 16px;
    color: #f8fafc;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid #58a6ff;
}

QPushButton#SendButton {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1f6feb,
        stop:1 #173763
    );
    border: 1px solid #2f81f7;
    border-radius: 14px;
    padding: 12px 28px;
    color: white;
    font-weight: 800;
    min-width: 110px;
}

QPushButton#SendButton:hover {
    background: #2f81f7;
}

QPushButton#MicButton {
    background: #121d31;
    border: 1px solid #263a5c;
    border-radius: 32px;
    min-width: 64px;
    max-width: 64px;
    min-height: 64px;
    max-height: 64px;
    color: #f8fafc;
    font-size: 22px;
    font-weight: 700;
}

QPushButton#MicButton:hover {
    border: 1px solid #2f81f7;
    background: #172742;
}

QScrollArea {
    border: none;
    background: transparent;
}

QFrame#CommandsCard {
    background: #0c1424;
    border: 1px solid #1b2a44;
    border-radius: 24px;
}

QFrame#CommandsHeader {
    background: transparent;
    border: none;
}

QLabel#CommandsTitle {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    background: transparent;
}

QLabel#CommandsSubtitle {
    font-size: 13px;
    color: #9fb0c8;
    background: transparent;
}

QFrame#ChatViewport {
    background: #09111d;
    border: 1px solid #16243b;
    border-radius: 20px;
}

QWidget#ChatContainer {
    background: transparent;
}

QFrame#BubbleUser {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1f6feb,
        stop:1 #173763
    );
    border: 1px solid #2f81f7;
    border-radius: 18px;
}

QFrame#BubbleAssistant {
    background: #101a2d;
    border: 1px solid #213250;
    border-radius: 18px;
}

QFrame#BubbleSystem {
    background: #102019;
    border: 1px solid #1f4d3c;
    border-radius: 18px;
}

QFrame#BubbleError {
    background: #24131a;
    border: 1px solid #6e2b3a;
    border-radius: 18px;
}

QLabel#BubbleSender {
    font-size: 12px;
    font-weight: 700;
    color: #dbe7f5;
    background: transparent;
}

QLabel#BubbleText {
    font-size: 15px;
    color: #f8fafc;
    line-height: 1.35em;
    background: transparent;
}

QPushButton#QuickActionButton {
    background: #111b2f;
    border: 1px solid #213250;
    border-radius: 14px;
    text-align: left;
    padding: 0px;
}

QPushButton#QuickActionButton:hover {
    background: #162540;
    border: 1px solid #2f81f7;
}

QLabel#QuickActionText {
    color: #f8fafc;
    font-size: 14px;
    font-weight: 600;
    background: transparent;
}

QFrame#InfoListItem {
    background: transparent;
    border: none;
}

QLabel#InfoListText {
    color: #d8e1ee;
    font-size: 13px;
    background: transparent;
}

QFrame#ActivityToolbar {
    background: transparent;
    border: none;
}

QTableWidget#ActivityTable {
    background: #09111d;
    border: 1px solid #16243b;
    border-radius: 16px;
    gridline-color: #16243b;
    color: #f8fafc;
    selection-background-color: #173763;
    selection-color: #ffffff;
}

QHeaderView::section {
    background: #111b2f;
    color: #f8fafc;
    padding: 10px;
    border: none;
    border-bottom: 1px solid #213250;
    font-weight: 700;
}

QTableWidget#ActivityTable::item {
    padding: 8px;
    border-bottom: 1px solid #132038;
}

QPushButton#SecondaryButton {
    background: #111b2f;
    border: 1px solid #213250;
    border-radius: 12px;
    padding: 10px 16px;
    color: #f8fafc;
    font-weight: 600;
}

QPushButton#SecondaryButton:hover {
    background: #162540;
    border: 1px solid #2f81f7;
}

QFrame#AppsToolbar {
    background: transparent;
    border: none;
}

QTableWidget#AppsTable {
    background: #09111d;
    border: 1px solid #16243b;
    border-radius: 16px;
    gridline-color: #16243b;
    color: #f8fafc;
    selection-background-color: #173763;
    selection-color: #ffffff;
}

QTableWidget#AppsTable::item {
    padding: 8px;
    border-bottom: 1px solid #132038;
}
"""


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"


@dataclass
class ChatMessage:
    author: str
    text: str
    type: MessageType


class StatusPill(QFrame):
    def __init__(self, label: str, value: str, color: str, icon_file: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self.label_name = label

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setFixedSize(16, 16)
        icon_label.setPixmap(svg_pixmap(icon_file, 16, 16))

        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px;")

        self.text = QLabel(f"{label}: {value}")
        self.text.setStyleSheet("color: #f8fafc; font-weight: 700; background: transparent;")

        layout.addWidget(icon_label)
        layout.addWidget(self.dot)
        layout.addWidget(self.text)

    def set_status(self, value: str, color: str) -> None:
        self.dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self.text.setText(f"{self.label_name}: {value}")


class TopHeader(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopHeader")
        self.setFixedHeight(82)

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(14)

        left_wrap = QWidget()
        left_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left_wrap.setStyleSheet("background: transparent;")
        left_box = QVBoxLayout(left_wrap)
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(2)

        self.page_title = QLabel("Centro de comandos")
        self.page_title.setObjectName("PageTitle")

        self.page_subtitle = QLabel("Envía instrucciones por texto o activa el micrófono para hablar con ORION.")
        self.page_subtitle.setObjectName("MutedText")

        left_box.addWidget(self.page_title)
        left_box.addWidget(self.page_subtitle)
        root.addWidget(left_wrap, 1)

        pills_wrap = QWidget()
        pills_wrap.setStyleSheet("background: transparent;")
        pills_layout = QHBoxLayout(pills_wrap)
        pills_layout.setContentsMargins(0, 0, 0, 0)
        pills_layout.setSpacing(10)

        self.mic_pill = StatusPill("Mic", "Detenido", "#ff7b72", "mic.svg")
        self.api_pill = StatusPill("API", "Desconocida", "#f2cc60", "shield.svg")
        self.db_pill = StatusPill("DB", "Desconocida", "#f2cc60", "database.svg")
        self.mode_pill = StatusPill("Modo", "Híbrido", "#58a6ff", "orion.svg")

        pills_layout.addWidget(self.mic_pill)
        pills_layout.addWidget(self.api_pill)
        pills_layout.addWidget(self.db_pill)
        pills_layout.addWidget(self.mode_pill)

        root.addWidget(pills_wrap, 0, Qt.AlignRight)

    def set_mic_status(self, value: str, color: str) -> None:
        self.mic_pill.set_status(value, color)

    def set_api_status(self, value: str, color: str) -> None:
        self.api_pill.set_status(value, color)

    def set_db_status(self, value: str, color: str) -> None:
        self.db_pill.set_status(value, color)

    def set_mode_status(self, value: str, color: str) -> None:
        self.mode_pill.set_status(value, color)


class NavButton(QPushButton):
    def __init__(self, label: str, icon_file: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(56)
        self.setText(f"   {label}")
        self.setIcon(QIcon(icon_path(icon_file)))
        self.setIconSize(QSize(20, 20))


class LeftSidebar(QFrame):
    page_selected = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(235)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)

        brand_card = QFrame()
        brand_card.setObjectName("BrandCard")
        brand_layout = QVBoxLayout(brand_card)
        brand_layout.setContentsMargins(16, 16, 16, 16)
        brand_layout.setSpacing(4)

        title = QLabel("ORION")
        title.setObjectName("BrandTitle")

        subtitle = QLabel("Asistente inteligente de escritorio")
        subtitle.setObjectName("BrandSubtitle")
        subtitle.setWordWrap(True)

        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        root.addWidget(brand_card)

        self.buttons: list[NavButton] = []
        items = [
            ("Dashboard", "dashboard.svg"),
            ("Comandos", "mic.svg"),
            ("Actividad", "activity.svg"),
            ("Aplicaciones", "apps.svg"),
            ("Dispositivos", "devices.svg"),
        ]

        for index, (label, icon_file) in enumerate(items):
            btn = NavButton(label, icon_file)
            btn.clicked.connect(lambda checked=False, i=index: self.select_page(i))
            root.addWidget(btn)
            self.buttons.append(btn)

        self.buttons[1].setChecked(True)

        root.addStretch(1)

        status_card = QFrame()
        status_card.setObjectName("StatusMiniCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(14, 14, 14, 14)
        status_layout.setSpacing(6)

        status_title = QLabel("Estado del motor")
        status_title.setObjectName("MiniCardTitle")

        status_text = QLabel("GUI conectada a FastAPI y MariaDB.")
        status_text.setObjectName("MiniCardText")
        status_text.setWordWrap(True)

        status_layout.addWidget(status_title)
        status_layout.addWidget(status_text)
        root.addWidget(status_card)

    def select_page(self, index: int) -> None:
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)
        self.page_selected.emit(index)


class MessageBubble(QFrame):
    def __init__(self, message: ChatMessage, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        if message.type == MessageType.USER:
            self.setObjectName("BubbleUser")
            icon_file = "mic.svg"
        elif message.type == MessageType.ASSISTANT:
            self.setObjectName("BubbleAssistant")
            icon_file = "orion.svg"
        elif message.type == MessageType.SYSTEM:
            self.setObjectName("BubbleSystem")
            icon_file = "shield.svg"
        else:
            self.setObjectName("BubbleError")
            icon_file = "shield.svg"

        self.setMaximumWidth(760)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        icon_label = QLabel()
        icon_label.setFixedSize(18, 18)
        icon_label.setPixmap(svg_pixmap(icon_file, 18, 18))

        sender = QLabel(message.author)
        sender.setObjectName("BubbleSender")

        top_row.addWidget(icon_label)
        top_row.addWidget(sender)

        body = QLabel(message.text)
        body.setObjectName("BubbleText")
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)

        root.addLayout(top_row)
        root.addWidget(body)


class ChatPanel(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ChatViewport")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.container.setObjectName("ChatContainer")

        self.layout_messages = QVBoxLayout(self.container)
        self.layout_messages.setContentsMargins(10, 10, 10, 10)
        self.layout_messages.setSpacing(14)
        self.layout_messages.addStretch(1)

        self.scroll.setWidget(self.container)
        outer.addWidget(self.scroll)

    def add_message(self, message: ChatMessage) -> None:
        bubble = MessageBubble(message)

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        if message.type == MessageType.USER:
            wrapper_layout.addStretch(1)
            wrapper_layout.addWidget(bubble, 0, Qt.AlignRight)
        else:
            wrapper_layout.addWidget(bubble, 0, Qt.AlignLeft)
            wrapper_layout.addStretch(1)

        self.layout_messages.insertWidget(self.layout_messages.count() - 1, wrapper)

        QApplication.processEvents()
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())


class InputArea(QFrame):
    send_requested = Signal(str)
    mic_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("InputBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Escribe un comando para ORION...")
        self.input.returnPressed.connect(self._emit_send)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._emit_send)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.clicked.connect(self.mic_requested.emit)
        self.mic_btn.setToolTip("Activar escucha continua")

        layout.addWidget(self.input, 1)
        layout.addWidget(self.send_btn)
        layout.addWidget(self.mic_btn)

    def _emit_send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.send_requested.emit(text)
        self.input.clear()

    def set_listening(self, active: bool) -> None:
        if active:
            self.mic_btn.setText("■")
            self.mic_btn.setToolTip("Detener escucha continua")
        else:
            self.mic_btn.setText("🎤")
            self.mic_btn.setToolTip("Activar escucha continua")


class CommandsPage(QWidget):
    send_requested = Signal(str)
    mic_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        card = QFrame()
        card.setObjectName("CommandsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("CommandsHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("Conversación")
        title.setObjectName("CommandsTitle")

        subtitle = QLabel("Escribe o habla con ORION para ejecutar acciones y obtener respuestas.")
        subtitle.setObjectName("CommandsSubtitle")
        subtitle.setWordWrap(True)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        self.chat_panel = ChatPanel()
        self.input_area = InputArea()

        self.input_area.send_requested.connect(self.send_requested.emit)
        self.input_area.mic_requested.connect(self.mic_requested.emit)

        card_layout.addWidget(header)
        card_layout.addWidget(self.chat_panel, 1)
        card_layout.addWidget(self.input_area)

        root.addWidget(card, 1)

        self.chat_panel.add_message(
            ChatMessage("Sistema", "GUI conectada a FastAPI y MariaDB. Puedes escribir comandos o activar escucha continua.", MessageType.SYSTEM)
        )


class PlaceholderPage(QFrame):
    def __init__(self, title_text: str, description: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        title = QLabel(title_text)
        title.setObjectName("SectionTitle")

        text = QLabel(description)
        text.setWordWrap(True)
        text.setObjectName("MutedText")

        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch(1)


class IconActionButton(QPushButton):
    def __init__(self, label: str, icon_file: str, command_text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.command_text = command_text
        self.setObjectName("QuickActionButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(18, 18)
        icon_label.setPixmap(svg_pixmap(icon_file, 18, 18))

        text_label = QLabel(label)
        text_label.setObjectName("QuickActionText")

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch(1)


class InfoListItem(QFrame):
    def __init__(self, text: str, color: str = "#58a6ff", icon_file: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("InfoListItem")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        if icon_file:
            icon_label = QLabel()
            icon_label.setFixedSize(14, 14)
            icon_label.setPixmap(svg_pixmap(icon_file, 14, 14))
            layout.addWidget(icon_label)
        else:
            dot = QLabel("•")
            dot.setStyleSheet(f"color: {color}; font-size: 16px; background: transparent;")
            layout.addWidget(dot)

        text_label = QLabel(text)
        text_label.setObjectName("InfoListText")

        layout.addWidget(text_label)
        layout.addStretch(1)


class RightPanel(QFrame):
    action_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(290)
        self.setStyleSheet("background: transparent;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        quick_card = QFrame()
        quick_card.setObjectName("Card")
        quick_layout = QVBoxLayout(quick_card)
        quick_layout.setContentsMargins(14, 14, 14, 14)
        quick_layout.setSpacing(10)

        quick_title = QLabel("Acciones rápidas")
        quick_title.setObjectName("SectionTitle")
        quick_layout.addWidget(quick_title)

        actions = [
            ("Abrir Chrome", "chrome.svg", "abre chrome"),
            ("Discord", "discord.svg", "abre discord"),
            ("Spotify", "spotify.svg", "abre spotify"),
            ("Captura", "camera.svg", "toma una captura"),
            ("Buscar", "search.svg", "busca inteligencia artificial"),
            ("Silenciar", "volume.svg", "silencia el volumen"),
        ]

        for label, icon_file, command_text in actions:
            btn = IconActionButton(label, icon_file, command_text)
            btn.clicked.connect(lambda checked=False, cmd=command_text: self.action_requested.emit(cmd))
            quick_layout.addWidget(btn)

        root.addWidget(quick_card)

        activity_card = QFrame()
        activity_card.setObjectName("Card")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(14, 14, 14, 14)
        activity_layout.setSpacing(8)

        activity_title = QLabel("Actividad reciente")
        activity_title.setObjectName("SectionTitle")
        activity_layout.addWidget(activity_title)

        activity_layout.addWidget(InfoListItem("Se sincroniza desde command_history", "#58a6ff", "activity.svg"))
        activity_layout.addWidget(InfoListItem("Comandos y eventos por API", "#58a6ff", "shield.svg"))
        activity_layout.addWidget(InfoListItem("Persistencia en MariaDB", "#7ee787", "database.svg"))

        root.addWidget(activity_card)

        devices_card = QFrame()
        devices_card.setObjectName("Card")
        devices_layout = QVBoxLayout(devices_card)
        devices_layout.setContentsMargins(14, 14, 14, 14)
        devices_layout.setSpacing(8)

        devices_title = QLabel("Dispositivos")
        devices_title.setObjectName("SectionTitle")
        devices_layout.addWidget(devices_title)

        devices_layout.addWidget(InfoListItem("Micrófono: activo", "#7ee787", "mic.svg"))
        devices_layout.addWidget(InfoListItem("Altavoz: listo", "#7ee787", "volume.svg"))
        devices_layout.addWidget(InfoListItem("Raspberry Pi: pendiente", "#f2cc60", "devices.svg"))

        root.addWidget(devices_card)
        root.addStretch(1)


class VoiceWorker(QObject):
    status_signal = Signal(str, str)
    heard_signal = Signal(str)
    response_signal = Signal(str, bool)
    error_signal = Signal(str)
    finished = Signal()

    def __init__(self, assistant: OrionAssistant) -> None:
        super().__init__()
        self.assistant = assistant
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            self.status_signal.emit("Escuchando hotword", "#f2cc60")

            while self._running:
                hot = self.assistant.context.listener.escuchar_con_gramatica(
                    config.HOTWORD_OPTIONS,
                    segundos_max=config.LISTENER_HOTWORD_SECONDS,
                )

                if not self._running:
                    break

                if not hot:
                    continue

                if not detectar_hotword(hot):
                    continue

                self.heard_signal.emit(f"[Hotword] {hot}")
                self.status_signal.emit("Hotword detectada", "#7ee787")

                try:
                    self.assistant.context.speaker.decir("¿Qué necesitas?")
                except Exception:
                    pass

                if not self._running:
                    break

                self.status_signal.emit("Escuchando comando", "#58a6ff")

                comando = self.assistant.context.listener.escuchar_hasta_texto(
                    intentos=config.LISTENER_COMMAND_ATTEMPTS,
                    segundos_por_intento=config.LISTENER_COMMAND_SECONDS,
                )

                if not self._running:
                    break

                if not comando:
                    self.response_signal.emit("No escuché el comando.", False)
                    self.status_signal.emit("Escuchando hotword", "#f2cc60")
                    continue

                self.heard_signal.emit(comando)
                self.status_signal.emit("Procesando", "#d2a8ff")

                result = self.assistant.process_text(comando, speak=True)
                self.response_signal.emit(result.message, result.success)

                if result.action == "EXIT":
                    self._running = False
                    break

                self.status_signal.emit("Escuchando hotword", "#f2cc60")
                time.sleep(0.15)

        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.finished.emit()


class ActivityPage(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Actividad")
        title.setObjectName("CommandsTitle")

        subtitle = QLabel("Historial real de comandos y acciones registradas en MariaDB.")
        subtitle.setObjectName("CommandsSubtitle")
        subtitle.setWordWrap(True)

        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QFrame()
        toolbar.setObjectName("ActivityToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar por texto, intent o payload...")
        self.search_input.textChanged.connect(self.apply_filter)

        self.refresh_btn = QPushButton("Recargar")
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.clicked.connect(self.load_activity)

        toolbar_layout.addWidget(self.search_input, 1)
        toolbar_layout.addWidget(self.refresh_btn)
        root.addWidget(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("ActivityTable")
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Raw text", "Intent", "Payload", "Status", "Respuesta"]
        )
        self.table.setAlternatingRowColors(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

        root.addWidget(self.table, 1)

        self.all_rows: list[dict] = []
        self.load_activity()

    def load_activity(self) -> None:
        self.all_rows.clear()

        try:
            response = requests.get(f"{API_URL}/commands/recent?limit=200", timeout=3)
            response.raise_for_status()
            rows = response.json()

            self.all_rows = [
                {
                    "created_at": str(row.get("created_at", "")),
                    "raw_text": str(row.get("raw_text", "")),
                    "intent": str(row.get("intent", "")),
                    "payload": str(row.get("payload", "")),
                    "status": str(row.get("status", "")),
                    "response_message": str(row.get("response_message", "")),
                }
                for row in rows
            ]

        except Exception as e:
            self.all_rows = [{
                "created_at": "-",
                "raw_text": "No se pudo leer la actividad",
                "intent": "ERROR",
                "payload": "",
                "status": "error",
                "response_message": str(e),
            }]

        self.populate_table(self.all_rows)

    def populate_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row["created_at"]))
            self.table.setItem(r, 1, QTableWidgetItem(row["raw_text"]))
            self.table.setItem(r, 2, QTableWidgetItem(row["intent"]))
            self.table.setItem(r, 3, QTableWidgetItem(row["payload"]))
            self.table.setItem(r, 4, QTableWidgetItem(row["status"]))
            self.table.setItem(r, 5, QTableWidgetItem(row["response_message"]))

        self.table.resizeRowsToContents()

    def apply_filter(self) -> None:
        text = self.search_input.text().strip().lower()

        if not text:
            self.populate_table(self.all_rows)
            return

        filtered = []
        for row in self.all_rows:
            haystack = " ".join([
                row["created_at"],
                row["raw_text"],
                row["intent"],
                row["payload"],
                row["status"],
                row["response_message"],
            ]).lower()
            if text in haystack:
                filtered.append(row)

        self.populate_table(filtered)


class AppsPage(QFrame):
    action_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Aplicaciones")
        title.setObjectName("CommandsTitle")

        subtitle = QLabel("Listado real de aplicaciones registradas en MariaDB y sus aliases.")
        subtitle.setObjectName("CommandsSubtitle")
        subtitle.setWordWrap(True)

        root.addWidget(title)
        root.addWidget(subtitle)

        toolbar = QFrame()
        toolbar.setObjectName("AppsToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, alias o ruta...")
        self.search_input.textChanged.connect(self.apply_filter)

        self.refresh_btn = QPushButton("Recargar")
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.clicked.connect(self.load_apps)

        self.open_btn = QPushButton("Abrir seleccionada")
        self.open_btn.setObjectName("SecondaryButton")
        self.open_btn.clicked.connect(self.open_selected_app)

        toolbar_layout.addWidget(self.search_input, 1)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.open_btn)
        root.addWidget(toolbar)

        self.table = QTableWidget(0, 3)
        self.table.setObjectName("AppsTable")
        self.table.setHorizontalHeaderLabels(["Aplicación", "Aliases", "Ruta"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setWordWrap(True)
        self.table.setShowGrid(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.doubleClicked.connect(self.open_selected_app)

        root.addWidget(self.table, 1)

        self.all_rows: list[dict] = []
        self.load_apps()

    def load_apps(self) -> None:
        self.all_rows.clear()

        try:
            data = get_apps()
            rows = []

            for app in data:
                aliases = [a.get("alias", "") for a in app.get("aliases", [])]
                rows.append({
                    "app": str(app.get("name", "")),
                    "aliases": ", ".join(x for x in aliases if x),
                    "command": str(app.get("exec_path", "")),
                })

            rows.sort(key=lambda x: x["app"].lower())
            self.all_rows = rows

        except Exception as e:
            self.all_rows = [{
                "app": "Error",
                "aliases": "No se pudo cargar desde MariaDB",
                "command": str(e),
            }]

        self.populate_table(self.all_rows)

    def populate_table(self, rows: list[dict]) -> None:
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row["app"]))
            self.table.setItem(r, 1, QTableWidgetItem(row["aliases"]))
            self.table.setItem(r, 2, QTableWidgetItem(row["command"]))

        self.table.resizeRowsToContents()

    def apply_filter(self) -> None:
        text = self.search_input.text().strip().lower()

        if not text:
            self.populate_table(self.all_rows)
            return

        filtered = []
        for row in self.all_rows:
            haystack = f'{row["app"]} {row["aliases"]} {row["command"]}'.lower()
            if text in haystack:
                filtered.append(row)

        self.populate_table(filtered)

    def open_selected_app(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return

        item = self.table.item(row, 0)
        if item is None:
            return

        app_name = item.text().strip()
        if not app_name or app_name.lower() == "error":
            return

        self.action_requested.emit(f"abre {app_name}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.orion = OrionAssistant()

        self.voice_thread: Optional[QThread] = None
        self.voice_worker: Optional[VoiceWorker] = None
        self.voice_active = False

        self.setWindowTitle("ORION")
        self.resize(1450, 860)
        self.setMinimumSize(QSize(1180, 760))

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_header = TopHeader()
        root.addWidget(self.top_header)

        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(16)
        root.addLayout(body, 1)

        self.sidebar = LeftSidebar()
        self.sidebar.page_selected.connect(self.on_page_selected)

        self.stack = QStackedWidget()
        self.stack.addWidget(PlaceholderPage("Dashboard", "Aquí podrás mostrar métricas generales, estados y resumen del sistema."))

        self.commands_page = CommandsPage()
        self.commands_page.send_requested.connect(self.handle_text_command)
        self.commands_page.mic_requested.connect(self.handle_mic_request)
        self.stack.addWidget(self.commands_page)

        self.activity_page = ActivityPage()
        self.stack.addWidget(self.activity_page)

        self.apps_page = AppsPage()
        self.apps_page.action_requested.connect(self.handle_text_command)
        self.stack.addWidget(self.apps_page)

        self.stack.addWidget(PlaceholderPage("Dispositivos", "Aquí podrás mostrar micrófonos, audio, cámara y futura Raspberry Pi."))

        self.stack.setCurrentIndex(1)

        self.right_panel = RightPanel()
        self.right_panel.action_requested.connect(self.handle_text_command)

        body.addWidget(self.sidebar)
        body.addWidget(self.stack, 1)
        body.addWidget(self.right_panel)

        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self.refresh_backend_status)
        self.health_timer.start(5000)

        self.refresh_backend_status()

    def on_page_selected(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def refresh_backend_status(self) -> None:
        try:
            response = requests.get(f"{API_URL}/health", timeout=1.5)
            response.raise_for_status()
            data = response.json()

            self.top_header.set_api_status("Online", "#7ee787")
            self.top_header.set_db_status(
                "Conectada" if data.get("db_connected") else "Desconectada",
                "#7ee787" if data.get("db_connected") else "#ff7b72",
            )
        except Exception:
            self.top_header.set_api_status("Offline", "#ff7b72")
            self.top_header.set_db_status("Sin API", "#f2cc60")

    def handle_text_command(self, text: str) -> None:
        self.commands_page.chat_panel.add_message(
            ChatMessage("Usuario", text, MessageType.USER)
        )

        try:
            result = self.orion.process_text(text, speak=False)
            msg_type = MessageType.ASSISTANT if result.success else MessageType.ERROR

            self.commands_page.chat_panel.add_message(
                ChatMessage("ORION", result.message, msg_type)
            )

            self.activity_page.load_activity()
            self.apps_page.load_apps()

        except Exception as e:
            self.commands_page.chat_panel.add_message(
                ChatMessage("Sistema", f"Error al procesar comando: {e}", MessageType.ERROR)
            )

    def handle_mic_request(self) -> None:
        if self.voice_active:
            self.stop_voice_mode()
        else:
            self.start_voice_mode()

    def start_voice_mode(self) -> None:
        if self.voice_active:
            return

        from orion.audio.listener import Listener
        self.orion.context.listener = Listener(str(config.MODEL_PATH))

        self.voice_thread = QThread()
        self.voice_worker = VoiceWorker(self.orion)
        self.voice_worker.moveToThread(self.voice_thread)

        self.voice_thread.started.connect(self.voice_worker.run)
        self.voice_worker.status_signal.connect(self.on_voice_status)
        self.voice_worker.heard_signal.connect(self.on_voice_heard)
        self.voice_worker.response_signal.connect(self.on_voice_response)
        self.voice_worker.error_signal.connect(self.on_voice_error)
        self.voice_worker.finished.connect(self.on_voice_finished)

        self.voice_worker.finished.connect(self.voice_thread.quit)
        self.voice_worker.finished.connect(self.voice_worker.deleteLater)
        self.voice_thread.finished.connect(self.voice_thread.deleteLater)

        self.voice_active = True
        self.commands_page.input_area.set_listening(True)
        self.top_header.set_mic_status("Activo", "#7ee787")

        self.commands_page.chat_panel.add_message(
            ChatMessage("Sistema", "Escucha continua activada. Esperando hotword 'ORION'.", MessageType.SYSTEM)
        )

        self.voice_thread.start()

    def stop_voice_mode(self) -> None:
        if not self.voice_active:
            return

        self.voice_active = False

        if self.voice_worker is not None:
            self.voice_worker.stop()

        self.commands_page.input_area.set_listening(False)
        self.top_header.set_mic_status("Deteniendo...", "#f2cc60")

        self.commands_page.chat_panel.add_message(
            ChatMessage("Sistema", "Deteniendo escucha continua...", MessageType.SYSTEM)
        )

        if self.voice_thread is not None:
            self.voice_thread.quit()
            self.voice_thread.wait(3000)

    def on_voice_status(self, text: str, color: str) -> None:
        self.top_header.set_mic_status(text, color)

    def on_voice_heard(self, text: str) -> None:
        if text.startswith("[Hotword]"):
            self.commands_page.chat_panel.add_message(
                ChatMessage("Sistema", text, MessageType.SYSTEM)
            )
        else:
            self.commands_page.chat_panel.add_message(
                ChatMessage("Usuario", text, MessageType.USER)
            )

    def on_voice_response(self, message: str, success: bool) -> None:
        msg_type = MessageType.ASSISTANT if success else MessageType.ERROR
        self.commands_page.chat_panel.add_message(
            ChatMessage("ORION", message, msg_type)
        )
        self.activity_page.load_activity()
        self.apps_page.load_apps()

    def on_voice_error(self, error_text: str) -> None:
        self.commands_page.chat_panel.add_message(
            ChatMessage("Sistema", f"Error de voz: {error_text}", MessageType.ERROR)
        )

    def on_voice_finished(self) -> None:
        self.commands_page.input_area.set_listening(False)
        self.top_header.set_mic_status("Detenido", "#ff7b72")

        self.commands_page.chat_panel.add_message(
            ChatMessage("Sistema", "Escucha continua detenida.", MessageType.SYSTEM)
        )

        self.voice_worker = None
        self.voice_thread = None
        self.voice_active = False

    def closeEvent(self, event) -> None:
        try:
            if self.voice_worker is not None:
                self.voice_worker.stop()

            if self.voice_thread is not None:
                self.voice_thread.quit()
                self.voice_thread.wait(3000)

            try:
                self.orion.context.speaker.cerrar()
            except Exception:
                pass
        finally:
            event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()