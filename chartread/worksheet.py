"""把图表与题目组装成可直接打开的 HTML 练习纸。"""

import html
from typing import List, Sequence

from chartread.charts import CHART_NAMES
from chartread.dataio import Series
from chartread.questions import Question

_STYLE = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 32px 16px 48px;
    background: #f4f6f8;
    color: #222222;
    font-family: "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", sans-serif;
    line-height: 1.7;
  }
  .page {
    max-width: 760px;
    margin: 0 auto;
    padding: 28px 32px 36px;
    background: #ffffff;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  }
  h1 { margin: 0 0 6px; font-size: 24px; }
  h2 { margin: 28px 0 12px; font-size: 18px; }
  .meta { margin: 0; color: #666666; font-size: 14px; }
  .chart { margin: 20px 0 8px; text-align: center; }
  .chart svg { max-width: 100%; height: auto; }
  ol { margin: 0; padding-left: 24px; }
  li.question { margin-bottom: 18px; }
  .prompt { margin: 0 0 6px; font-weight: 600; }
  details {
    margin-top: 4px;
    padding: 8px 12px;
    background: #f7f9fb;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 14px;
  }
  summary { cursor: pointer; color: #2f6fab; font-weight: 600; }
  .answer { margin: 8px 0 4px; }
  .explanation { margin: 0; color: #555555; }
  footer { margin-top: 32px; color: #999999; font-size: 12px; text-align: center; }
  @media print {
    body { background: #ffffff; padding: 0; }
    .page { box-shadow: none; max-width: none; }
    details { break-inside: avoid; }
  }
""".strip()


def render_worksheet(
    series: Series, questions: Sequence[Question], chart_type: str, chart_svg: str
) -> str:
    """生成完整的 HTML 练习纸，答案统一放在折叠的 details 中。"""
    if not isinstance(series, Series):
        raise TypeError("series 必须是 Series 对象")
    if not isinstance(chart_svg, str):
        raise TypeError("chart_svg 必须是字符串")
    if not isinstance(chart_type, str):
        raise TypeError("图表类型必须是字符串")
    if chart_type not in CHART_NAMES:
        raise ValueError("未知的图表类型: {0}".format(chart_type))
    if isinstance(questions, (str, bytes)):
        raise TypeError("questions 必须是题目序列")
    items = list(questions)
    if not items:
        raise ValueError("题目列表不能为空")
    for item in items:
        if not isinstance(item, Question):
            raise TypeError("questions 只能包含 Question 对象")

    title = "统计图读图练习（{0}）".format(CHART_NAMES[chart_type])
    lines: List[str] = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>{0}</title>".format(html.escape(title)),
        "<style>",
        _STYLE,
        "</style>",
        "</head>",
        "<body>",
        '<main class="page">',
        "<h1>{0}</h1>".format(html.escape(title)),
        '<p class="meta">数据：{0} · 共 {1} 题</p>'.format(
            html.escape("、".join(series.labels)), len(items)
        ),
        '<section class="chart">',
        chart_svg,
        "</section>",
        '<section class="questions">',
        "<h2>读图题</h2>",
        "<ol>",
    ]
    for item in items:
        lines.append('<li class="question">')
        lines.append('<p class="prompt">{0}</p>'.format(html.escape(item.prompt)))
        lines.append("<details><summary>参考答案</summary>")
        lines.append('<p class="answer">答案：{0}</p>'.format(html.escape(item.answer)))
        lines.append(
            '<p class="explanation">解析：{0}</p>'.format(html.escape(item.explanation))
        )
        lines.append("</details>")
        lines.append("</li>")
    lines.extend(
        [
            "</ol>",
            "</section>",
            "<footer>chartread · 统计图读图练习</footer>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(lines) + "\n"
