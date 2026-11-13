import os
import tempfile
from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea,
    QTimeEdit,
)
from PySide6.QtCore import QDate, QTime, Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QTransform
import cv2

# Se reutiliza el diseño del diálogo de Gestión (calendario, campos y botones),
# así los dos diálogos se ven igual y no se duplica código.
from desktop.views.dialogs.gestion_dialog import (
    ESTILO_DIALOGO,
    _a_qdate,
    _pix_chevron,
    _ruta_flecha,
    _selector_fecha,
)


# Estilo del selector de hora (QTimeEdit): mismo aspecto que los demás campos,
# con botones ▲ ▼ a la derecha.
ESTILO_HORA = """
    QTimeEdit {
        min-height: 34px; padding: 2px 12px;
        border: 1px solid #E2E8F0; border-radius: 9px;
        background: #FFFFFF; color: #0F172A; font-size: 13px; font-weight: 600;
        selection-background-color: #1E54B7; selection-color: #FFFFFF;
    }
    QTimeEdit:hover { border: 1px solid #CBD5E1; }
    QTimeEdit:focus { border: 1px solid #1E54B7; }
    QTimeEdit::up-button {
        subcontrol-origin: border; subcontrol-position: top right;
        width: 28px; border: none; border-top-right-radius: 8px;
    }
    QTimeEdit::down-button {
        subcontrol-origin: border; subcontrol-position: bottom right;
        width: 28px; border: none; border-bottom-right-radius: 8px;
    }
    QTimeEdit::up-button:hover, QTimeEdit::down-button:hover { background: #F1F5F9; }
    QTimeEdit::up-button:pressed, QTimeEdit::down-button:pressed { background: #E2E8F0; }
    QTimeEdit::up-arrow { image: url("%(arriba)s"); width: 10px; height: 10px; }
    QTimeEdit::down-arrow { image: url("%(abajo)s"); width: 10px; height: 10px; }
"""

_RUTA_FLECHA_ARRIBA = None


def _ruta_flecha_arriba():
    """Flecha hacia arriba (la de abajo girada 180°), guardada una sola vez."""
    global _RUTA_FLECHA_ARRIBA
    if _RUTA_FLECHA_ARRIBA is None:
        ruta = os.path.join(tempfile.gettempdir(), "umsa_flecha_arriba.png")
        pix = _pix_chevron("abajo", "#64748B").transformed(QTransform().rotate(180))
        pix.save(ruta, "PNG")
        _RUTA_FLECHA_ARRIBA = ruta.replace("\\", "/")
    return _RUTA_FLECHA_ARRIBA


def _a_qtime(valor, por_defecto):
    """Convierte «HH:MM» (o «HH:MM:SS») a QTime; si no sirve, usa el valor por defecto."""
    if valor:
        hora = QTime.fromString(str(valor)[:5], "HH:mm")
        if hora.isValid():
            return hora
    return por_defecto


def _selector_hora(hora):
    """Selector de hora: se puede escribir, usar las flechas o la rueda del mouse."""
    campo = QTimeEdit()
    campo.setDisplayFormat("HH:mm")
    campo.setTime(hora)
    campo.setToolTip("Escriba la hora o use las flechas")
    return campo


class DialogExamen(QDialog):
    def __init__(self, examen=None, gestion_id=None, carrera_id=None, parent=None):
        super().__init__(parent)
        self.examen = examen or {"id_gestion": gestion_id, "id_carrera": carrera_id}
        self.setWindowTitle("Editar Examen" if examen else "Nuevo Examen")
        self.setFixedSize(420, 400)
        self.setStyleSheet(
            ESTILO_DIALOGO % {"flecha": _ruta_flecha()}
            + ESTILO_HORA % {"arriba": _ruta_flecha_arriba(), "abajo": _ruta_flecha()}
        )
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)

        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.txt_materia = QLineEdit(self.examen.get("materia", ""))
        self.txt_materia.setObjectName("campoGestion")

        # Fecha con calendario y horas con selector. Se conservan los nombres
        # txt_fecha / txt_inicio / txt_fin por si otra parte del código los usa.
        self.txt_fecha = _selector_fecha(_a_qdate(self.examen.get("fecha"), QDate.currentDate()))
        hora_inicio = _a_qtime(self.examen.get("hora_inicio"), QTime(8, 0))
        hora_fin = _a_qtime(self.examen.get("hora_fin"), hora_inicio.addSecs(2 * 3600))
        self.txt_inicio = _selector_hora(hora_inicio)
        self.txt_fin = _selector_hora(hora_fin)

        for w in [self.txt_materia, self.txt_fecha, self.txt_inicio, self.txt_fin]:
            w.setMinimumHeight(34)

        form.addRow("Materia *:", self.txt_materia)
        form.addRow("Fecha *:", self.txt_fecha)
        form.addRow("Hora Inicio *:", self.txt_inicio)
        form.addRow("Hora Fin *:", self.txt_fin)
        layout.addLayout(form)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("BtnPrimario")
        btn_save.clicked.connect(self.accept)
        for b in [btn_cancel, btn_save]:
            b.setMinimumHeight(38)
            b.setCursor(Qt.PointingHandCursor)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def accept(self):
        if self.txt_fin.time() <= self.txt_inicio.time():
            QMessageBox.warning(
                self, "Horario", "La hora de fin debe ser posterior a la hora de inicio."
            )
            return
        super().accept()

    def get_data(self):
        d = dict(self.examen)
        # id_examen no es parte del schema de actualización; se ignora en el backend
        d.pop("id_examen", None)
        d.update({
            "materia": self.txt_materia.text().strip(),
            # Mismos formatos que antes: fecha YYYY-MM-DD y horas HH:MM.
            "fecha": self.txt_fecha.date().toString("yyyy-MM-dd"),
            "hora_inicio": self.txt_inicio.time().toString("HH:mm"),
            "hora_fin": self.txt_fin.time().toString("HH:mm"),
        })
        # Al crear no existe estado/tolerancia; al editar se conservan los actuales
        d.setdefault("estado", "PROGRAMADO")
        d.setdefault("tolerancia_minutos", 10)
        return d