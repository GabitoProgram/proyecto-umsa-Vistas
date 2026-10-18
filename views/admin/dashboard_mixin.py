import math
from datetime import date

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ----------------------------------------------------------------------
# Paleta (coherente con el login: azul institucional + acentos suaves)
# ----------------------------------------------------------------------
AZUL = "#2F6FED"
VIOLETA = "#8B5CF6"
PALETA_ANILLO = ("#2F6FED", "#14B8A6", "#F59E0B", "#8B5CF6", "#EC4899", "#64748B")
ACENTOS_KPI = ("#2F6FED", "#F59E0B", "#14B8A6", "#8B5CF6")

COLOR_TEXTO = "#334155"
COLOR_TEXTO_FUERTE = "#0F172A"
COLOR_MUDO = "#94A3B8"
COLOR_GRID = "#E5EAF1"
COLOR_PISTA = "#EEF2F7"


class _GraficoBase(QWidget):
    """Base común: fondo transparente (lo da la tarjeta) y estado vacío."""

    def __init__(self, datos, limite, parent=None):
        super().__init__(parent)
        self.datos = list(datos)[:limite]
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    @staticmethod
    def _fuente(puntos, negrita=False):
        fuente = QFont()
        fuente.setPointSizeF(puntos)
        fuente.setBold(negrita)
        return fuente

    def _pintar_vacio(self, painter, mensaje):
        painter.setPen(QColor(COLOR_MUDO))
        painter.setFont(self._fuente(10))
        painter.drawText(self.rect(), Qt.AlignCenter, mensaje)


