"""charts 模块测试：三个纯函数生成的 SVG 结构与几何。"""

import re
import unittest

from chartread.charts import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    build_bar_chart,
    build_chart,
    build_line_chart,
    build_pie_chart,
)
from chartread.dataio import Series, parse_inline


class BarChartTests(unittest.TestCase):
    """柱状图 SVG。"""

    def setUp(self) -> None:
        self.series = parse_inline("语文:88,数学:95,英语:79")
        self.svg = build_bar_chart(self.series)

    def test_has_svg_root(self) -> None:
        self.assertTrue(self.svg.startswith("<svg"))
        self.assertIn("</svg>", self.svg)

    def test_canvas_size_is_fixed(self) -> None:
        self.assertIn('width="{0}"'.format(CANVAS_WIDTH), self.svg)
        self.assertIn('height="{0}"'.format(CANVAS_HEIGHT), self.svg)
        self.assertEqual((CANVAS_WIDTH, CANVAS_HEIGHT), (640, 420))

    def test_contains_category_labels(self) -> None:
        for label in self.series.labels:
            with self.subTest(label=label):
                self.assertIn(">{0}<".format(label), self.svg)

    def test_contains_value_labels(self) -> None:
        for value in self.series.values:
            with self.subTest(value=value):
                self.assertIn(">{0}<".format(int(value)), self.svg)

    def test_has_axes_and_six_ticks(self) -> None:
        self.assertIn('class="axis"', self.svg)
        ticks = re.findall(r'<text class="tick"[^>]*>([^<]+)</text>', self.svg)
        self.assertEqual(len(ticks), 6)
        self.assertEqual(ticks[0], "0")
        self.assertEqual(ticks[-1], "100")

    def test_bar_count(self) -> None:
        rects = re.findall(r'<rect class="bar"[^>]*/>', self.svg)
        self.assertEqual(len(rects), 3)

    def test_bar_heights_are_proportional(self) -> None:
        heights = [
            float(item)
            for item in re.findall(
                r'<rect class="bar"[^>]*height="([0-9.]+)"', self.svg
            )
        ]
        self.assertEqual(len(heights), 3)
        self.assertAlmostEqual(heights[0] / heights[1], 88.0 / 95.0, places=2)
        self.assertAlmostEqual(heights[2] / heights[1], 79.0 / 95.0, places=2)

    def test_zero_values_are_allowed(self) -> None:
        svg = build_bar_chart(Series(("甲", "乙"), (0, 0)))
        heights = re.findall(r'<rect class="bar"[^>]*height="([0-9.]+)"', svg)
        self.assertEqual(heights, ["0.0", "0.0"])

    def test_special_characters_are_escaped(self) -> None:
        svg = build_bar_chart(Series(("A&B", "C<D"), (1, 2)))
        self.assertIn("A&amp;B", svg)
        self.assertIn("C&lt;D", svg)
        self.assertNotIn("C<D", svg)

    def test_rejects_non_series(self) -> None:
        with self.assertRaises(TypeError):
            build_bar_chart("语文:88,数学:95")  # type: ignore[arg-type]


class LineChartTests(unittest.TestCase):
    """折线图 SVG。"""

    def setUp(self) -> None:
        self.series = parse_inline("一月:10,二月:20,三月:30")
        self.svg = build_line_chart(self.series)

    def test_has_polyline(self) -> None:
        self.assertIn('<polyline class="line"', self.svg)

    def test_polyline_has_one_point_per_category(self) -> None:
        match = re.search(r'<polyline class="line"[^>]*points="([^"]+)"', self.svg)
        self.assertIsNotNone(match)
        assert match is not None
        pairs = match.group(1).split(" ")
        self.assertEqual(len(pairs), 3)

    def test_point_count(self) -> None:
        circles = re.findall(r'<circle class="point"', self.svg)
        self.assertEqual(len(circles), 3)

    def test_contains_labels_and_values(self) -> None:
        self.assertIn(">一月<", self.svg)
        self.assertIn(">30<", self.svg)

    def test_rising_values_go_up(self) -> None:
        match = re.search(r'<polyline class="line"[^>]*points="([^"]+)"', self.svg)
        self.assertIsNotNone(match)
        assert match is not None
        ys = [float(pair.split(",")[1]) for pair in match.group(1).split(" ")]
        self.assertGreater(ys[0], ys[1])
        self.assertGreater(ys[1], ys[2])

    def test_has_axes(self) -> None:
        self.assertIn('class="axis"', self.svg)

    def test_single_flat_series(self) -> None:
        svg = build_line_chart(Series(("甲", "乙", "丙"), (5, 5, 5)))
        match = re.search(r'<polyline class="line"[^>]*points="([^"]+)"', svg)
        self.assertIsNotNone(match)
        assert match is not None
        ys = [float(pair.split(",")[1]) for pair in match.group(1).split(" ")]
        self.assertEqual(len(set(ys)), 1)

    def test_rejects_non_series(self) -> None:
        with self.assertRaises(TypeError):
            build_line_chart(None)  # type: ignore[arg-type]


