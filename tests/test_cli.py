"""cli 模块测试：子命令返回值、输出文件与错误提示。"""

import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from html.parser import HTMLParser
from typing import List, Tuple

from chartread.cli import main

DATA = "语文:88,数学:95,英语:79"


class HtmlCounter(HTMLParser):
    """统计练习纸中的 details、summary 与转义文本。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.details = 0
        self.summaries = 0
        self.paragraphs = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        if tag == "details":
            self.details += 1
        elif tag == "summary":
            self.summaries += 1
        elif tag == "p":
            self.paragraphs += 1


def run_cli(argv: List[str]) -> Tuple[int, str, str]:
    """执行命令行并捕获标准输出、标准错误与返回码（SystemExit 也会被记录）。"""
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = 0
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = main(argv)
        except SystemExit as exc:  # argparse 的 --help 与参数错误
            code = exc.code if isinstance(exc.code, int) else 1
    return code, stdout.getvalue(), stderr.getvalue()


class ChartCommandTests(unittest.TestCase):
    """chart 子命令。"""

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()

    def _output(self, name: str) -> str:
        return os.path.join(self.tempdir, name)

    def test_bar_creates_svg(self) -> None:
        out = self._output("chart.svg")
        code, stdout, stderr = run_cli(
            ["chart", "--type", "bar", "--data", DATA, "--out", out]
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("已生成", stdout)
        with open(out, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertTrue(content.startswith("<svg"))
        self.assertIn("柱状图", content)

    def test_line_creates_svg(self) -> None:
        out = self._output("line.svg")
        code, _, stderr = run_cli(
            ["chart", "--type", "line", "--data", DATA, "--out", out]
        )
        self.assertEqual(code, 0, stderr)
        with open(out, "r", encoding="utf-8") as handle:
            self.assertIn("polyline", handle.read())

    def test_pie_creates_svg(self) -> None:
        out = self._output("pie.svg")
        code, _, stderr = run_cli(
            ["chart", "--type", "pie", "--data", DATA, "--out", out]
        )
        self.assertEqual(code, 0, stderr)
        with open(out, "r", encoding="utf-8") as handle:
            self.assertIn("扇形图", handle.read())

    def test_reads_csv_file(self) -> None:
        csv_path = self._output("data.csv")
        with open(csv_path, "w", encoding="utf-8") as handle:
            handle.write("名称,数值\n语文,88\n数学,95\n")
        out = self._output("from_csv.svg")
        code, _, stderr = run_cli(
            ["chart", "--type", "bar", "--file", csv_path, "--out", out]
        )
        self.assertEqual(code, 0, stderr)
        self.assertTrue(os.path.exists(out))

    def test_missing_data_source(self) -> None:
        out = self._output("none.svg")
        code, _, stderr = run_cli(["chart", "--type", "bar", "--out", out])
        self.assertEqual(code, 2)
        self.assertIn("错误：", stderr)
        self.assertIn("--data", stderr)

    def test_both_data_sources(self) -> None:
        out = self._output("both.svg")
        code, _, stderr = run_cli(
            [
                "chart",
                "--type",
                "bar",
                "--data",
                DATA,
                "--file",
                "data.csv",
                "--out",
                out,
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("二选一", stderr)

    def test_invalid_data_returns_two(self) -> None:
        out = self._output("bad.svg")
        code, _, stderr = run_cli(
            ["chart", "--type", "bar", "--data", "语文:-3,数学:95", "--out", out]
        )
        self.assertEqual(code, 2)
        self.assertIn("负数", stderr)
        self.assertFalse(os.path.exists(out))

    def test_missing_csv_file_returns_two(self) -> None:
        out = self._output("missing.svg")
        code, _, stderr = run_cli(
            [
                "chart",
                "--type",
                "bar",
                "--file",
                self._output("nope.csv"),
                "--out",
                out,
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("文件不存在", stderr)

    def test_unwritable_output_returns_two(self) -> None:
        code, _, stderr = run_cli(
            ["chart", "--type", "bar", "--data", DATA, "--out", self.tempdir]
        )
        self.assertEqual(code, 2)
        self.assertIn("写入文件失败", stderr)

    def test_unknown_type_exits(self) -> None:
        out = self._output("unknown.svg")
        code, _, stderr = run_cli(
            ["chart", "--type", "scatter", "--data", DATA, "--out", out]
        )
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", stderr)

    def test_pie_zero_total_returns_two(self) -> None:
        out = self._output("zero.svg")
        code, _, stderr = run_cli(
            ["chart", "--type", "pie", "--data", "语文:0,数学:0", "--out", out]
        )
        self.assertEqual(code, 2)
        self.assertIn("大于 0", stderr)


class SummaryCommandTests(unittest.TestCase):
    """summary 子命令。"""

    def test_summary_output(self) -> None:
        code, stdout, stderr = run_cli(["summary", "--data", DATA])
        self.assertEqual(code, 0, stderr)
        self.assertIn("类目数：3", stdout)
        self.assertIn("总和：262", stdout)
        self.assertIn("极差：16", stdout)

    def test_summary_mean_and_extremes(self) -> None:
        code, stdout, _ = run_cli(["summary", "--data", DATA])
        self.assertEqual(code, 0)
        self.assertIn("平均：87.3", stdout)
        self.assertIn("最大值：数学（95）", stdout)
        self.assertIn("最小值：英语（79）", stdout)

    def test_summary_percentage_table(self) -> None:
        code, stdout, _ = run_cli(["summary", "--data", DATA])
        self.assertEqual(code, 0)
        self.assertIn("占比表：", stdout)
        self.assertIn("33.6%", stdout)

    def test_summary_zero_total(self) -> None:
        code, stdout, _ = run_cli(["summary", "--data", "甲:0,乙:0"])
        self.assertEqual(code, 0)
        self.assertIn("0.0%", stdout)


class QuizCommandTests(unittest.TestCase):
    """quiz 子命令。"""

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()

    def test_creates_html_with_details(self) -> None:
        out = os.path.join(self.tempdir, "quiz.html")
        code, stdout, stderr = run_cli(
            [
                "quiz",
                "--type",
                "bar",
                "--data",
                DATA,
                "--seed",
                "5",
                "--count",
                "8",
                "--out",
                out,
            ]
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("8 题", stdout)
        with open(out, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertEqual(
            content.count("<details><summary>参考答案</summary>"), 8
        )
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<svg", content)
        self.assertIn("语文", content)

    def test_html_is_parseable(self) -> None:
        out = os.path.join(self.tempdir, "parsed.html")
        code, _, stderr = run_cli(
            [
                "quiz",
                "--type",
                "pie",
                "--data",
                DATA,
                "--seed",
                "2",
                "--count",
                "5",
                "--out",
                out,
            ]
        )
        self.assertEqual(code, 0, stderr)
        with open(out, "r", encoding="utf-8") as handle:
            content = handle.read()
        counter = HtmlCounter()
        counter.feed(content)
        counter.close()
        self.assertEqual(counter.details, 5)
        self.assertEqual(counter.summaries, 5)
        self.assertGreaterEqual(counter.paragraphs, 10)

    def test_seed_reproducible(self) -> None:
        first = os.path.join(self.tempdir, "a.html")
        second = os.path.join(self.tempdir, "b.html")
        arguments = [
            "quiz",
            "--type",
            "line",
            "--data",
            DATA,
            "--seed",
            "11",
            "--count",
            "6",
            "--out",
        ]
        self.assertEqual(run_cli(arguments + [first])[0], 0)
        self.assertEqual(run_cli(arguments + [second])[0], 0)
        with open(first, "r", encoding="utf-8") as handle:
            first_text = handle.read()
        with open(second, "r", encoding="utf-8") as handle:
            second_text = handle.read()
        self.assertEqual(first_text, second_text)

    def test_special_characters_are_escaped(self) -> None:
        out = os.path.join(self.tempdir, "escape.html")
        code, _, stderr = run_cli(
            [
                "quiz",
                "--type",
                "pie",
                "--data",
                "A&B:5,C<D:7",
                "--seed",
                "1",
                "--count",
                "3",
                "--out",
                out,
            ]
        )
        self.assertEqual(code, 0, stderr)
        with open(out, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("A&amp;B", content)
        self.assertIn("C&lt;D", content)
        self.assertNotIn("C<D", content)

    def test_count_zero_exits(self) -> None:
        out = os.path.join(self.tempdir, "zero.html")
        code, _, stderr = run_cli(
            [
                "quiz",
                "--type",
                "bar",
                "--data",
                DATA,
                "--count",
                "0",
                "--out",
                out,
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("--count", stderr)
        self.assertFalse(os.path.exists(out))


class CsvAndDemoTests(unittest.TestCase):
    """csv 与 demo 子命令。"""

    def test_csv_default_rows(self) -> None:
        code, stdout, _ = run_cli(["csv"])
        self.assertEqual(code, 0)
        rows = re.findall(r"^[^\s,]+,[^\s,]+$", stdout, flags=re.MULTILINE)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0], "名称,数值")

    def test_csv_custom_rows(self) -> None:
        code, stdout, _ = run_cli(["csv", "--rows", "5"])
        self.assertEqual(code, 0)
        rows = re.findall(r"^[^\s,]+,[^\s,]+$", stdout, flags=re.MULTILINE)
        self.assertEqual(len(rows), 6)

    def test_csv_zero_rows_exits(self) -> None:
        code, _, stderr = run_cli(["csv", "--rows", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--rows", stderr)

    def test_demo_prints_usage(self) -> None:
        code, stdout, _ = run_cli(["demo"])
        self.assertEqual(code, 0)
        self.assertIn("chartread chart", stdout)
        self.assertIn("chartread quiz", stdout)

    def test_demo_mentions_csv(self) -> None:
        code, stdout, _ = run_cli(["demo"])
        self.assertEqual(code, 0)
        self.assertIn("chartread summary", stdout)


class GeneralTests(unittest.TestCase):
    """帮助信息与缺少子命令。"""

    def test_help_exits_zero(self) -> None:
        code, stdout, _ = run_cli(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("usage", stdout.lower())
        self.assertIn("chartread", stdout)

    def test_no_command_exits(self) -> None:
        code, _, stderr = run_cli([])
        self.assertEqual(code, 2)
        self.assertTrue(stderr)

    def test_subcommand_help(self) -> None:
        code, stdout, _ = run_cli(["chart", "--help"])
        self.assertEqual(code, 0)
        self.assertIn("--out", stdout)


if __name__ == "__main__":
    unittest.main()