class GraficoBarras(_GraficoBase):
    """Barras horizontales con degradado y valor al final."""

    def __init__(self, datos, color=AZUL, parent=None):
        super().__init__(datos, 8, parent)
        self.color = QColor(color)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.datos:
            self._pintar_vacio(painter, "No hay datos disponibles")
            painter.end()
            return

        fuente = self._fuente(9)
        fuente_valor = self._fuente(9, negrita=True)
        painter.setFont(fuente)
        fm = painter.fontMetrics()

        ancho, alto = self.width(), self.height()
        n = len(self.datos)
        maximo = max(valor for _, valor in self.datos) or 1

        margen_izq = min(
            int(ancho * 0.40),
            max(fm.horizontalAdvance(etiqueta) for etiqueta, _ in self.datos) + 16,
        )
        margen_izq = max(90, margen_izq)
        margen_der = max(fm.horizontalAdvance(str(v)) for _, v in self.datos) + 22
        ancho_pista = max(40, ancho - margen_izq - margen_der)

        separacion = 10
        alto_barra = max(14, min(26, (alto - 16 - (n - 1) * separacion) // n))
        total = n * alto_barra + (n - 1) * separacion
        y0 = max(8, (alto - total) // 2)
        radio = alto_barra / 2

        for indice, (etiqueta, valor) in enumerate(self.datos):
            y = y0 + indice * (alto_barra + separacion)

            painter.setFont(fuente)
            painter.setPen(QColor(COLOR_TEXTO))
            texto = fm.elidedText(etiqueta, Qt.ElideRight, margen_izq - 14)
            painter.drawText(
                QRectF(0, y, margen_izq - 12, alto_barra),
                Qt.AlignVCenter | Qt.AlignLeft,
                texto,
            )

            # Pista de fondo
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(COLOR_PISTA))
            painter.drawRoundedRect(
                QRectF(margen_izq, y, ancho_pista, alto_barra), radio, radio
            )

            # Barra con degradado
            if valor > 0:
                largo = max(alto_barra, ancho_pista * valor / maximo)
                degradado = QLinearGradient(margen_izq, 0, margen_izq + ancho_pista, 0)
                degradado.setColorAt(0.0, self.color.lighter(135))
                degradado.setColorAt(1.0, self.color)
                painter.setBrush(degradado)
                painter.drawRoundedRect(
                    QRectF(margen_izq, y, largo, alto_barra), radio, radio
                )

            painter.setFont(fuente_valor)
            painter.setPen(QColor(COLOR_TEXTO_FUERTE))
            painter.drawText(
                QRectF(margen_izq + ancho_pista + 8, y, margen_der - 8, alto_barra),
                Qt.AlignVCenter | Qt.AlignLeft,
                str(valor),
            )
        painter.end()


class GraficoLineas(_GraficoBase):
    """Línea suave con área degradada, puntos y valores. La escala parte de 0."""

    def __init__(self, datos, color=VIOLETA, parent=None):
        super().__init__(datos, 8, parent)
        self.color = QColor(color)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if not self.datos:
            self._pintar_vacio(painter, "No hay datos disponibles")
            painter.end()
            return

        izquierda, derecha, arriba, abajo = 40, 24, 30, 40
        area = QRectF(
            izquierda,
            arriba,
            max(60, self.width() - izquierda - derecha),
            max(60, self.height() - arriba - abajo),
        )
        n = len(self.datos)
        maximo = max(valor for _, valor in self.datos)
        paso = max(1, math.ceil(maximo / 4))
        tope = paso * 4

        fuente = self._fuente(8)
        painter.setFont(fuente)
        fm = painter.fontMetrics()

        # Rejilla y eje Y
        pluma_grid = QPen(QColor(COLOR_GRID), 1, Qt.DashLine)
        for nivel in range(5):
            y = area.bottom() - area.height() * nivel / 4
            painter.setPen(pluma_grid)
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            painter.setPen(QColor(COLOR_MUDO))
            painter.drawText(
                QRectF(0, y - 9, izquierda - 8, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                str(paso * nivel),
            )

        # Puntos (con margen interno para que quepan los textos de los extremos)
        margen_x = 22
        x_ini = area.left() + margen_x
        x_fin = area.right() - margen_x
        puntos = []
        for indice, (_, valor) in enumerate(self.datos):
            x = (x_ini + x_fin) / 2 if n == 1 else x_ini + (x_fin - x_ini) * indice / (n - 1)
            y = area.bottom() - area.height() * valor / tope
            puntos.append(QPointF(x, y))

        # Curva suave (Catmull-Rom convertida a Bézier)
        ruta = QPainterPath()
        ruta.moveTo(puntos[0])
        for i in range(n - 1):
            p0 = puntos[i - 1] if i > 0 else puntos[i]
            p1 = puntos[i]
            p2 = puntos[i + 1]
            p3 = puntos[i + 2] if i + 2 < n else p2
            c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6, p1.y() + (p2.y() - p0.y()) / 6)
            c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6, p2.y() - (p3.y() - p1.y()) / 6)
            c1.setY(min(area.bottom(), max(area.top(), c1.y())))
            c2.setY(min(area.bottom(), max(area.top(), c2.y())))
            ruta.cubicTo(c1, c2, p2)

        # Área bajo la curva
        if n > 1:
            area_ruta = QPainterPath(ruta)
            area_ruta.lineTo(puntos[-1].x(), area.bottom())
            area_ruta.lineTo(puntos[0].x(), area.bottom())
            area_ruta.closeSubpath()
            degradado = QLinearGradient(0, area.top(), 0, area.bottom())
            relleno = QColor(self.color)
            relleno.setAlpha(80)
            transparente = QColor(self.color)
            transparente.setAlpha(0)
            degradado.setColorAt(0.0, relleno)
            degradado.setColorAt(1.0, transparente)
            painter.setPen(Qt.NoPen)
            painter.setBrush(degradado)
            painter.drawPath(area_ruta)

            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(self.color, 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(ruta)

        # Puntos, valores y etiquetas del eje X
        ancho_etiqueta = max(34, int(area.width() / n))
        for punto, (etiqueta, valor) in zip(puntos, self.datos):
            painter.setPen(QPen(self.color, 2.4))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(punto, 4.8, 4.8)

            painter.setFont(self._fuente(8, negrita=True))
            painter.setPen(QColor(COLOR_TEXTO_FUERTE))
            painter.drawText(
                QRectF(punto.x() - 30, punto.y() - 25, 60, 18), Qt.AlignCenter, str(valor)
            )

            painter.setFont(fuente)
            painter.setPen(QColor(COLOR_TEXTO))
            texto = fm.elidedText(etiqueta, Qt.ElideRight, ancho_etiqueta)
            painter.drawText(
                QRectF(punto.x() - ancho_etiqueta / 2, area.bottom() + 10, ancho_etiqueta, 20),
                Qt.AlignHCenter | Qt.AlignTop,
                texto,
            )
        painter.end()


class GraficoAnillo(_GraficoBase):
    """Anillo con separación entre segmentos, total al centro y leyenda."""

    def __init__(self, datos, parent=None):
        super().__init__(datos, 6, parent)
        self.colores = PALETA_ANILLO

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        total = sum(valor for _, valor in self.datos)
        if not self.datos or not total:
            self._pintar_vacio(painter, "No hay asignaciones")
            painter.end()
            return

        ancho, alto = self.width(), self.height()
        grosor = 22
        diametro = max(90, min(alto - 24, int(ancho * 0.46), 200))
        x0 = 12
        y0 = (alto - diametro) / 2
        anillo = QRectF(
            x0 + grosor / 2, y0 + grosor / 2, diametro - grosor, diametro - grosor
        )

        # Pista de fondo
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(COLOR_PISTA), grosor, Qt.SolidLine, Qt.FlatCap))
        painter.drawArc(anillo, 0, 360 * 16)

        # Segmentos (empiezan a las 12 en punto y avanzan en sentido horario)
        positivos = sum(1 for _, valor in self.datos if valor > 0)
        hueco = 40 if positivos > 1 else 0
        angulo = 90 * 16
        for indice, (_, valor) in enumerate(self.datos):
            if valor <= 0:
                continue
            tramo = int(round(360 * 16 * valor / total))
            visible = tramo - hueco if tramo > hueco * 2 else tramo
            color = QColor(self.colores[indice % len(self.colores)])
            painter.setPen(QPen(color, grosor, Qt.SolidLine, Qt.FlatCap))
            painter.drawArc(anillo, angulo - hueco // 2, -visible)
            angulo -= tramo

        # Total al centro
        centro_y = y0 + diametro / 2
        painter.setPen(QColor(COLOR_TEXTO_FUERTE))
        painter.setFont(self._fuente(20, negrita=True))
        painter.drawText(QRectF(x0, centro_y - 24, diametro, 28), Qt.AlignCenter, str(total))
        painter.setPen(QColor(COLOR_MUDO))
        painter.setFont(self._fuente(8))
        painter.drawText(QRectF(x0, centro_y + 4, diametro, 18), Qt.AlignCenter, "asignados")

        # Leyenda
        x_leyenda = x0 + diametro + 30
        disponible = ancho - x_leyenda - 8
        if disponible < 60:
            painter.end()
            return

        fuente_leyenda = self._fuente(9)
        painter.setFont(fuente_leyenda)
        fm = painter.fontMetrics()
        fila = 36
        y = (alto - len(self.datos) * fila) / 2
        for indice, (etiqueta, valor) in enumerate(self.datos):
            color = QColor(self.colores[indice % len(self.colores)])
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x_leyenda, y + 4, 11, 11), 3, 3)

            painter.setFont(fuente_leyenda)
            painter.setPen(QColor(COLOR_TEXTO))
            texto = fm.elidedText(etiqueta, Qt.ElideRight, int(disponible - 20))
            painter.drawText(
                QRectF(x_leyenda + 20, y, disponible - 20, 18),
                Qt.AlignLeft | Qt.AlignVCenter,
                texto,
            )

            porcentaje = valor * 100 / total
            painter.setFont(self._fuente(8))
            painter.setPen(QColor(COLOR_MUDO))
            painter.drawText(
                QRectF(x_leyenda + 20, y + 17, disponible - 20, 16),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{valor} · {porcentaje:.0f}%",
            )
            y += fila
        painter.end()


