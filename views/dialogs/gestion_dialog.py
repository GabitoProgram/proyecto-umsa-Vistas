import os
import tempfile
from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea,
    QDateEdit, QToolButton,
)
from PySide6.QtCore import QDate, QLocale, QSize, Qt, QTimer, QPointF
from PySide6.QtGui import (
    QColor, QIcon, QImage, QPainter, QPen, QPixmap, QTextCharFormat,
)
import cv2


# ======================================================================
# Estilos
# ======================================================================
ESTILO_DIALOGO = """
    QDialog { background: #F1F5F9; }
    QLabel { color: #334155; font-weight: 600; background: transparent; border: none; }
    QToolTip {
        background: #0F172A; color: #FFFFFF; border: none;
        padding: 6px 10px; font-size: 12px;
    }

    /* ---------- Campos ----------
       El QLineEdit va por objectName: así la regla no se hereda al
       campo interno de los selectores de fecha ni al del calendario. */
    QLineEdit#campoGestion, QComboBox, QDateEdit {
        min-height: 34px; padding: 2px 12px;
        border: 1px solid #E2E8F0; border-radius: 9px;
        background: #FFFFFF; color: #0F172A; font-size: 13px;
    }
    QLineEdit#campoGestion:hover, QComboBox:hover, QDateEdit:hover {
        border: 1px solid #CBD5E1;
    }
    QLineEdit#campoGestion:focus, QComboBox:focus, QDateEdit:focus {
        border: 1px solid #1E54B7;
    }
    QComboBox::drop-down, QDateEdit::drop-down {
        subcontrol-origin: padding; subcontrol-position: center right;
        width: 30px; border: none;
    }
    QComboBox::down-arrow, QDateEdit::down-arrow {
        image: url("%(flecha)s"); width: 12px; height: 12px;
    }
    QComboBox QAbstractItemView {
        background: #FFFFFF; color: #0F172A;
        border: 1px solid #E2E8F0; outline: 0;
        selection-background-color: #E8F0FD; selection-color: #0F172A;
    }

    /* ---------- Botones ---------- */
    QPushButton {
        min-width: 100px; min-height: 36px; padding: 0 18px;
        border-radius: 9px; font-size: 13px; font-weight: 700;
        background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1;
    }
    QPushButton:hover { background: #F8FAFC; border: 1px solid #94A3B8; }
    QPushButton:pressed { background: #EEF2F7; }
    QPushButton#BtnPrimario {
        background: #1E54B7; color: #FFFFFF; border: 1px solid #1E54B7;
    }
    QPushButton#BtnPrimario:hover { background: #17449A; border: 1px solid #17449A; }
    QPushButton#BtnPrimario:pressed { background: #123A83; border: 1px solid #123A83; }
"""

ESTILO_CALENDARIO = """
    QCalendarWidget {
        background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 10px;
    }

    /* Barra superior: mes, año y flechas */
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        background: #0F2C59; min-height: 44px;
        border-top-left-radius: 9px; border-top-right-radius: 9px;
    }
    QCalendarWidget QToolButton {
        color: #FFFFFF; background: transparent; border: none;
        border-radius: 8px; padding: 4px 10px;
        font-size: 14px; font-weight: 700; icon-size: 18px;
    }
    QCalendarWidget QToolButton:hover { background: rgba(255, 255, 255, 0.16); }
    QCalendarWidget QToolButton:pressed { background: rgba(255, 255, 255, 0.28); }
    QCalendarWidget QToolButton::menu-indicator { image: none; }
    QCalendarWidget QMenu {
        background: #FFFFFF; color: #0F172A;
        border: 1px solid #E2E8F0; padding: 4px;
    }
    QCalendarWidget QMenu::item { padding: 6px 22px; border-radius: 6px; }
    QCalendarWidget QMenu::item:selected { background: #E8F0FD; color: #0F172A; }
    QCalendarWidget QSpinBox {
        background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1;
        border-radius: 6px; padding: 2px 6px; font-size: 13px; font-weight: 700;
        selection-background-color: #1E54B7; selection-color: #FFFFFF;
    }
    QCalendarWidget QSpinBox QLineEdit {
        border: none; background: transparent; min-height: 0; padding: 0;
    }

    /* Cuadrícula de días */
    QCalendarWidget QAbstractItemView:enabled {
        background: #FFFFFF; color: #0F172A; font-size: 13px; outline: 0;
        selection-background-color: #1E54B7; selection-color: #FFFFFF;
    }
    QCalendarWidget QAbstractItemView:disabled { color: #CBD5E1; }
"""

