"""读图题生成：基于 ``Series`` 与随机种子生成可复现的题目。"""

import random
from dataclasses import dataclass
from typing import Callable, Dict, List

from chartread.charts import CHART_NAMES, CHART_TYPES
from chartread.dataio import Series, format_number, format_percent

QUESTION_KINDS = (
    "maximum",
    "minimum",
    "difference",
    "total",
    "percentage",
    "trend",
    "mean",
)


@dataclass(frozen=True)
class Question:
    """一道读图题：题型、题干、答案与简要解析。"""

    kind: str
    prompt: str
    answer: str
    explanation: str


def _join_labels(series: Series) -> str:
    """把类目名用顿号连接，便于题干引用。"""
    return "、".join(series.labels)


def _build_maximum(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「最大值」题目。"""
    index = series.maximum_index()
    value = series.values[index]
    prompt = "观察这幅{0}：在 {1} 中，哪一项的数据最大？最大值是多少？".format(
        CHART_NAMES[chart_type], _join_labels(series)
    )
    answer = "{0}，{1}".format(series.labels[index], format_number(value))
    detail = "、".join(
        "{0} {1}".format(label, format_number(item)) for label, item in series.items()
    )
    explanation = "逐个比较：{0}；其中 {1} 最大，对应「{2}」。".format(
        detail, format_number(value), series.labels[index]
    )
    return Question("maximum", prompt, answer, explanation)


def _build_minimum(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「最小值」题目。"""
    index = series.minimum_index()
    value = series.values[index]
    prompt = "观察这幅{0}：在 {1} 中，哪一项的数据最小？最小值是多少？".format(
        CHART_NAMES[chart_type], _join_labels(series)
    )
    answer = "{0}，{1}".format(series.labels[index], format_number(value))
    detail = "、".join(
        "{0} {1}".format(label, format_number(item)) for label, item in series.items()
    )
    explanation = "逐个比较：{0}；其中 {1} 最小，对应「{2}」。".format(
        detail, format_number(value), series.labels[index]
    )
    return Question("minimum", prompt, answer, explanation)


def _build_difference(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「两项之差」题目。"""
    count = len(series)
    first = rng.randrange(count)
    second = rng.randrange(count - 1)
    if second >= first:
        second += 1
    if series.values[second] > series.values[first]:
        first, second = second, first
    high_value = series.values[first]
    low_value = series.values[second]
    difference = high_value - low_value
    prompt = "观察这幅{0}：「{1}」比「{2}」多多少？".format(
        CHART_NAMES[chart_type], series.labels[first], series.labels[second]
    )
    answer = format_number(difference)
    explanation = "{0} - {1} = {2}。".format(
        format_number(high_value), format_number(low_value), answer
    )
    return Question("difference", prompt, answer, explanation)


def _build_total(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「总和」题目。"""
    total = series.total()
    prompt = "这幅{0}展示了 {1} 的数据，这些数据的总和是多少？".format(
        CHART_NAMES[chart_type], _join_labels(series)
    )
    answer = format_number(total)
    explanation = "{0} = {1}。".format(
        " + ".join(format_number(value) for value in series.values), answer
    )
    return Question("total", prompt, answer, explanation)


def _build_percentage(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「某项占总数的百分比」题目。"""
    index = rng.randrange(len(series))
    value = series.values[index]
    percent = series.percent(index)
    prompt = "在这幅{0}中，「{1}」的数值占全部数据的百分之几？（保留 1 位小数）".format(
        CHART_NAMES[chart_type], series.labels[index]
    )
    answer = format_percent(percent)
    if series.total() > 0:
        explanation = "{0} ÷ {1} × 100% ≈ {2}。".format(
            format_number(value), format_number(series.total()), answer
        )
    else:
        explanation = "所有数值都是 0，总和为 0，占比按 0.0% 处理。"
    return Question("percentage", prompt, answer, explanation)


def _build_trend(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「整体趋势」题目（上升/下降/持平）。"""
    first_label = series.labels[0]
    last_label = series.labels[-1]
    first_value = series.values[0]
    last_value = series.values[-1]
    if last_value > first_value:
        trend = "上升"
        reason = "末项 {0} 大于首项 {1}".format(
            format_number(last_value), format_number(first_value)
        )
    elif last_value < first_value:
        trend = "下降"
        reason = "末项 {0} 小于首项 {1}".format(
            format_number(last_value), format_number(first_value)
        )
    else:
        trend = "持平"
        reason = "末项与首项都等于 {0}".format(format_number(first_value))
    prompt = "观察这幅{0}：从第一项「{1}」到最后一项「{2}」，数据整体呈上升、下降还是持平趋势？".format(
        CHART_NAMES[chart_type], first_label, last_label
    )
    explanation = "{0}，所以呈{1}趋势。".format(reason, trend)
    return Question("trend", prompt, trend, explanation)


def _build_mean(series: Series, rng: random.Random, chart_type: str) -> Question:
    """生成「平均数」题目。"""
    answer = "{0:.1f}".format(series.mean())
    prompt = "这幅{0}共 {1} 项数据（{2}），平均数是多少？（保留 1 位小数）".format(
        CHART_NAMES[chart_type], len(series), _join_labels(series)
    )
    explanation = "总和 {0} ÷ {1} = {2}（保留 1 位小数）。".format(
        format_number(series.total()), len(series), answer
    )
    return Question("mean", prompt, answer, explanation)


_BUILDERS: Dict[str, Callable[[Series, random.Random, str], Question]] = {
    "maximum": _build_maximum,
    "minimum": _build_minimum,
    "difference": _build_difference,
    "total": _build_total,
    "percentage": _build_percentage,
    "trend": _build_trend,
    "mean": _build_mean,
}


def generate_questions(
    series: Series, chart_type: str = "bar", seed: int = 0, count: int = 8
) -> List[Question]:
    """生成 ``count`` 道读图题，题序由 ``random.Random(seed)`` 决定且可复现。"""
    if not isinstance(series, Series):
        raise TypeError("series 必须是 Series 对象")
    if not isinstance(chart_type, str):
        raise TypeError("图表类型必须是字符串")
    if chart_type not in CHART_TYPES:
        raise ValueError("未知的图表类型: {0}".format(chart_type))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed 必须是整数")
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count 必须是整数")
    if count < 1:
        raise ValueError("count 至少为 1")
    rng = random.Random(seed)
    kinds = list(QUESTION_KINDS)
    rng.shuffle(kinds)
    questions: List[Question] = []
    for position in range(count):
        kind = kinds[position % len(kinds)]
        questions.append(_BUILDERS[kind](series, rng, chart_type))
    return questions
