"""柱状图、折线图与扇形图的 SVG 生成函数（纯标准库，字符串拼接）。"""

import html
import math
from typing import List, Sequence, Tuple

from chartread.dataio import Series, format_number, format_percent

CANVAS_WIDTH = 640
CANVAS_HEIGHT = 420
CHART_TYPES = ("bar", "line", "pie")
CHART_NAMES = {"bar": "柱状图", "line": "折线图", "pie": "扇形图"}

_MARGIN_LEFT = 64
_MARGIN_RIGHT = 24
_MARGIN_TOP = 56
_MARGIN_BOTTOM = 56
_TICK_STEPS = 5

_PIE_CENTER_X = 232.0
_PIE_CENTER_Y = 220.0
_PIE_RADIUS = 116.0

_COLORS = (
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#e15759",
    "#76b7b2",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
)


def _text(
    x: float,
    y: float,
    content: str,
    css_class: str,
    anchor: str = "middle",
    size: int = 13,
    fill: str = "#333333",
) -> str:
    """拼接一段 SVG 文本元素，内容自动转义。"""
    return (
        '<text class="{0}" x="{1:.1f}" y="{2:.1f}" font-size="{3}" '
        'text-anchor="{4}" fill="{5}">{6}</text>'
    ).format(
        css_class, x, y, size, anchor, fill, html.escape(content, quote=True)
    )


def _svg_head(title: str, subtitle: str) -> List[str]:
    """返回 SVG 开头（画布、背景、标题、副标题）的片段列表。"""
    return [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{1}" '
            'viewBox="0 0 {0} {1}" role="img" aria-label="{2}">'
        ).format(
            CANVAS_WIDTH,
            CANVAS_HEIGHT,
            html.escape("{0}：{1}".format(title, subtitle), quote=True),
        ),
        '<rect x="0" y="0" width="{0}" height="{1}" fill="#ffffff"/>'.format(
            CANVAS_WIDTH, CANVAS_HEIGHT
        ),
        _text(CANVAS_WIDTH / 2.0, 30.0, title, "chart-title", size=18, fill="#222222"),
        _text(
            CANVAS_WIDTH / 2.0, 48.0, subtitle, "chart-subtitle", size=12, fill="#666666"
        ),
    ]


def _plot_area() -> Tuple[float, float, float, float]:
    """返回绘图区左上角坐标与宽高。"""
    width = CANVAS_WIDTH - _MARGIN_LEFT - _MARGIN_RIGHT
    height = CANVAS_HEIGHT - _MARGIN_TOP - _MARGIN_BOTTOM
    return float(_MARGIN_LEFT), float(_MARGIN_TOP), float(width), float(height)


def _nice_max(value: float) -> float:
    """把最大值向上取整到 1、2、2.5、5、10 倍数量级，便于刻度标注。"""
    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    base = 10.0 ** exponent
    for factor in (1.0, 2.0, 2.5, 5.0, 10.0):
        candidate = factor * base
        if candidate >= value - 1e-9:
            return candidate
    return 10.0 * base


def _axes(y_max: float) -> List[str]:
    """返回坐标轴、网格线与 y 轴刻度的片段列表。"""
    left, top, width, height = _plot_area()
    baseline = top + height
    right = left + width
    parts = [
        (
            '<line class="axis" x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{1:.1f}" '
            'stroke="#333333" stroke-width="1.5"/>'
        ).format(left, baseline, right),
        (
            '<line class="axis" x1="{0:.1f}" y1="{1:.1f}" x2="{0:.1f}" y2="{2:.1f}" '
            'stroke="#333333" stroke-width="1.5"/>'
        ).format(left, top, baseline),
    ]
    for step in range(_TICK_STEPS + 1):
        value = y_max * step / _TICK_STEPS
        y = baseline - height * (value / y_max)
        parts.append(
            (
                '<line class="grid" x1="{0:.1f}" y1="{1:.1f}" x2="{2:.1f}" y2="{1:.1f}" '
                'stroke="#dddddd" stroke-width="1"/>'
            ).format(left, y, right)
        )
        parts.append(
            _text(
                left - 10.0,
                y + 4.0,
                format_number(value),
                "tick",
                anchor="end",
                size=12,
                fill="#555555",
            )
        )
    return parts