_RUTA_FLECHA = None


def _pix_chevron(direccion, color, lado=24, grosor=2.4):
    """Chevron «<», «>» o «v» dibujado por código (sin archivos de imagen)."""
    pix = QPixmap(lado, lado)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    lapiz = QPen(QColor(color), grosor)
    lapiz.setCapStyle(Qt.RoundCap)
    lapiz.setJoinStyle(Qt.RoundJoin)
    p.setPen(lapiz)
    c = lado / 2
    r = lado * 0.2
    if direccion == "abajo":
        puntos = [(c - r * 1.4, c - r * 0.7), (c, c + r * 0.7), (c + r * 1.4, c - r * 0.7)]
    elif direccion == "izquierda":
        puntos = [(c + r * 0.7, c - r * 1.4), (c - r * 0.7, c), (c + r * 0.7, c + r * 1.4)]
    else:  # derecha
        puntos = [(c - r * 0.7, c - r * 1.4), (c + r * 0.7, c), (c - r * 0.7, c + r * 1.4)]
    p.drawLine(QPointF(*puntos[0]), QPointF(*puntos[1]))
    p.drawLine(QPointF(*puntos[1]), QPointF(*puntos[2]))
    p.end()
    return pix


def _ruta_flecha():
    """Guarda (una vez) la flecha de los desplegables y devuelve su ruta para el QSS."""
    global _RUTA_FLECHA
    if _RUTA_FLECHA is None:
        ruta = os.path.join(tempfile.gettempdir(), "umsa_flecha_abajo.png")
        _pix_chevron("abajo", "#64748B").save(ruta, "PNG")
        _RUTA_FLECHA = ruta.replace("\\", "/")
    return _RUTA_FLECHA


def _estilizar_calendario(calendario):
    """Aplica diseño al calendario desplegable."""
    es = QLocale(QLocale.Spanish, QLocale.Bolivia)
    calendario.setLocale(es)
    calendario.setFirstDayOfWeek(Qt.Monday)
    calendario.setGridVisible(False)
    calendario.setVerticalHeaderFormat(calendario.VerticalHeaderFormat.NoVerticalHeader)
    calendario.setHorizontalHeaderFormat(calendario.HorizontalHeaderFormat.ShortDayNames)
    calendario.setMinimumSize(320, 270)
    calendario.setStyleSheet(ESTILO_CALENDARIO)

    # Flechas de mes anterior / siguiente (blancas, dibujadas por código).
    anterior = calendario.findChild(QToolButton, "qt_calendar_prevmonth")
    siguiente = calendario.findChild(QToolButton, "qt_calendar_nextmonth")
    if anterior:
        anterior.setIcon(QIcon(_pix_chevron("izquierda", "#FFFFFF")))
        anterior.setIconSize(QSize(18, 18))
        anterior.setCursor(Qt.PointingHandCursor)
    if siguiente:
        siguiente.setIcon(QIcon(_pix_chevron("derecha", "#FFFFFF")))
        siguiente.setIconSize(QSize(18, 18))
        siguiente.setCursor(Qt.PointingHandCursor)

    # Fila de nombres de día: fondo suave y texto gris.
    cabecera = QTextCharFormat()
    cabecera.setBackground(QColor("#F1F5F9"))
    cabecera.setForeground(QColor("#64748B"))
    cabecera.setFontWeight(700)
    calendario.setHeaderTextFormat(cabecera)

    # Sábado y domingo en rojo suave.
    fin_semana = QTextCharFormat()
    fin_semana.setForeground(QColor("#DC2626"))
    calendario.setWeekdayTextFormat(Qt.Saturday, fin_semana)
    calendario.setWeekdayTextFormat(Qt.Sunday, fin_semana)

    # El día de hoy resaltado.
    hoy = QTextCharFormat()
    hoy.setForeground(QColor("#1E54B7"))
    hoy.setBackground(QColor("#E8F0FD"))
    hoy.setFontWeight(700)
    calendario.setDateTextFormat(QDate.currentDate(), hoy)


