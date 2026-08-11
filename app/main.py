from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QSize, Qt, QThread, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QDoubleSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QToolBar,
    QVBoxLayout, QWidget, QPlainTextEdit,
)

from app.core.database import Database
from app.core.export_service import ExportService
from app.core.face_engine import FaceEngine
from app.core.image_io import load_image_bgr
from app.core.model_factory import FaceAnalysisFactory
from app.workers import (
    FeedbackWorker, ScanWorker, SearchWorker, ThumbnailWorker, export_failures,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = DATA / "index.db"
CACHE = DATA / "thumbnails"
DEFAULT_LIBRARY = str(Path.home() / "Pictures")  # cross-platform default; change in the UI via "选择图库"


def setup_logging() -> None:
    DATA.joinpath("logs").mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        DATA / "logs" / "app.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler],
    )


class QtLogHandler(logging.Handler):
    def __init__(self, widget: QPlainTextEdit) -> None:
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        self.widget.appendPlainText(self.format(record))


def stable_query_id(library_root: str, target: np.ndarray) -> str:
    """跨次搜索稳定的 query_id：library_root + 目标脸 embedding 哈希。"""
    vec = np.ascontiguousarray(target, dtype=np.float32).tobytes()
    digest = hashlib.sha1(vec).hexdigest()[:16]
    return f"lib={Path(library_root).resolve()}|face={digest}"


