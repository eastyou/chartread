"""chartread 命令行入口。"""

import argparse
import sys
from typing import List, Optional, Sequence

from chartread.charts import CHART_NAMES, CHART_TYPES, build_chart
from chartread.dataio import (
    Series,
    format_number,
    format_percent,
    load_csv,
    parse_inline,
)
from chartread.questions import generate_questions
from chartread.worksheet import render_worksheet

SAMPLE_ROWS = (
    ("语文", 88),
    ("数学", 95),
    ("英语", 79),
    ("科学", 82),
    ("体育", 90),
)


def _ensure_utf8_console() -> None:
    """尽量把标准输出与标准错误切换为 UTF-8，失败时静默跳过。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            continue


def _add_data_arguments(parser: argparse.ArgumentParser) -> None:
    """为子命令添加 --data 与 --file 两个数据来源参数。"""
    parser.add_argument(
        "--data",
        metavar="TEXT",
        help='内联数据，例如 "语文:88,数学:95,英语:79"',
    )
    parser.add_argument(
        "--file",
        dest="input_file",
        metavar="PATH",
        help="CSV 文件，每行 名称,数值（UTF-8，可含表头）",
    )


def build_parser() -> argparse.ArgumentParser:
    """构建带子命令的命令行解析器。"""
    parser = argparse.ArgumentParser(
        prog="chartread",
        description="统计图读图练习工具：生成柱状图、折线图、扇形图，并自动出读图题。",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    chart_parser = subparsers.add_parser("chart", help="生成 SVG 图表")
    chart_parser.add_argument(
        "--type",
        dest="chart_type",
        required=True,
        choices=list(CHART_TYPES),
        help="图表类型：bar 柱状图 / line 折线图 / pie 扇形图",
    )
    _add_data_arguments(chart_parser)
    chart_parser.add_argument(
        "--out", required=True, metavar="PATH", help="输出 SVG 文件路径"
    )

    quiz_parser = subparsers.add_parser("quiz", help="生成 HTML 读图练习纸")
    quiz_parser.add_argument(
        "--type",
        dest="chart_type",
        required=True,
        choices=list(CHART_TYPES),
        help="图表类型：bar / line / pie",
    )
    _add_data_arguments(quiz_parser)
    quiz_parser.add_argument(
        "--seed", type=int, default=0, metavar="N", help="随机种子（默认 0）"
    )
    quiz_parser.add_argument(
        "--count", type=int, default=8, metavar="N", help="题目数量（默认 8）"
    )
    quiz_parser.add_argument(
        "--out", required=True, metavar="PATH", help="输出 HTML 文件路径"
    )

    summary_parser = subparsers.add_parser("summary", help="输出数据概况与占比表")
    _add_data_arguments(summary_parser)

    csv_parser = subparsers.add_parser("csv", help="打印数据格式示例")
    csv_parser.add_argument(
        "--rows", type=int, default=3, metavar="N", help="示例数据行数（默认 3）"
    )

    subparsers.add_parser("demo", help="打印一段用法示例")
    return parser


def _load_series(args: argparse.Namespace) -> Series:
    """根据 --data 或 --file 读取数据，二者必须且只能提供一个。"""
    has_data = args.data is not None
    has_file = args.input_file is not None
    if has_data and has_file:
        raise ValueError("--data 与 --file 只能二选一")
    if not has_data and not has_file:
        raise ValueError("请用 --data 或 --file 提供数据")
    if has_data:
        if not args.data.strip():
            raise ValueError("--data 不能为空")
        return parse_inline(args.data)
    return load_csv(args.input_file)


def _write_text(path: str, content: str) -> None:
    """以 UTF-8 写出文本文件，失败时抛出 ValueError。"""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    except OSError as exc:
        raise ValueError(
            "写入文件失败: {0} ({1})".format(path, exc.strerror or exc)
        ) from exc


def _format_summary(series: Series) -> str:
    """把数据概况与占比表格式化为多行文本。"""
    total = series.total()
    width = max(len(label) for label in series.labels)
    lines: List[str] = [
        "类目数：{0}".format(len(series)),
        "总和：{0}".format(format_number(total)),
        "平均：{0:.1f}".format(series.mean()),
        "最大值：{0}（{1}）".format(
            series.labels[series.maximum_index()], format_number(series.maximum())
        ),
        "最小值：{0}（{1}）".format(
            series.labels[series.minimum_index()], format_number(series.minimum())
        ),
        "极差：{0}".format(format_number(series.span())),
        "占比表：",
    ]
    for label, value in series.items():
        percent = 0.0 if total <= 0 else value / total * 100.0
        lines.append(
            "  {0}  {1:>6}  {2}".format(
                label.ljust(width), format_number(value), format_percent(percent)
            )
        )
    return "\n".join(lines)


def _format_csv(rows: int) -> str:
    """生成可直接保存为 CSV 的示例文本。"""
    lines = ["名称,数值"]
    for index in range(rows):
        label, value = SAMPLE_ROWS[index % len(SAMPLE_ROWS)]
        lines.append("{0},{1}".format(label, value))
    lines.append("")
    lines.append("把以上内容保存为 data.csv，再用 --file data.csv 读取。")
    return "\n".join(lines)


def _format_demo() -> str:
    """返回一段演示文本。"""
    return "\n".join(
        [
            "chartread 示例",
            "==============",
            "数据：语文:88,数学:95,英语:79",
            "",
            "1) 生成柱状图",
            '   chartread chart --type bar --data "语文:88,数学:95,英语:79" --out chart.svg',
            "2) 生成折线图",
            '   chartread chart --type line --data "语文:88,数学:95,英语:79" --out line.svg',
            "3) 生成扇形图",
            '   chartread chart --type pie --data "语文:88,数学:95,英语:79" --out pie.svg',
            "4) 生成 8 道读图题",
            '   chartread quiz --type bar --data "语文:88,数学:95,英语:79" --seed 5 --count 8 --out quiz.html',
            "5) 查看数据概况",
            '   chartread summary --data "语文:88,数学:95,英语:79"',
            "6) 查看 CSV 格式示例",
            "   chartread csv --rows 3",
        ]
    )


def _run(args: argparse.Namespace) -> int:
    """执行具体子命令，成功返回 0。"""
    command = args.command
    if command == "chart":
        series = _load_series(args)
        svg = build_chart(args.chart_type, series)
        _write_text(args.out, svg)
        print(
            "已生成{0}：{1}".format(CHART_NAMES[args.chart_type], args.out)
        )
        return 0
    if command == "quiz":
        series = _load_series(args)
        questions = generate_questions(
            series, args.chart_type, seed=args.seed, count=args.count
        )
        svg = build_chart(args.chart_type, series)
        document = render_worksheet(series, questions, args.chart_type, svg)
        _write_text(args.out, document)
        print("已生成练习纸：{0}（共 {1} 题）".format(args.out, len(questions)))
        return 0
    if command == "summary":
        series = _load_series(args)
        print(_format_summary(series))
        return 0
    if command == "csv":
        print(_format_csv(args.rows))
        return 0
    if command == "demo":
        print(_format_demo())
        return 0
    raise ValueError("未知的命令: {0}".format(command))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """命令行主入口：返回 0 表示成功，2 表示输入或写文件出错。"""
    _ensure_utf8_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "count", None) is not None and args.count < 1:
        parser.error("--count 至少为 1")
    if getattr(args, "rows", None) is not None and args.rows < 1:
        parser.error("--rows 至少为 1")
    try:
        return _run(args)
    except (TypeError, ValueError) as exc:
        print("错误：{0}".format(exc), file=sys.stderr)
        return 2