def _check_series(series: Series) -> None:
    """校验传入对象确实是 ``Series``。"""
    if not isinstance(series, Series):
        raise TypeError("series 必须是 Series 对象")


def build_bar_chart(series: Series) -> str:
    """生成柱状图 SVG：含坐标轴、刻度、柱体、数值标签与类目名。"""
    _check_series(series)
    left, top, width, height = _plot_area()
    baseline = top + height
    y_max = _nice_max(series.maximum())
    parts = _svg_head("柱状图", "共 {0} 个类目".format(len(series)))
    parts.extend(_axes(y_max))
    slot = width / float(len(series))
    bar_width = slot * 0.6
    for index in range(len(series)):
        label = series.labels[index]
        value = series.values[index]
        center_x = left + slot * (index + 0.5)
        bar_height = height * (value / y_max)
        bar_y = baseline - bar_height
        color = _COLORS[index % len(_COLORS)]
        parts.append(
            (
                '<rect class="bar" x="{0:.1f}" y="{1:.1f}" width="{2:.1f}" '
                'height="{3:.1f}" rx="3" fill="{4}"/>'
            ).format(center_x - bar_width / 2.0, bar_y, bar_width, bar_height, color)
        )
        parts.append(
            _text(
                center_x,
                max(bar_y - 8.0, top + 12.0),
                format_number(value),
                "value",
                size=13,
            )
        )
        parts.append(_text(center_x, baseline + 24.0, label, "category", size=13))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build_line_chart(series: Series) -> str:
    """生成折线图 SVG：含折线、数据点、坐标轴与数值标签。"""
    _check_series(series)
    left, top, width, height = _plot_area()
    baseline = top + height
    y_max = _nice_max(series.maximum())
    parts = _svg_head("折线图", "共 {0} 个类目".format(len(series)))
    parts.extend(_axes(y_max))
    slot = width / float(len(series))
    points: List[Tuple[float, float]] = []
    for index in range(len(series)):
        x = left + slot * (index + 0.5)
        y = baseline - height * (series.values[index] / y_max)
        points.append((x, y))
    coord_text = " ".join("{0:.1f},{1:.1f}".format(x, y) for x, y in points)
    parts.append(
        (
            '<polyline class="line" fill="none" stroke="#4e79a7" stroke-width="2.5" '
            'stroke-linejoin="round" points="{0}"/>'
        ).format(coord_text)
    )
    for index in range(len(series)):
        x, y = points[index]
        parts.append(
            (
                '<circle class="point" cx="{0:.1f}" cy="{1:.1f}" r="4" '
                'fill="#ffffff" stroke="#4e79a7" stroke-width="2"/>'
            ).format(x, y)
        )
        parts.append(
            _text(
                x,
                max(y - 10.0, top + 12.0),
                format_number(series.values[index]),
                "value",
                size=12,
            )
        )
        parts.append(_text(x, baseline + 24.0, series.labels[index], "category", size=13))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _pie_percentages(values: Sequence[float]) -> List[float]:
    """把各数值换算成保留 1 位小数、合计恰好为 100.0 的百分比列表。"""
    total = float(sum(values))
    if total <= 0:
        raise ValueError("扇形图要求所有数值之和大于 0")
    raw = [float(value) / total * 100.0 for value in values]
    rounded = [round(item, 1) for item in raw]
    residual = round(100.0 - sum(rounded), 1)
    if abs(residual) >= 0.05:
        target = 0
        for index in range(1, len(values)):
            if values[index] > values[target]:
                target = index
        rounded[target] = round(rounded[target] + residual, 1)
    return rounded


