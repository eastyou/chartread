"""数据读取与校验：把内联文本或 CSV 文本转换成 ``Series``。"""

import math
from dataclasses import dataclass
from typing import List, Tuple

_HEADER_LABELS = ("名称", "label")
_HEADER_VALUES = ("数值", "value")
_SEPARATORS = (":", "：")


def format_number(value: float) -> str:
    """把数值格式化为便于展示的字符串：整数不带小数点，最多保留两位小数。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("数值必须是 int 或 float")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("数值必须是有限数字")
    rounded = round(number, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    text = "{0:.2f}".format(rounded).rstrip("0").rstrip(".")
    return text


def format_percent(value: float) -> str:
    """把数值格式化为保留 1 位小数的百分比字符串。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("百分比必须是 int 或 float")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("百分比必须是有限数字")
    return "{0:.1f}%".format(number)


@dataclass(frozen=True)
class Series:
    """一组「类目 + 数值」数据，构造时完成合法性校验。

    约束：至少 2 个类目；类目非空且唯一；数值为非负有限数字（bool 不算数字）。
    """

    labels: Tuple[str, ...]
    values: Tuple[float, ...]

    def __post_init__(self) -> None:
        labels = tuple(self.labels)
        values = tuple(self.values)
        if len(labels) != len(values):
            raise ValueError("类目数量与数值数量不一致")
        if len(labels) < 2:
            raise ValueError("至少需要 2 个类目")
        seen = set()
        clean_labels: List[str] = []
        for label in labels:
            if not isinstance(label, str):
                raise TypeError("类目必须是字符串")
            name = label.strip()
            if not name:
                raise ValueError("类目不能为空")
            if name in seen:
                raise ValueError("类目重复: {0}".format(name))
            seen.add(name)
            clean_labels.append(name)
        clean_values: List[float] = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError("数值必须是 int 或 float")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("数值必须是有限数字")
            if number < 0:
                raise ValueError("数值不能为负数: {0}".format(format_number(number)))
            clean_values.append(number)
        object.__setattr__(self, "labels", tuple(clean_labels))
        object.__setattr__(self, "values", tuple(clean_values))

    def __len__(self) -> int:
        """返回类目数量。"""
        return len(self.labels)

    def items(self) -> List[Tuple[str, float]]:
        """返回 (类目, 数值) 列表，便于遍历。"""
        return list(zip(self.labels, self.values))

    def total(self) -> float:
        """返回所有数值之和。"""
        return float(sum(self.values))

    def mean(self) -> float:
        """返回算术平均数。"""
        return self.total() / len(self.values)

    def maximum(self) -> float:
        """返回最大值。"""
        return max(self.values)

    def minimum(self) -> float:
        """返回最小值。"""
        return min(self.values)

    def maximum_index(self) -> int:
        """返回最大值首次出现的下标。"""
        best = 0
        for index in range(1, len(self.values)):
            if self.values[index] > self.values[best]:
                best = index
        return best

    def minimum_index(self) -> int:
        """返回最小值首次出现的下标。"""
        best = 0
        for index in range(1, len(self.values)):
            if self.values[index] < self.values[best]:
                best = index
        return best

    def span(self) -> float:
        """返回极差（最大值减最小值）。"""
        return self.maximum() - self.minimum()

    def percent(self, index: int) -> float:
        """返回第 index 项占总和的百分比，总和为 0 时返回 0.0。"""
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("索引必须是整数")
        if index < 0 or index >= len(self.values):
            raise ValueError("索引超出范围: {0}".format(index))
        total = self.total()
        if total <= 0:
            return 0.0
        return self.values[index] / total * 100.0


def _split_pair(item: str, position: int) -> Tuple[str, str]:
    """按第一个冒号把一项拆成 (类目, 数值文本)。"""
    for separator in _SEPARATORS:
        if separator in item:
            label, _, value_text = item.partition(separator)
            return label.strip(), value_text.strip()
    raise ValueError("第 {0} 项缺少冒号: {1}".format(position, item))


def _parse_number(raw: str, where: str) -> float:
    """把数值文本转换为非负有限浮点数，非法时抛出 ValueError。"""
    text = raw.strip()
    if not text:
        raise ValueError("{0}数值不能为空".format(where))
    try:
        number = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("{0}数值不是有效数字: {1}".format(where, text)) from exc
    if not math.isfinite(number):
        raise ValueError("{0}数值必须是有限数字: {1}".format(where, text))
    if number < 0:
        raise ValueError("{0}数值不能为负数: {1}".format(where, text))
    return number


def parse_inline(text: str) -> Series:
    """解析 ``名称:数值,名称:数值`` 形式的内联数据，支持全角冒号与全角逗号。"""
    if not isinstance(text, str):
        raise TypeError("内联数据必须是字符串")
    normalized = text.replace("，", ",")
    labels: List[str] = []
    values: List[float] = []
    position = 0
    for chunk in normalized.split(","):
        item = chunk.strip()
        if not item:
            continue
        position += 1
        label, value_text = _split_pair(item, position)
        if not label:
            raise ValueError("第 {0} 项类目不能为空".format(position))
        if label in labels:
            raise ValueError("第 {0} 项类目重复: {1}".format(position, label))
        values.append(_parse_number(value_text, "第 {0} 项".format(position)))
        labels.append(label)
    return Series(tuple(labels), tuple(values))


def _is_header(fields: List[str]) -> bool:
    """判断一行是否为表头（名称,数值 或 label,value）。"""
    if len(fields) != 2:
        return False
    return (
        fields[0].strip().lower() in _HEADER_LABELS
        and fields[1].strip().lower() in _HEADER_VALUES
    )


def parse_csv_text(text: str) -> Series:
    """解析 CSV 文本：每行 ``名称,数值``，允许首行表头、空行与 UTF-8 BOM。"""
    if not isinstance(text, str):
        raise TypeError("CSV 文本必须是字符串")
    if text.startswith("\ufeff"):
        text = text[1:]
    labels: List[str] = []
    values: List[float] = []
    first_row = True
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        fields = [field.strip() for field in line.replace("，", ",").split(",")]
        if first_row:
            first_row = False
            if _is_header(fields):
                continue
        if len(fields) != 2:
            raise ValueError(
                "第 {0} 行格式错误：应为 名称,数值".format(line_number)
            )
        label, value_text = fields
        if not label:
            raise ValueError("第 {0} 行类目不能为空".format(line_number))
        if label in labels:
            raise ValueError("第 {0} 行类目重复: {1}".format(line_number, label))
        values.append(_parse_number(value_text, "第 {0} 行".format(line_number)))
        labels.append(label)
    if not labels:
        raise ValueError("CSV 中没有有效数据行")
    return Series(tuple(labels), tuple(values))


def load_csv(path: str) -> Series:
    """读取 UTF-8（允许 BOM）的 CSV 文件并解析为 ``Series``。"""
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            content = handle.read()
    except FileNotFoundError as exc:
        raise ValueError("文件不存在: {0}".format(path)) from exc
    except IsADirectoryError as exc:
        raise ValueError("这是一个目录，不是文件: {0}".format(path)) from exc
    except PermissionError as exc:
        raise ValueError("没有权限读取: {0}".format(path)) from exc
    except UnicodeDecodeError as exc:
        raise ValueError("文件不是有效的 UTF-8 文本: {0}".format(path)) from exc
    except OSError as exc:
        raise ValueError(
            "读取文件失败: {0} ({1})".format(path, exc.strerror or exc)
        ) from exc
    return parse_csv_text(content)
