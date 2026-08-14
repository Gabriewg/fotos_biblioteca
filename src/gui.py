import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pillow_heif
from PIL import Image, ImageFile, ImageOps
from PySide6.QtCore import QSharedMemory, QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QListView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from .duplicates import duplicate_groups
from .metadata import get_photo_datetime
from .organizer import PHOTO_EXTENSIONS, organize_photos

IMAGE_FILTER = (
    "Imagens (*.jpg *.jpeg *.png *.gif *.bmp *.tif *.tiff *.webp *.heic *.heif);;"
    "Todos os arquivos (*.*)"
)

MONTHS_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

_MISSING = object()

WINE_STYLESHEET = """
* {
    font-family: "Segoe UI";
    font-size: 13px;
    outline: none;
}
QMainWindow, QDialog {
    background-color: #1d0b10;
}
QLabel {
    color: #f3e2e6;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #7e2440, stop:1 #591830);
    color: #fbeef1;
    border: 1px solid #93304f;
    border-radius: 9px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #93304f, stop:1 #6d2038);
    border-color: #a84a68;
}
QPushButton:pressed {
    background: #4a1224;
    border-color: #7e2440;
}
QPushButton:disabled {
    background: #3a1a26;
    color: #8a6a74;
    border-color: #4a1a2c;
}
QPushButton#organizeBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #a22d4f, stop:1 #7a1f3a);
    border-color: #c0406a;
    padding: 12px 26px;
    font-size: 14px;
}
QPushButton#organizeBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #bb3a5e, stop:1 #8a2444);
}
QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #8a1f1f, stop:1 #631414);
    border-color: #a83232;
}
QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #a32929, stop:1 #7a1a1a);
}
QLineEdit {
    background-color: #2a1018;
    color: #f3e2e6;
    border: 1px solid #6b1d33;
    border-radius: 9px;
    padding: 7px 12px;
    selection-background-color: #93304f;
}
QLineEdit:focus {
    border-color: #c0406a;
}
QCheckBox {
    color: #f3e2e6;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid #93304f;
    background-color: #2a1018;
}
QCheckBox::indicator:hover {
    border-color: #c0406a;
}
QCheckBox::indicator:checked {
    background-color: #a22d4f;
    border-color: #c0406a;
}
QListWidget {
    background-color: #250e15;
    border: 1px solid #4a1a2c;
    border-radius: 12px;
    color: #f3e2e6;
    padding: 10px;
}
QListWidget::item {
    padding: 6px;
    border-radius: 10px;
}
QListWidget::item:hover {
    background-color: #451727;
}
QListWidget::item:selected {
    background-color: #7e2440;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #6b1d33;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #93304f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 4px;
}
QScrollBar::handle:horizontal {
    background: #6b1d33;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #93304f;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QMessageBox {
    background-color: #250e15;
}
QMessageBox QLabel {
    color: #f3e2e6;
    font-size: 14px;
}
QMessageBox QPushButton {
    min-width: 90px;
}
"""


def _pil_to_qimage(img: Image.Image) -> QImage | None:
    try:
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        data = img.tobytes("raw", "RGB")
        qimage = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
        return qimage.copy()
    except Exception:
        return None


def _load_qimage(path: Path) -> QImage | None:
    try:
        with Image.open(path) as img:
            img.load()
            qimage = _pil_to_qimage(img)
            if qimage is not None and not qimage.isNull():
                return qimage
    except Exception:
        pass

    qimage = QImage(str(path))
    if not qimage.isNull():
        return qimage
    return None