class PieChartTests(unittest.TestCase):
    """扇形图 SVG。"""

    def setUp(self) -> None:
        self.series = parse_inline("语文:88,数学:95,英语:79")
        self.svg = build_pie_chart(self.series)

    def test_has_svg_root(self) -> None:
        self.assertTrue(self.svg.startswith("<svg"))
        self.assertIn("</svg>", self.svg)

    def test_slice_path_count(self) -> None:
        paths = re.findall(r'<path class="slice"', self.svg)
        self.assertEqual(len(paths), 3)

    def test_percentages_sum_to_about_100(self) -> None:
        values = [
            float(item)
            for item in re.findall(
                r'<text class="percent"[^>]*>([0-9.]+)%</text>', self.svg
            )
        ]
        self.assertEqual(len(values), 3)
        self.assertAlmostEqual(sum(values), 100.0, places=1)

    def test_percentages_have_one_decimal(self) -> None:
        values = re.findall(r'<text class="percent"[^>]*>([0-9.]+)%</text>', self.svg)
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(len(value.split(".")[1]), 1)

    def test_legend_contains_labels(self) -> None:
        for label in self.series.labels:
            with self.subTest(label=label):
                self.assertIn(">{0} ".format(label), self.svg)

    def test_zero_total_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            build_pie_chart(Series(("甲", "乙"), (0, 0)))
        self.assertIn("大于 0", str(ctx.exception))

    def test_full_circle_for_single_positive_slice(self) -> None:
        svg = build_pie_chart(Series(("甲", "乙"), (0, 5)))
        self.assertIn('<circle class="slice"', svg)
        self.assertIn("100.0%", svg)

    def test_zero_slice_is_drawn_only_in_legend(self) -> None:
        svg = build_pie_chart(Series(("甲", "乙"), (0, 5)))
        self.assertIn("0.0%", svg)
        paths = re.findall(r'<path class="slice"', svg)
        self.assertEqual(paths, [])

    def test_rejects_non_series(self) -> None:
        with self.assertRaises(TypeError):
            build_pie_chart(42)  # type: ignore[arg-type]


class BuildChartTests(unittest.TestCase):
    """图表分发生成。"""

    def test_dispatch_bar(self) -> None:
        series = parse_inline("甲乙:1,丙丁:2")
        self.assertEqual(build_chart("bar", series), build_bar_chart(series))

    def test_dispatch_line(self) -> None:
        series = parse_inline("甲乙:1,丙丁:2")
        self.assertEqual(build_chart("line", series), build_line_chart(series))

    def test_dispatch_pie(self) -> None:
        series = parse_inline("甲乙:1,丙丁:2")
        self.assertEqual(build_chart("pie", series), build_pie_chart(series))

    def test_unknown_type(self) -> None:
        series = parse_inline("甲乙:1,丙丁:2")
        with self.assertRaises(ValueError) as ctx:
            build_chart("scatter", series)
        self.assertIn("未知的图表类型", str(ctx.exception))

    def test_non_string_type(self) -> None:
        series = parse_inline("甲乙:1,丙丁:2")
        with self.assertRaises(TypeError):
            build_chart(1, series)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
