"""dataio 模块测试：内联解析、CSV 解析、Series 校验与格式化。"""

import os
import tempfile
import unittest
from unittest import mock

from chartread.dataio import (
    Series,
    format_number,
    format_percent,
    load_csv,
    parse_csv_text,
    parse_inline,
)


class ParseInlineTests(unittest.TestCase):
    """内联数据解析。"""

    def test_basic(self) -> None:
        series = parse_inline("语文:88,数学:95,英语:79")
        self.assertEqual(series.labels, ("语文", "数学", "英语"))
        self.assertEqual(series.values, (88.0, 95.0, 79.0))

    def test_spaces_around_fields(self) -> None:
        series = parse_inline(" 语文 : 88 , 数学 : 95 ")
        self.assertEqual(series.labels, ("语文", "数学"))
        self.assertEqual(series.values, (88.0, 95.0))

    def test_fullwidth_colon(self) -> None:
        series = parse_inline("语文：88，数学：95")
        self.assertEqual(series.labels, ("语文", "数学"))
        self.assertEqual(series.values, (88.0, 95.0))

    def test_fullwidth_comma(self) -> None:
        series = parse_inline("语文:88，数学:95，英语:79")
        self.assertEqual(len(series), 3)

    def test_decimal_values(self) -> None:
        series = parse_inline("一班:12.5,二班:7.25")
        self.assertEqual(series.values, (12.5, 7.25))

    def test_missing_colon(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline("语文88,数学:95")
        self.assertIn("冒号", str(ctx.exception))

    def test_empty_label(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline(":88,数学:95")
        self.assertIn("类目不能为空", str(ctx.exception))

    def test_duplicate_label(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline("语文:88,语文:95")
        self.assertIn("类目重复", str(ctx.exception))

    def test_negative_value(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline("语文:-5,数学:95")
        self.assertIn("负数", str(ctx.exception))

    def test_non_numeric_value(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline("语文:abc,数学:95")
        self.assertIn("不是有效数字", str(ctx.exception))

    def test_bool_string_is_not_number(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline("语文:True,数学:95")
        self.assertIn("不是有效数字", str(ctx.exception))

    def test_nan_and_inf_rejected(self) -> None:
        for raw in ("nan", "inf", "-inf"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_inline("语文:{0},数学:95".format(raw))

    def test_single_item(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_inline("语文:88")
        self.assertIn("至少需要 2 个类目", str(ctx.exception))

    def test_empty_text(self) -> None:
        with self.assertRaises(ValueError):
            parse_inline("   ")

    def test_trailing_comma_is_ignored(self) -> None:
        series = parse_inline("语文:88,数学:95,")
        self.assertEqual(len(series), 2)

    def test_not_a_string(self) -> None:
        with self.assertRaises(TypeError):
            parse_inline(123)  # type: ignore[arg-type]


class SeriesTests(unittest.TestCase):
    """Series 构造校验与统计辅助方法。"""

    def setUp(self) -> None:
        self.series = Series(("语文", "数学", "英语"), (88, 95, 79))

    def test_labels_are_stripped(self) -> None:
        series = Series((" 语文 ", "数学"), (1, 2))
        self.assertEqual(series.labels, ("语文", "数学"))

    def test_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            Series(("语文", "数学"), (1,))

    def test_too_few_categories(self) -> None:
        with self.assertRaises(ValueError):
            Series(("语文",), (1,))

    def test_empty_label_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Series(("语文", "   "), (1, 2))

    def test_non_string_label_rejected(self) -> None:
        with self.assertRaises(TypeError):
            Series((1, "数学"), (1, 2))  # type: ignore[arg-type]

    def test_duplicate_label_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Series(("语文", " 语文"), (1, 2))

    def test_bool_value_rejected(self) -> None:
        with self.assertRaises(TypeError):
            Series(("语文", "数学"), (True, 2))  # type: ignore[arg-type]

    def test_string_value_rejected(self) -> None:
        with self.assertRaises(TypeError):
            Series(("语文", "数学"), ("88", 2))  # type: ignore[arg-type]

    def test_negative_value_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Series(("语文", "数学"), (-1, 2))

    def test_total_and_mean(self) -> None:
        self.assertEqual(self.series.total(), 262.0)
        self.assertAlmostEqual(self.series.mean(), 262.0 / 3.0, places=6)

    def test_maximum_and_minimum(self) -> None:
        self.assertEqual(self.series.maximum(), 95.0)
        self.assertEqual(self.series.minimum(), 79.0)
        self.assertEqual(self.series.maximum_index(), 1)
        self.assertEqual(self.series.minimum_index(), 2)

    def test_span(self) -> None:
        self.assertEqual(self.series.span(), 16.0)

    def test_percent(self) -> None:
        self.assertAlmostEqual(self.series.percent(0), 88.0 / 262.0 * 100.0, places=6)
        self.assertEqual(self.series.percent(0), self.series.percent(0))

    def test_percent_zero_total(self) -> None:
        series = Series(("语文", "数学"), (0, 0))
        self.assertEqual(series.percent(0), 0.0)

    def test_percent_index_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            self.series.percent(3)

    def test_percent_index_type(self) -> None:
        with self.assertRaises(TypeError):
            self.series.percent(True)  # type: ignore[arg-type]

    def test_items(self) -> None:
        self.assertEqual(
            self.series.items(), [("语文", 88.0), ("数学", 95.0), ("英语", 79.0)]
        )


class ParseCsvTests(unittest.TestCase):
    """CSV 文本解析。"""

    def test_chinese_header(self) -> None:
        series = parse_csv_text("名称,数值\n语文,88\n数学,95")
        self.assertEqual(series.labels, ("语文", "数学"))
        self.assertEqual(series.values, (88.0, 95.0))

    def test_english_header(self) -> None:
        series = parse_csv_text("Label,Value\n语文,88\n数学,95")
        self.assertEqual(series.labels, ("语文", "数学"))

    def test_header_case_insensitive(self) -> None:
        series = parse_csv_text("LABEL,VALUE\n语文,88\n数学,95")
        self.assertEqual(len(series), 2)

    def test_blank_lines_are_skipped(self) -> None:
        series = parse_csv_text("\n\n语文,88\n\n数学,95\n\n")
        self.assertEqual(series.labels, ("语文", "数学"))

    def test_bom_is_ignored(self) -> None:
        series = parse_csv_text("\ufeff名称,数值\n语文,88\n数学,95")
        self.assertEqual(series.labels, ("语文", "数学"))

    def test_bad_line_reports_line_number(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_csv_text("名称,数值\n语文,88\n数学,abc\n英语,95")
        message = str(ctx.exception)
        self.assertIn("第 3 行", message)
        self.assertIn("不是有效数字", message)

    def test_wrong_field_count_reports_line_number(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_csv_text("语文,88,1\n数学,95")
        message = str(ctx.exception)
        self.assertIn("第 1 行", message)
        self.assertIn("格式错误", message)

    def test_empty_label_reports_line_number(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_csv_text("语文,88\n,95")
        self.assertIn("第 2 行", str(ctx.exception))

    def test_duplicate_label_reports_line_number(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_csv_text("语文,88\n语文,95")
        self.assertIn("第 2 行", str(ctx.exception))

    def test_negative_value_reports_line_number(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_csv_text("语文,88\n数学,-3")
        message = str(ctx.exception)
        self.assertIn("第 2 行", message)
        self.assertIn("负数", message)

    def test_single_row_is_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_csv_text("语文,88")
        self.assertIn("至少需要 2 个类目", str(ctx.exception))

    def test_only_header_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_csv_text("名称,数值")

    def test_not_a_string(self) -> None:
        with self.assertRaises(TypeError):
            parse_csv_text(123)  # type: ignore[arg-type]


class LoadCsvTests(unittest.TestCase):
    """CSV 文件读取与异常提示。"""

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()

    def test_reads_utf8_file_with_bom(self) -> None:
        path = os.path.join(self.tempdir, "data.csv")
        with open(path, "w", encoding="utf-8-sig") as handle:
            handle.write("名称,数值\n语文,88\n数学,95\n")
        series = load_csv(path)
        self.assertEqual(series.labels, ("语文", "数学"))

    def test_missing_file(self) -> None:
        path = os.path.join(self.tempdir, "missing.csv")
        with self.assertRaises(ValueError) as ctx:
            load_csv(path)
        self.assertIn("文件不存在", str(ctx.exception))

    def test_directory_instead_of_file(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            load_csv(self.tempdir)
        self.assertIn("目录", str(ctx.exception))

    def test_permission_error(self) -> None:
        with mock.patch("builtins.open", side_effect=PermissionError(13, "denied")):
            with self.assertRaises(ValueError) as ctx:
                load_csv("secret.csv")
        self.assertIn("没有权限", str(ctx.exception))

    def test_invalid_utf8(self) -> None:
        path = os.path.join(self.tempdir, "broken.csv")
        with open(path, "wb") as handle:
            handle.write(b"\xff\xfe\xfa\x00")
        with self.assertRaises(ValueError) as ctx:
            load_csv(path)
        self.assertIn("UTF-8", str(ctx.exception))

    def test_generic_os_error(self) -> None:
        with mock.patch("builtins.open", side_effect=OSError(5, "io error")):
            with self.assertRaises(ValueError) as ctx:
                load_csv("broken.csv")
        self.assertIn("读取文件失败", str(ctx.exception))


class FormatTests(unittest.TestCase):
    """数值格式化。"""

    def test_format_integer(self) -> None:
        self.assertEqual(format_number(95.0), "95")
        self.assertEqual(format_number(0), "0")

    def test_format_decimal(self) -> None:
        self.assertEqual(format_number(87.5), "87.5")
        self.assertEqual(format_number(1.234), "1.23")

    def test_format_number_rejects_bool(self) -> None:
        with self.assertRaises(TypeError):
            format_number(True)  # type: ignore[arg-type]

    def test_format_number_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            format_number(float("nan"))

    def test_format_percent(self) -> None:
        self.assertEqual(format_percent(33.587), "33.6%")
        self.assertEqual(format_percent(100), "100.0%")

    def test_format_percent_rejects_inf(self) -> None:
        with self.assertRaises(ValueError):
            format_percent(float("inf"))


if __name__ == "__main__":
    unittest.main()