def _slice_path(
    cx: float, cy: float, radius: float, start_deg: float, end_deg: float
) -> str:
    """返回一个扇形路径的 d 属性字符串。"""
    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)
    x1 = cx + radius * math.cos(start_rad)
    y1 = cy + radius * math.sin(start_rad)
    x2 = cx + radius * math.cos(end_rad)
    y2 = cy + radius * math.sin(end_rad)
    large_arc = 1 if (end_deg - start_deg) > 180.0 else 0
    return (
        "M {0:.2f} {1:.2f} L {2:.2f} {3:.2f} "
        "A {4:.2f} {4:.2f} 0 {5} 1 {6:.2f} {7:.2f} Z"
    ).format(cx, cy, x1, y1, radius, large_arc, x2, y2)


def build_pie_chart(series: Series) -> str:
    """生成扇形图 SVG：按比例绘制扇形，并给出图例与百分比。"""
    _check_series(series)
    total = series.total()
    if total <= 0:
        raise ValueError("扇形图要求所有数值之和大于 0")
    percentages = _pie_percentages(series.values)
    cx = _PIE_CENTER_X
    cy = _PIE_CENTER_Y
    radius = _PIE_RADIUS
    parts = _svg_head(
        "扇形图", "共 {0} 个类目，总和 {1}".format(len(series), format_number(total))
    )
    start_angle = -90.0
    for index in range(len(series)):
        percent = percentages[index]
        sweep = percent / 100.0 * 360.0
        if sweep <= 0:
            continue
        color = _COLORS[index % len(_COLORS)]
        if sweep >= 359.99:
            parts.append(
                '<circle class="slice" cx="{0:.1f}" cy="{1:.1f}" r="{2:.1f}" fill="{3}"/>'.format(
                    cx, cy, radius, color
                )
            )
            parts.append(
                _text(cx, cy, format_percent(percent), "percent", size=15, fill="#ffffff")
            )
            start_angle += sweep
            continue
        parts.append(
            '<path class="slice" d="{0}" fill="{1}" stroke="#ffffff" stroke-width="1.5"/>'.format(
                _slice_path(cx, cy, radius, start_angle, start_angle + sweep), color
            )
        )
        middle = math.radians(start_angle + sweep / 2.0)
        parts.append(
            _text(
                cx + radius * 0.6 * math.cos(middle),
                cy + radius * 0.6 * math.sin(middle) + 4.0,
                format_percent(percent),
                "percent",
                size=13,
                fill="#ffffff",
            )
        )
        start_angle += sweep
    legend_x = 392.0
    legend_y = 126.0
    parts.append(
        _text(
            legend_x,
            legend_y - 24.0,
            "图例与占比",
            "legend-title",
            anchor="start",
            size=13,
            fill="#666666",
        )
    )
    for index in range(len(series)):
        item_y = legend_y + index * 30.0
        parts.append(
            '<rect class="swatch" x="{0:.1f}" y="{1:.1f}" width="16" height="16" rx="3" fill="{2}"/>'.format(
                legend_x, item_y, _COLORS[index % len(_COLORS)]
            )
        )
        legend_text = "{0} {1}".format(
            series.labels[index], format_percent(percentages[index])
        )
        parts.append(
            _text(
                legend_x + 24.0,
                item_y + 13.0,
                legend_text,
                "legend",
                anchor="start",
                size=13,
            )
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build_chart(chart_type: str, series: Series) -> str:
    """按图表类型分发生成 SVG，未知类型抛出 ValueError。"""
    if not isinstance(chart_type, str):
        raise TypeError("图表类型必须是字符串")
    builders = {
        "bar": build_bar_chart,
        "line": build_line_chart,
        "pie": build_pie_chart,
    }
    try:
        builder = builders[chart_type]
    except KeyError as exc:
        raise ValueError("未知的图表类型: {0}".format(chart_type)) from exc
    return builder(series)