class MainWindow(QMainWindow):
    def __init__(self, engine: FaceEngine, model_message: str = "") -> None:
        super().__init__()
        self.engine = engine
        self.faces: list = []
        self.target: np.ndarray | None = None
        self.hits: list = []
        self.query_id = ""
        self.thread: QThread | None = None
        self.worker = None
        self.thumb_thread: QThread | None = None
        self.thumb_worker = None
        self._feedback_thread: QThread | None = None
        self.setWindowTitle("本地人脸照片检索")
        self.resize(1180, 780)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        Database(DB_PATH).close()
        self._build_ui()
        if model_message:
            self.log.appendPlainText(model_message)

    # ---------------- UI construction ----------------

    def _build_ui(self) -> None:
        top = QWidget()
        form = QFormLayout(top)
        self.reference = QLabel("请选择参考照片")
        self.reference.setMinimumSize(260, 190)
        self.reference.setAlignment(Qt.AlignCenter)
        choose = QPushButton("选择参考照片")
        choose.clicked.connect(self.choose_reference)

        self.face_list = QListWidget()
        self.face_list.setViewMode(QListWidget.IconMode)
        self.face_list.setIconSize(QSize(96, 96))
        self.face_list.itemClicked.connect(self.select_face)

        self.library = QLabel(DEFAULT_LIBRARY)
        library_btn = QPushButton("选择图库")
        library_btn.clicked.connect(self.choose_library)
        lib_row = QHBoxLayout()
        lib_row.addWidget(self.library, 1)
        lib_row.addWidget(library_btn)

        self.high = QDoubleSpinBox()
        self.high.setRange(0, 1)
        self.high.setValue(0.55)
        self.high.setSingleStep(0.01)
        self.manual = QDoubleSpinBox()
        self.manual.setRange(0, 1)
        self.manual.setValue(0.35)
        self.manual.setSingleStep(0.01)

        scan = QPushButton("扫描/增量索引")
        scan.clicked.connect(self.start_scan)
        search = QPushButton("搜索")
        search.clicked.connect(self.start_search)
        cancel = QPushButton("停止扫描")
        cancel.clicked.connect(self.cancel_scan)
        actions = QHBoxLayout()
        for widget in (choose, scan, cancel, search):
            actions.addWidget(widget)

        form.addRow("参考图", self.reference)
        form.addRow("选择目标脸", self.face_list)
        form.addRow("图库", lib_row)
        th = QHBoxLayout()
        th.addWidget(QLabel("高置信 ≥"))
        th.addWidget(self.high)
        th.addWidget(QLabel("人工确认 ≥"))
        th.addWidget(self.manual)
        form.addRow("阈值", th)
        form.addRow(actions)
        self.progress = QProgressBar()
        form.addRow(self.progress)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["缩略图", "分组", "相似度", "路径"])
        self.table.setIconSize(QSize(180, 135))
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setRowHeight(0, 140)

        buttons = QHBoxLayout()
        for text, slot in [
            ("打开原图", self.open_original),
            ("打开文件夹", self.open_folder),
            ("确认", lambda: self.feedback("confirmed")),
            ("排除", lambda: self.feedback("excluded")),
            ("复制所选", self.copy_selected),
        ]:
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)

        result_widget = QWidget()
        rv = QVBoxLayout(result_widget)
        rv.addWidget(self.table)
        rv.addLayout(buttons)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(2000)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(top)
        lv.addWidget(QLabel("运行日志"))
        lv.addWidget(self.log)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(result_widget)
        splitter.setSizes([420, 760])
        self.setCentralWidget(splitter)

        bar = QToolBar()
        self.addToolBar(bar)
        show_failures = QAction("查看失败记录", self)
        show_failures.triggered.connect(self.show_failures)
        bar.addAction(show_failures)
        export_csv = QAction("导出失败 CSV", self)
        export_csv.triggered.connect(self.export_failure_csv)
        bar.addAction(export_csv)

        handler = QtLogHandler(self.log)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logging.getLogger().addHandler(handler)

    # ---------------- reference + face selection ----------------

    def choose_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择参考照片", "", "图片 (*.jpg *.jpeg *.png)")
        if not path:
            return
        image = load_image_bgr(path)
        if image is None:
            return self.error("参考照片无法读取")
        try:
            self.faces = self.engine.extract(image)
        except Exception as exc:  # noqa: BLE001 - 引擎层异常向用户报告
            return self.error(str(exc))
        if not self.faces:
            return self.error("参考照片中未检测到人脸")
        self.reference.setPixmap(
            QPixmap(path).scaled(self.reference.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.face_list.clear()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        for index, face in enumerate(self.faces):
            x1, y1, x2, y2 = [max(0, int(v)) for v in face.bbox]
            crop = rgb[y1:y2, x1:x2].copy()
            qimage = QImage(
                crop.data,
                crop.shape[1],
                crop.shape[0],
                crop.strides[0],
                QImage.Format_RGB888,
            ).copy()
            item = QListWidgetItem(QIcon(QPixmap.fromImage(qimage)), f"人脸 {index + 1}")
            item.setData(Qt.UserRole, index)
            self.face_list.addItem(item)
        self.face_list.setCurrentRow(0)
        self.target = self.faces[0].embedding
        self.log.appendPlainText(f"参考图检测到 {len(self.faces)} 张脸")

    def select_face(self, item) -> None:
        self.target = self.faces[item.data(Qt.UserRole)].embedding

    def choose_library(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择图库", self.library.text())
        if path:
            self.library.setText(path)

    # ---------------- workers ----------------

    def _run_worker(self, worker, finished):
        self.worker = worker
        self.thread = QThread(self)
        worker.moveToThread(self.thread)
        self.thread.started.connect(worker.run)
        worker.finished.connect(finished)
        worker.finished.connect(self.thread.quit)
        worker.failed.connect(self.error)
        worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(worker.deleteLater)
        self.thread.finished.connect(self._clear_main_thread)
        self.thread.start()

    def _clear_main_thread(self) -> None:
        if self.thread is not None:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None

    def start_scan(self) -> None:
        if self.thread and self.thread.isRunning():
            return self.error("已有后台任务正在运行")
        worker = ScanWorker(str(DB_PATH), self.engine, self.library.text())
        worker.progress.connect(self.scan_progress)
        self._run_worker(worker, self.scan_done)
        self.log.appendPlainText("开始增量扫描…")

    def scan_progress(self, done: int, total: int, path: str) -> None:
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)
        self.log.appendPlainText(path)

    def scan_done(self, report) -> None:
        msg = (
            f"扫描完成：总计 {report.total_files}，"
            f"新增/更新 {report.indexed}，跳过 {report.skipped}，"
            f"失败 {report.failed}"
        )
        if report.missing:
            msg += f"，标记 missing {report.missing}"
        if report.errors:
            msg += f"，错误 {report.errors}"
        self.log.appendPlainText(msg)

    def cancel_scan(self) -> None:
        if isinstance(self.worker, ScanWorker):
            self.worker.cancel()
            self.log.appendPlainText("将在当前图片处理完后停止")

    def start_search(self) -> None:
        if self.target is None:
            return self.error("请先选择参考照片中的目标脸")
        if self.thread and self.thread.isRunning():
            return self.error("已有后台任务正在运行")
        # 同步 query_id 绑定当前库 + 目标脸；跨次搜索保持稳定
        self.query_id = stable_query_id(self.library.text(), self.target)
        worker = SearchWorker(
            str(DB_PATH),
            self.target,
            float(self.manual.value()),
            self.query_id,
            self.library.text(),
        )
        self._run_worker(worker, self.search_done)

    def search_done(self, hits) -> None:
        # 关键修复：旧的缩略图线程要先排空再启动新的
        self._drain_thumb_thread()
        self.hits = hits
        self.table.setRowCount(len(hits))
        manual = float(self.manual.value())
        for row, hit in enumerate(hits):
            group = "高置信" if hit.score >= float(self.high.value()) else "人工确认"
            if hit.score < manual:
                # 不会到这里，但保留兜底
                group = "低于阈值"
            self.table.setItem(row, 0, QTableWidgetItem("加载中"))
            self.table.setItem(row, 1, QTableWidgetItem(group))
            self.table.setItem(row, 2, QTableWidgetItem(f"{hit.score:.3f}"))
            self.table.setItem(row, 3, QTableWidgetItem(hit.photo_path))
            self.table.setRowHeight(row, 140)
        self.log.appendPlainText(f"搜索完成：{len(hits)} 张照片")
        if hits:
            self._start_thumb_thread(hits)

    def _drain_thumb_thread(self) -> None:
        if self.thumb_thread is not None:
            if self.thumb_thread.isRunning():
                self.thumb_thread.quit()
                self.thumb_thread.wait(2000)
            self.thumb_thread = None
        self.thumb_worker = None

    def _start_thumb_thread(self, hits) -> None:
        worker = ThumbnailWorker(
            str(CACHE),
            [(index, hit.photo_path) for index, hit in enumerate(hits)],
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.ready.connect(self.thumbnail_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thumb_finished)
        self.thumb_thread = thread
        self.thumb_worker = worker
        thread.start()

    def _on_thumb_finished(self) -> None:
        self.thumb_thread = None
        self.thumb_worker = None

    def thumbnail_ready(self, row: int, path: str) -> None:
        item = self.table.item(row, 0)
        if item is not None:
            item.setIcon(QIcon(path))
            item.setText("")

    # ---------------- row actions ----------------

    def selected_hit(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.hits):
            return self.hits[row]
        return None

    def open_original(self) -> None:
        hit = self.selected_hit()
        if hit:
            QDesktopServices.openUrl(QUrl.fromLocalFile(hit.photo_path))

    def open_folder(self) -> None:
        hit = self.selected_hit()
        if not hit:
            return
        # Windows 下用 explorer /select 需写成单一参数
        subprocess.Popen(["explorer.exe", f"/select,{Path(hit.photo_path)}"])

    def feedback(self, decision: str) -> None:
        hit = self.selected_hit()
        if not hit:
            return
        if not self.query_id:
            return self.error("请先执行一次搜索")
        row = self.table.currentRow()
        worker = FeedbackWorker(
            str(DB_PATH),
            self.query_id,
            hit.photo_id,
            decision,
            hit.score,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda pid, dec, r=row: self._on_feedback(r, dec, pid))
        worker.failed.connect(self.error)
        worker.failed.connect(thread.quit)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._feedback_thread = thread
        thread.start()

    def _on_feedback(self, row: int, decision: str, photo_id: int) -> None:
        if not (0 <= row < len(self.hits)):
            return
        if decision == "excluded":
            # 同步从当前视图移除，避免 currentRow 偏移
            self.table.removeRow(row)
            if row < len(self.hits):
                del self.hits[row]
        else:
            item = self.table.item(row, 1)
            if item is not None:
                item.setText("已确认")
        label = "已确认" if decision == "confirmed" else "已排除"
        self.log.appendPlainText(f"{label}：{self.hits[row].photo_path if row < len(self.hits) else ''}")

    def copy_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        paths = [self.hits[row].photo_path for row in rows if 0 <= row < len(self.hits)]
        if not paths:
            return self.error("请先选择结果")
        destination = QFileDialog.getExistingDirectory(self, "选择复制目标目录")
        if not destination:
            return
        service = ExportService()
        ok = 0
        failed: list[str] = []
        for src in paths:
            try:
                written = service.export([src], destination)
                ok += len(written)
            except (OSError, shutil.SameFileError) as exc:
                failed.append(f"{src} -> {exc}")
        self.log.appendPlainText(f"已复制 {ok} 张照片到 {destination}")
        for line in failed:
            self.log.appendPlainText("复制失败：" + line)

    # ---------------- failures ----------------

    def show_failures(self) -> None:
        db = Database(DB_PATH)
        try:
            rows = db.list_unresolved_failures()
        finally:
            db.close()
        text = "\n\n".join(
            f"{r['occurred_at']}\n{r['photo_path']}\n{r['exception_type']}: {r['message']}"
            for r in rows
        ) or "没有失败记录"
        QMessageBox.information(self, "失败记录", text[:12000])

    def export_failure_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出失败记录", "scan_failures.csv", "CSV (*.csv)")
        if not path:
            return
        self.log.appendPlainText(f"已导出 {export_failures(str(DB_PATH), path)} 条失败记录：{path}")

    # ---------------- misc ----------------

    def error(self, text: str) -> None:
        self.log.appendPlainText("错误：" + text)
        QMessageBox.critical(self, "错误", text)


def create_window() -> tuple[QApplication, MainWindow]:
    setup_logging()
    app = QApplication.instance() or QApplication(sys.argv)
    factory = FaceAnalysisFactory()
    insight = factory.create()
    message = factory.info.warning if factory.info and factory.info.warning else ""
    return app, MainWindow(FaceEngine(insight), message)


def main() -> int:
    try:
        app, window = create_window()
    except Exception as exc:  # noqa: BLE001
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "启动失败", str(exc))
        logging.exception("startup failed")
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