class DashboardMixin:
    ESTILOS_DASHBOARD = """
        QLabel { background: transparent; border: none; }
        QScrollArea { background: transparent; border: none; }
        QWidget#dashboardContent { background: transparent; }

        QFrame#dashCard {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
        }

        QLabel#dashTitle    { color: #0F2C59; font-size: 26px; font-weight: 800; }
        QLabel#dashSubtitle { color: #64748B; font-size: 13px; }

        QLabel#kpiLabel     { color: #64748B; font-size: 11px; font-weight: 700; }
        QLabel#kpiValue     { color: #0F172A; font-size: 34px; font-weight: 800; }
        QLabel#kpiValueText { color: #0F172A; font-size: 24px; font-weight: 800; }
        QLabel#kpiHint      { color: #94A3B8; font-size: 12px; }

        QLabel#chartTitle   { color: #1E293B; font-size: 16px; font-weight: 800; }
        QLabel#chartSub     { color: #94A3B8; font-size: 12px; }

        QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #C3D2E0; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #9FB6CB; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """

    PISTAS_KPI = (
        "Periodo en curso",
        "Postulantes sin registro completo",
        "Programados para hoy",
        "Aulas activas",
    )

    def _crear_dashboard_view(self):
        pagina = QWidget()
        pagina.setStyleSheet(self.ESTILOS_DASHBOARD)
        pagina_layout = QVBoxLayout(pagina)
        pagina_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        pagina_layout.addWidget(scroll)

        contenido = QWidget()
        contenido.setObjectName("dashboardContent")
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(22)
        scroll.setWidget(contenido)

        # Encabezado
        titulo = QLabel("Dashboard Resumen")
        titulo.setObjectName("dashTitle")
        subtitulo = QLabel(f"Vista general del sistema · {date.today().strftime('%d/%m/%Y')}")
        subtitulo.setObjectName("dashSubtitle")
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addSpacing(4)

        datos, graficos = self._cargar_resumen_dashboard()

        # Tarjetas de resumen
        tarjetas = QHBoxLayout()
        tarjetas.setSpacing(18)
        for indice, (etiqueta, valor) in enumerate(datos):
            tarjetas.addWidget(
                self._crear_tarjeta_kpi(
                    etiqueta,
                    valor,
                    self.PISTAS_KPI[indice % len(self.PISTAS_KPI)],
                    ACENTOS_KPI[indice % len(ACENTOS_KPI)],
                ),
                1,
            )
        layout.addLayout(tarjetas)

        # Fila 1: barras + anillo
        fila_superior = QHBoxLayout()
        fila_superior.setSpacing(18)
        fila_superior.addWidget(
            self._crear_tarjeta_grafico(
                "Inscritos por carrera",
                "Inscripciones activas por carrera",
                GraficoBarras(graficos["carreras"], AZUL),
            ),
            3,
        )
        fila_superior.addWidget(
            self._crear_tarjeta_grafico(
                "Distribución por aula",
                "Postulantes asignados (asignados/capacidad)",
                GraficoAnillo(graficos["aulas"]),
            ),
            2,
        )
        layout.addLayout(fila_superior)

        # Fila 2: líneas a todo el ancho
        layout.addWidget(
            self._crear_tarjeta_grafico(
                "Evolución por gestión",
                "Inscripciones activas por gestión",
                GraficoLineas(graficos["gestiones"], VIOLETA),
            )
        )
        layout.addStretch()
        return pagina

    def _crear_tarjeta_kpi(self, etiqueta, valor, pista, color):
        tarjeta = QFrame()
        tarjeta.setObjectName("dashCard")
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(20, 18, 20, 18)
        fila.setSpacing(16)

        acento = QFrame()
        acento.setFixedWidth(5)
        acento.setStyleSheet(f"background: {color}; border: none; border-radius: 2px;")
        fila.addWidget(acento)

        columna = QVBoxLayout()
        columna.setSpacing(4)
        lbl_etiqueta = QLabel(str(etiqueta).upper())
        lbl_etiqueta.setObjectName("kpiLabel")
        columna.addWidget(lbl_etiqueta)

        lbl_valor = QLabel(str(valor))
        lbl_valor.setObjectName("kpiValue" if str(valor).isdigit() else "kpiValueText")
        columna.addWidget(lbl_valor)

        lbl_pista = QLabel(pista)
        lbl_pista.setObjectName("kpiHint")
        columna.addWidget(lbl_pista)

        fila.addLayout(columna, 1)
        return tarjeta

    def _crear_tarjeta_grafico(self, titulo, subtitulo, grafico):
        tarjeta = QFrame()
        tarjeta.setObjectName("dashCard")
        layout = QVBoxLayout(tarjeta)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(2)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("chartTitle")
        lbl_sub = QLabel(subtitulo)
        lbl_sub.setObjectName("chartSub")
        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_sub)
        layout.addSpacing(8)
        layout.addWidget(grafico, stretch=1)
        return tarjeta

    def _cargar_resumen_dashboard(self):
        gestiones = self._obtener_lista("/admin/gestiones")
        postulantes = self._obtener_lista("/postulantes?limit=1000")
        examenes = self._obtener_lista("/admin/examenes")
        aulas = self._obtener_lista("/admin/aulas")
        carreras = self._obtener_lista("/admin/carreras")
        inscripciones = self._obtener_lista("/inscripciones")
        hoy = date.today().isoformat()
        gestion_activa = next((g.get("nombre") for g in gestiones if g.get("estado") == "ACTIVO"), "Sin gestión")
        pendientes = sum(
            1 for p in postulantes if str(p.get("estado_biometria", "")).upper() != "COMPLETO"
        )
        examenes_hoy = sum(1 for examen in examenes if examen.get("fecha") == hoy)
        aulas_disponibles = sum(1 for aula in aulas if aula.get("activa", True))
        carreras_por_id = {c.get("id_carrera"): c.get("nombre", "Sin nombre") for c in carreras}
        gestiones_por_id = {g.get("id_gestion"): g.get("nombre", "Sin nombre") for g in gestiones}
        carrera_totales = {}
        gestion_totales = {}
        for inscripcion in inscripciones:
            if str(inscripcion.get("estado", "")).upper() == "RETIRADO":
                continue
            carrera = carreras_por_id.get(inscripcion.get("id_carrera"), "Sin carrera")
            gestion = gestiones_por_id.get(inscripcion.get("id_gestion"), "Sin gestión")
            carrera_totales[carrera] = carrera_totales.get(carrera, 0) + 1
            gestion_totales[gestion] = gestion_totales.get(gestion, 0) + 1

        asignados_por_aula = {}
        for examen in examenes:
            id_examen = examen.get("id_examen")
            if not id_examen:
                continue
            for asignacion in self._obtener_lista(f"/asignaciones/examen/{id_examen}"):
                id_aula = asignacion.get("id_aula")
                asignados_por_aula[id_aula] = asignados_por_aula.get(id_aula, 0) + 1
        aula_totales = [
            (
                f"{aula.get('nombre', 'Sin nombre')} "
                f"({asignados_por_aula.get(aula.get('id_aula'), 0)}/"
                f"{int(aula.get('capacidad', 0) or 0)})",
                asignados_por_aula.get(aula.get("id_aula"), 0),
            )
            for aula in aulas
        ]
        resumen = (
            ("Gestión activa", gestion_activa),
            ("Biometría pendiente", pendientes),
            ("Exámenes de hoy", examenes_hoy),
            ("Aulas disponibles", aulas_disponibles),
        )
        graficos = {
            "carreras": sorted(carrera_totales.items(), key=lambda item: item[1], reverse=True),
            "gestiones": [
                (gestiones_por_id.get(gestion.get("id_gestion"), "Sin gestión"), gestion_totales.get(
                    gestiones_por_id.get(gestion.get("id_gestion"), "Sin gestión"), 0
                ))
                for gestion in sorted(gestiones, key=lambda item: (item.get("anio", 0), item.get("id_gestion", 0)))
            ],
            "aulas": sorted(aula_totales, key=lambda item: item[1], reverse=True),
        }
        return resumen, graficos