def _thumbnail_qimage(path: Path, size: int = 120) -> QImage | None:
    try:
        with Image.open(path) as img:
            img.load()
            img.thumbnail((size, size))
            qimage = _pil_to_qimage(img)
            if qimage is not None and not qimage.isNull():
                return qimage
    except Exception:
        pass

    qimage = QImage(str(path))
    if not qimage.isNull():
        return qimage.scaled(
            size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
    return None


def _thumbnail_pixmap(path: Path, size: int = 120) -> QPixmap | None:
    qimage = _thumbnail_qimage(path, size)
    if qimage is None:
        return None
    return QPixmap.fromImage(qimage)


class PreviewDialog(QDialog):
    def __init__(self, paths: list[Path], index: int, parent=None):
        super().__init__(parent)
        self._paths = paths
        self._index = index
        self.resize(1000, 720)
        self.setMinimumSize(400, 300)

        self.pixmap = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: #0d0407; border-radius: 10px; color: #f3e2e6;"
        )

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #d9a0b2; padding: 6px;")

        self.open_btn = QPushButton("Abrir com o visualizador padrão")
        self.open_btn.setStyleSheet("QPushButton { padding: 6px 16px; font-weight: 600; }")
        self.open_btn.clicked.connect(self._open_external)
        self.open_btn.hide()

        self.reveal_btn = QPushButton("Abrir local do arquivo")
        self.reveal_btn.setStyleSheet("QPushButton { padding: 6px 16px; font-weight: 600; }")
        self.reveal_btn.clicked.connect(self._reveal_file)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        buttons_row.addWidget(self.reveal_btn)
        buttons_row.addWidget(self.open_btn)
        buttons_row.addStretch(1)

        layout.addWidget(self.image_label, 1)
        layout.addLayout(buttons_row)
        layout.addWidget(self.info_label)

        self._load()

    def _reveal_file(self):
        path = str(self._current())
        try:
            subprocess.Popen(["explorer", "/select,", path])
        except Exception:
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._current().parent)))
            except Exception:
                pass

    def _open_external(self):
        path = str(self._current())
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception:
            pass

    def _current(self) -> Path:
        return self._paths[self._index]

    def _load(self):
        path = self._current()
        self.setWindowTitle(path.name)

        self.pixmap = None
        qimage = _load_qimage(path)
        if qimage is not None:
            self.pixmap = QPixmap.fromImage(qimage)

        if self.pixmap is None:
            self.image_label.setText("Não foi possível carregar a imagem")
            self.open_btn.show()
        else:
            self.image_label.setText("")
            self.open_btn.hide()
            self._update_preview()

        dt = get_photo_datetime(path)
        date_label = dt.strftime("%d/%m/%Y %H:%M") if dt else "sem data"
        counter = f"{self._index + 1}/{len(self._paths)}" if len(self._paths) > 1 else ""
        text = f"{counter}  •  {date_label}" if counter else date_label
        self.info_label.setText(text)
        self.info_label.setToolTip(f"{path.name}  •  use ← → para navegar, Esc para fechar")

    def _update_preview(self):
        if self.pixmap is None:
            return
        available = self.image_label.size()
        if available.width() <= 1 or available.height() <= 1:
            return
        scaled = self.pixmap.scaled(
            available, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left and len(self._paths) > 1:
            self._index = (self._index - 1) % len(self._paths)
            self._load()
        elif event.key() == Qt.Key.Key_Right and len(self._paths) > 1:
            self._index = (self._index + 1) % len(self._paths)
            self._load()
        elif event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
        else:
            super().keyPressEvent(event)


class PhotoGrid(QListWidget):
    HEADER_ROLE = Qt.ItemDataRole.UserRole + 5

    def __init__(self):
        super().__init__()
        self._headers: list[QListWidgetItem] = []
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setUniformItemSizes(False)
        self.setIconSize(QSize(120, 120))
        self.setSpacing(10)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionRectVisible(True)

    def clear(self):
        self._headers = []
        super().clear()

    def add_header(self, text: str):
        header = QListWidgetItem(text)
        header.setFlags(Qt.ItemFlag.ItemIsEnabled)
        header.setData(self.HEADER_ROLE, True)
        header.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        font = header.font()
        font.setPointSize(12)
        font.setBold(True)
        header.setFont(font)
        header.setForeground(QColor("#f7dbe3"))
        header.setSizeHint(QSize(max(self.viewport().width(), 200), 42))
        self.addItem(header)
        self._headers.append(header)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = max(self.viewport().width(), 200)
        for header in self._headers:
            header.setSizeHint(QSize(width, 42))


class MonthHeaderDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.data(PhotoGrid.HEADER_ROLE):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = option.rect.adjusted(2, 4, -2, -8)
            painter.setBrush(QColor("#3f1626"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 9, 9)
            painter.setPen(QColor("#f7dbe3"))
            font = option.font
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, index.data(Qt.ItemDataRole.DisplayRole))
            painter.restore()
        else:
            super().paint(painter, option, index)


class FolderScanWorker(QThread):
    photo_ready = Signal(object, object, object)
    scan_done = Signal(int)

    def __init__(self, folder: Path):
        super().__init__()
        self._folder = folder
        self._stop = False

    def request_stop(self):
        self._stop = True

    def run(self):
        photos: list[Path] = []
        stack = [self._folder]
        while stack and not self._stop:
            directory = stack.pop()
            try:
                children = list(directory.iterdir())
            except OSError:
                continue
            for child in children:
                if self._stop:
                    break
                try:
                    if child.is_dir():
                        stack.append(child)
                    elif child.is_file() and child.suffix.lower() in PHOTO_EXTENSIONS:
                        photos.append(child)
                except OSError:
                    continue

        if self._stop:
            return

        entries = []
        for photo in photos:
            if self._stop:
                return
            try:
                dt = get_photo_datetime(photo)
            except Exception:
                dt = None
            entries.append((photo, dt))

        entries.sort(key=lambda e: e[1] if e[1] else datetime.max, reverse=True)

        for photo, dt in entries:
            if self._stop:
                return
            thumb = _thumbnail_qimage(photo)
            self.photo_ready.emit(str(photo), dt, thumb)

        self.scan_done.emit(len(entries))


class DuplicateScanWorker(QThread):
    finished_scan = Signal(object)

    def __init__(self, photos: list[Path]):
        super().__init__()
        self._photos = photos

    def run(self):
        try:
            result = duplicate_groups(self._photos)
        except Exception:
            result = []
        self.finished_scan.emit(result)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fotos Organizer")
        self.resize(1200, 720)

        self.sources: list[Path] = []
        self.photo_entries: list[dict] = []
        self._thumbs: dict[str, QImage] = {}
        self._known: set[str] = set()
        self._scan_group: object = _MISSING
        self._scan_worker: FolderScanWorker | None = None
        self._dup_worker: DuplicateScanWorker | None = None
        self._dup_marked: set[str] = set()
        self._generation = 0
        self._dup_generation = 0
        self._organized = False
        self._stop_scan = False
        self.reset_view_btn: QPushButton | None = None
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet(
            "background-color: #250e15; border: 1px solid #4a1a2c; border-radius: 12px;"
        )
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 12, 12, 12)
        side.setSpacing(10)

        title = QLabel("Fotos Organizer")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f3e2e6;")
        side.addWidget(title)

        add_files_btn = QPushButton("＋ Adicionar fotos")
        add_files_btn.clicked.connect(self._add_files)
        add_folder_btn = QPushButton("＋ Adicionar pasta")
        add_folder_btn.clicked.connect(self._add_folder)
        remove_btn = QPushButton("Remover selecionadas")
        remove_btn.clicked.connect(self._remove_selected)
        duplicates_btn = QPushButton("Detectar duplicadas")
        duplicates_btn.clicked.connect(self._detect_duplicates)
        clear_btn = QPushButton("Limpar")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self._clear)
        open_output_btn = QPushButton("Abrir destino")
        open_output_btn.clicked.connect(self._open_output)

        for btn in (
            add_files_btn,
            add_folder_btn,
            remove_btn,
            duplicates_btn,
            clear_btn,
            open_output_btn,
        ):
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            side.addWidget(btn)

        side.addSpacing(4)
        side.addWidget(QLabel("Filtrar por data"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("ex.: 2026  ou  2026-08  ou  08/2026")
        self.filter_edit.textChanged.connect(self._apply_filter)
        side.addWidget(self.filter_edit)

        side.addSpacing(8)
        side.addWidget(QLabel("Pasta de destino"))

        output_row = QHBoxLayout()
        output_row.setSpacing(6)
        self.output_edit = QLineEdit(str(Path("output").resolve()))
        self.output_edit.setPlaceholderText("Pasta de destino")
        browse_btn = QPushButton("⋯")
        browse_btn.setFixedWidth(42)
        browse_btn.clicked.connect(self._choose_output)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(browse_btn)
        side.addLayout(output_row)

        self.dry_run_check = QCheckBox("Simular (dry-run)")
        self.dry_run_check.setChecked(True)
        self.rename_check = QCheckBox("Renomear com a data")
        side.addWidget(self.dry_run_check)
        side.addWidget(self.rename_check)

        side.addStretch(1)

        organize_row = QHBoxLayout()
        organize_btn = QPushButton("Organizar")
        organize_btn.setObjectName("organizeBtn")
        organize_btn.clicked.connect(self._organize)
        organize_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.reset_view_btn = QPushButton("✕")
        self.reset_view_btn.setObjectName("dangerBtn")
        self.reset_view_btn.setFixedWidth(44)
        self.reset_view_btn.setToolTip("Voltar à visualização normal")
        self.reset_view_btn.clicked.connect(self._reset_view)
        self.reset_view_btn.hide()
        organize_row.addWidget(organize_btn, 1)
        organize_row.addWidget(self.reset_view_btn)
        side.addLayout(organize_row)

        root.addWidget(sidebar)

        right = QVBoxLayout()
        right.setSpacing(8)

        self.photo_grid = PhotoGrid()
        self.photo_grid.setItemDelegate(MonthHeaderDelegate(self.photo_grid))
        self.photo_grid.itemDoubleClicked.connect(self._preview_item)
        self.photo_grid.itemActivated.connect(self._preview_item)
        right.addWidget(self.photo_grid, 1)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #d9a0b2; padding: 4px 2px;")
        right.addWidget(self.status_label)

        root.addLayout(right, 1)
        self.setCentralWidget(central)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecionar fotos", "", IMAGE_FILTER)
        if paths:
            if self._scan_worker is not None and self._scan_worker.isRunning():
                self.status_label.setText("Aguarde a leitura da pasta terminar.")
                return
            existing = {str(p) for p in self.sources}
            self.sources.extend(Path(p) for p in paths if str(Path(p)) not in existing)
            self._rebuild_browse()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta")
        if not folder:
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            self.status_label.setText("Já existe uma leitura em andamento.")
            return
        self._start_folder_scan(Path(folder))

    def _start_folder_scan(self, folder: Path):
        self._stop_scan_worker()
        self._generation += 1
        self._organized = False
        if self.reset_view_btn is not None:
            self.reset_view_btn.hide()
        self.photo_grid.clear()
        self.sources = []
        self.photo_entries = []
        self._thumbs = {}
        self._known = set()
        self._scan_group = _MISSING
        self._dup_marked = set()
        self._stop_scan = False

        worker = FolderScanWorker(folder)
        worker.photo_ready.connect(self._on_photo_ready)
        worker.scan_done.connect(self._on_scan_done)
        worker.finished.connect(worker.deleteLater)
        self._scan_worker = worker
        self.status_label.setText("Lendo pasta... isto pode levar um instante.")
        worker.start()

    def _stop_scan_worker(self):
        self._stop_scan = True
        if self._scan_worker is not None:
            self._scan_worker.request_stop()
        self._scan_worker = None

    def _on_photo_ready(self, path_str, dt, thumb):
        if self._stop_scan:
            return
        path = Path(path_str)
        key = str(path)
        if key in self._known:
            return
        self._known.add(key)
        self.sources.append(path)
        if thumb is not None:
            self._thumbs[key] = thumb
        entry = {
            "path": path,
            "dt": dt,
            "date_label": dt.strftime("%d/%m/%Y") if dt else "sem data",
            "subtitle": "",
            "tooltip": str(path),
        }
        self._append_tile_incremental(entry)
        self.status_label.setText(f"Lendo pasta... {len(self.photo_entries)} foto(s) encontrada(s).")

    def _on_scan_done(self, total):
        self._scan_worker = None
        if self._stop_scan:
            return
        if self.filter_edit.text().strip():
            self._apply_filter()
        else:
            self.status_label.setText(self._count_text(total))

    def _append_tile_incremental(self, entry: dict):
        dt = entry["dt"]
        key = (dt.year, dt.month) if dt else None
        if key != self._scan_group:
            self._scan_group = key
            label = "Sem data" if key is None else f"{MONTHS_PT[key[1] - 1]} de {key[0]}"
            self.photo_grid.add_header(label)
        self.photo_entries.append(entry)
        self._add_tile(entry)

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar pasta de destino")
        if folder:
            self.output_edit.setText(folder)

    def _open_output(self):
        output = Path(self.output_edit.text().strip())
        output.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output)))

    def _remove_selected(self):
        items = self.photo_grid.selectedItems()
        paths = [
            Path(item.data(Qt.ItemDataRole.UserRole))
            for item in items
            if item.data(Qt.ItemDataRole.UserRole) and not item.data(PhotoGrid.HEADER_ROLE)
        ]
        if not paths:
            self.status_label.setText("Selecione uma ou mais fotos para remover (Ctrl/Shift).")
            return
        doomed = {str(p) for p in paths}
        self.sources = [s for s in self.sources if str(s) not in doomed]
        self._dup_marked -= doomed
        self._rebuild_browse()

    def _detect_duplicates(self):
        if not self.photo_entries:
            return
        if self._scan_worker is not None and self._scan_worker.isRunning():
            self.status_label.setText("Aguarde a leitura da pasta terminar.")
            return
        if self._dup_worker is not None and self._dup_worker.isRunning():
            return
        self._dup_generation = self._generation
        self.status_label.setText("Detectando duplicadas...")
        worker = DuplicateScanWorker([e["path"] for e in self.photo_entries])
        worker.finished_scan.connect(self._on_duplicates_done)
        worker.finished.connect(worker.deleteLater)
        self._dup_worker = worker
        worker.start()

    def _on_duplicates_done(self, groups):
        self._dup_worker = None
        if self._dup_generation != self._generation:
            return
        marked: set[str] = set()
        for kept, dups in groups:
            for dup in dups:
                marked.add(str(dup))
        self._dup_marked = marked
        for entry in self.photo_entries:
            entry["dup"] = str(entry["path"]) in marked
        self._populate_grouped()

        count = len(marked)
        if count == 0:
            self.status_label.setText("Nenhuma duplicada encontrada.")
            return

        answer = QMessageBox.question(
            self,
            "Duplicadas",
            f"{count} duplicada(s) encontrada(s). Removê-las da lista "
            "(mantendo a primeira de cada grupo)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.sources = [s for s in self.sources if str(s) not in marked]
            self.photo_entries = [e for e in self.photo_entries if str(e["path"]) not in marked]
            self._dup_marked = set()
            self._rebuild_browse()
            self.status_label.setText(f"{count} duplicada(s) removida(s) da lista.")
        else:
            self.status_label.setText(f"{count} duplicada(s) marcada(s) no grid.")

    def _apply_filter(self):
        if self._scan_worker is not None and self._scan_worker.isRunning():
            return
        text = self.filter_edit.text().strip()
        if not text:
            self._populate_grouped()
            self.status_label.setText(self._count_text(len(self.photo_entries)))
            return
        visible = [e for e in self.photo_entries if self._entry_matches_filter(e, text)]
        self._populate_grouped(visible)
        self.status_label.setText(f"{len(visible)} de {len(self.photo_entries)} foto(s).")

    def _entry_matches_filter(self, entry: dict, text: str) -> bool:
        dt = entry["dt"]
        if dt is None:
            return False
        year = re.fullmatch(r"\d{4}", text)
        if year:
            return dt.year == int(year.group(0))
        month_year = re.fullmatch(r"(\d{1,2})/(\d{4})", text)
        if month_year:
            return dt.year == int(month_year.group(2)) and dt.month == int(month_year.group(1))
        year_month = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
        if year_month:
            return dt.year == int(year_month.group(1)) and dt.month == int(year_month.group(2))
        return False

    def _count_text(self, count: int) -> str:
        if count == 0:
            return "Nenhuma foto adicionada."
        return f"{count} foto(s). Clique duas vezes para visualizar."

    def _clear(self):
        if not self.sources and not self.photo_entries:
            return
        answer = QMessageBox.question(
            self,
            "Limpar lista",
            "Tem certeza que deseja remover todas as fotos da lista?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._stop_scan_worker()
            self._generation += 1
            self._organized = False
            if self.reset_view_btn is not None:
                self.reset_view_btn.hide()
            self.sources.clear()
            self.photo_grid.clear()
            self.photo_entries = []
            self._thumbs = {}
            self._known = set()
            self._scan_group = _MISSING
            self._refresh_status()

    def _rebuild_browse(self):
        self._stop_scan_worker()
        self._generation += 1
        self._organized = False
        if self.reset_view_btn is not None:
            self.reset_view_btn.hide()
        self.photo_grid.clear()
        self.photo_entries = []
        self._scan_group = _MISSING

        entries = []
        for photo in self.sources:
            dt = get_photo_datetime(photo)
            entries.append(
                {
                    "path": photo,
                    "dt": dt,
                    "date_label": dt.strftime("%d/%m/%Y") if dt else "sem data",
                    "subtitle": "",
                    "tooltip": str(photo),
                }
            )
        entries.sort(key=lambda e: e["dt"] if e["dt"] else datetime.max, reverse=True)
        for entry in entries:
            self._append_tile_incremental(entry)
        if self.filter_edit.text().strip():
            self._apply_filter()
        else:
            self._refresh_status()

    def _add_tile(self, entry: dict):
        path = entry["path"]
        key = str(path)
        thumb = self._thumbs.get(key, _MISSING)
        if thumb is _MISSING:
            thumb = _thumbnail_qimage(path)
            self._thumbs[key] = thumb

        subtitle = entry.get("subtitle", "")
        if thumb is None:
            subtitle = "⚠ não foi possível abrir"
        elif entry.get("dup") and not subtitle:
            subtitle = "⚠ duplicada"
        item = QListWidgetItem()
        item.setText(f"{entry['date_label']}\n{subtitle}" if subtitle else entry["date_label"])
        tooltip = entry.get("tooltip", "")
        if tooltip:
            item.setToolTip(tooltip)
        if thumb is not None:
            item.setIcon(QIcon(QPixmap.fromImage(thumb)))
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        item.setData(Qt.ItemDataRole.UserRole + 1, str(entry.get("destination", path)))
        font = item.font()
        font.setPointSize(10)
        item.setFont(font)
        self.photo_grid.addItem(item)

    def _populate_grouped(self, entries: list[dict] | None = None):
        if entries is None:
            entries = self.photo_entries
        self.photo_grid.clear()
        self._scan_group = _MISSING
        groups: dict[tuple[int, int], list[dict]] = {}
        undated: list[dict] = []
        for entry in entries:
            dt = entry["dt"]
            if dt is None:
                undated.append(entry)
            else:
                groups.setdefault((dt.year, dt.month), []).append(entry)

        for (year, month), entries in sorted(groups.items(), reverse=True):
            label = f"{MONTHS_PT[month - 1]} de {year}"
            self.photo_grid.add_header(label)
            for entry in entries:
                self._add_tile(entry)

        if undated:
            self.photo_grid.add_header("Sem data")
            for entry in undated:
                self._add_tile(entry)

    def _refresh_status(self):
        count = len(self.sources) if self.sources else len(self.photo_entries)
        self.status_label.setText(self._count_text(count))

    def _preview_item(self, item):
        paths = [
            Path(self.photo_grid.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.photo_grid.count())
            if not self.photo_grid.item(i).data(PhotoGrid.HEADER_ROLE)
        ]
        if not paths:
            return
        current_path = item.data(Qt.ItemDataRole.UserRole)
        try:
            row = paths.index(Path(current_path))
        except ValueError:
            return
        dialog = PreviewDialog(paths, row, self)
        dialog.exec()

    def _organize(self):
        if not self.photo_entries:
            return

        output = Path(self.output_edit.text().strip())
        dry_run = self.dry_run_check.isChecked()
        rename = self.rename_check.isChecked()

        actions = organize_photos(
            [e["path"] for e in self.photo_entries],
            output,
            dry_run=dry_run,
            rename_with_date=rename,
        )

        entries = []
        ready = 0
        skipped = 0
        for action in actions:
            dt = get_photo_datetime(action.source)
            date_label = dt.strftime("%d/%m/%Y") if dt else "sem data"
            if action.skipped:
                subtitle = f"IGNORADA: {action.skipped_reason}"
                tooltip = str(action.source)
                destination = str(action.source)
                skipped += 1
            else:
                subtitle = f"→ {action.destination.parent}"
                tooltip = str(action.destination)
                destination = str(action.destination)
                ready += 1
            entries.append(
                {
                    "path": action.source,
                    "dt": dt,
                    "date_label": date_label,
                    "subtitle": subtitle,
                    "tooltip": tooltip,
                    "destination": destination,
                }
            )

        self.photo_entries = entries
        self._populate_grouped()
        self._organized = True
        if self.reset_view_btn is not None:
            self.reset_view_btn.show()

        if dry_run:
            message = (
                f"{ready} foto(s) prontas para organizar, {skipped} ignorada(s). "
                "Desmarque 'Simular (dry-run)' para copiar de verdade."
            )
        else:
            message = f"{ready} foto(s) copiada(s) para '{output}', {skipped} ignorada(s)."
        self.status_label.setText(message)

    def _reset_view(self):
        self._rebuild_browse()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(WINE_STYLESHEET)

    singleton = QSharedMemory("fotos_organizer_singleton")
    if not singleton.create(1):
        return

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()