def _a_qdate(valor, por_defecto):
    """Convierte «YYYY-MM-DD» (o «YYYY-MM-DDTHH:MM…») a QDate; si no sirve, usa el valor por defecto."""
    if valor:
        fecha = QDate.fromString(str(valor)[:10], "yyyy-MM-dd")
        if fecha.isValid():
            return fecha
    return por_defecto


def _selector_fecha(fecha):
    """Campo de fecha con calendario desplegable (como en las páginas web)."""
    campo = QDateEdit()
    campo.setCalendarPopup(True)            # el botón ▼ abre el calendario
    campo.setDisplayFormat("dd/MM/yyyy")    # lo que ve el usuario
    campo.setLocale(QLocale(QLocale.Spanish, QLocale.Bolivia))  # meses y días en español
    campo.setDate(fecha)
    campo.setCursor(Qt.PointingHandCursor)
    _estilizar_calendario(campo.calendarWidget())
    return campo


class DialogGestion(QDialog):
    def __init__(self, gestion=None, parent=None):
        super().__init__(parent)
        self.gestion = gestion or {}
        self.setWindowTitle("Editar Gestión" if gestion else "Nueva Gestión")
        self.setFixedSize(420, 420)
        self.setStyleSheet(ESTILO_DIALOGO % {"flecha": _ruta_flecha()})
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)

        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.txt_nombre = QLineEdit(self.gestion.get("nombre", ""))
        self.txt_nombre.setObjectName("campoGestion")
        self.spin_anio = QLineEdit(str(self.gestion.get("anio", date.today().year)))
        self.spin_anio.setObjectName("campoGestion")
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(["I", "II", "ANUAL"])
        if "periodo" in self.gestion:
            self.combo_periodo.setCurrentText(self.gestion["periodo"])

        # Fechas con calendario. Se conservan los nombres txt_inicio / txt_fin
        # por si otra parte del código los usa.
        hoy = QDate.currentDate()
        inicio = _a_qdate(self.gestion.get("fecha_inicio"), hoy)
        fin = _a_qdate(self.gestion.get("fecha_fin"), inicio)
        self.txt_inicio = _selector_fecha(inicio)
        self.txt_fin = _selector_fecha(fin)
        # Si el inicio pasa a ser posterior al fin, el fin se ajusta solo.
        self.txt_inicio.dateChanged.connect(self._ajustar_fin)

        for w in [self.txt_nombre, self.spin_anio, self.combo_periodo, self.txt_inicio, self.txt_fin]:
            w.setMinimumHeight(34)

        form.addRow("Nombre *:", self.txt_nombre)
        form.addRow("Año *:", self.spin_anio)
        form.addRow("Periodo:", self.combo_periodo)
        form.addRow("Fecha Inicio *:", self.txt_inicio)
        form.addRow("Fecha Fin *:", self.txt_fin)

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

    def _ajustar_fin(self, nuevo_inicio):
        if self.txt_fin.date() < nuevo_inicio:
            self.txt_fin.setDate(nuevo_inicio)

    def accept(self):
        if self.txt_fin.date() < self.txt_inicio.date():
            QMessageBox.warning(
                self, "Fechas", "La fecha de fin no puede ser anterior a la fecha de inicio."
            )
            return
        super().accept()

    def get_data(self):
        return {
            "nombre": self.txt_nombre.text().strip(),
            "anio": int(self.spin_anio.text().strip() or date.today().year),
            "periodo": self.combo_periodo.currentText(),
            # Mismo formato que antes (YYYY-MM-DD), así la API recibe lo mismo.
            "fecha_inicio": self.txt_inicio.date().toString("yyyy-MM-dd"),
            "fecha_fin": self.txt_fin.date().toString("yyyy-MM-dd"),
            "estado": self.gestion.get("estado", "ACTIVO") if self.gestion else "ACTIVO"
        }