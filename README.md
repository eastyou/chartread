# chartread

[![CI](https://github.com/eastyou/chartread/actions/workflows/ci.yml/badge.svg)](https://github.com/eastyou/chartread/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-brightgreen.svg)](pyproject.toml)

面向小学与初中的「统计图读图」练习工具：输入一组数据，即可生成柱状图、折线图、扇形图的 SVG，并自动出一套带参考答案的读图题练习纸。纯标准库实现，无需联网。

## 特性

- 三种图表：柱状图（坐标轴、刻度、数值标签）、折线图（折线、数据点、坐标轴）、扇形图（按比例扇形、图例、百分比）。
- 自动出题：最大值、最小值、两项之差、总和、某项占比、整体趋势、平均数，共 7 种题型，题面引用真实类目名。
- 答案折叠：练习纸中每道题的参考答案与计算式都放在 `<details>` 里，方便先练习后核对。
- 数据来源：命令行内联文本或 UTF-8 CSV 文件，输入经过严格校验并给出中文错误提示。
- 可复现：同一 `--seed` 生成的题目顺序与内容完全一致，便于批量打印。
- 可编程：`build_bar_chart` 等均为纯函数，直接返回 SVG 字符串，便于在测试或其他脚本中复用。

## 安装

```bash
pip install -e .
```

也可以不安装，直接在仓库根目录用模块方式运行：

```bash
python -m chartread --help
```

## 使用

### 生成图表

```bash
chartread chart --type bar --data "语文:88,数学:95,英语:79" --out chart.svg
```

输出：

```
已生成柱状图：chart.svg
```

把 `--type` 换成 `line` 或 `pie`，即可得到折线图与扇形图：

```bash
chartread chart --type line --data "语文:88,数学:95,英语:79" --out line.svg
chartread chart --type pie  --data "语文:88,数学:95,英语:79" --out pie.svg
```

画布固定为 640×420，扇形图的三块占比为 33.6%、36.2%、30.2%，合计 100.0%。

### 生成读图题练习纸

```bash
chartread quiz --type bar --data "语文:88,数学:95,英语:79" --seed 5 --count 8 --out quiz.html
```

输出：

```
已生成练习纸：quiz.html（共 8 题）
```

生成的 HTML 中同时嵌入图表与题目，答案折叠显示。题面示例（`--seed 5`）：

```
这幅柱状图共 3 项数据（语文、数学、英语），平均数是多少？（保留 1 位小数）
答案：87.3

这幅柱状图展示了 语文、数学、英语 的数据，这些数据的总和是多少？
答案：262

观察这幅柱状图：在 语文、数学、英语 中，哪一项的数据最小？最小值是多少？
答案：英语，79
```

### 查看数据概况

```bash
chartread summary --data "语文:88,数学:95,英语:79"
```

输出：

```
类目数：3
总和：262
平均：87.3
最大值：数学（95）
最小值：英语（79）
极差：16
占比表：
  语文      88  33.6%
  数学      95  36.3%
  英语      79  30.2%
```

### 从 CSV 读取

`--data` 与 `--file` 只能二选一。CSV 每行写 `名称,数值`，首行表头 `名称,数值` 或 `label,value` 可省略，空行会被忽略：

```
名称,数值
语文,88
数学,95
英语,79
```

```bash
chartread chart --type line --file data.csv --out line.svg
```

### 打印 CSV 示例

```bash
chartread csv --rows 3
```

输出：

```
名称,数值
语文,88
数学,95
英语,79

把以上内容保存为 data.csv，再用 --file data.csv 读取。
```

### 查看用法示例

```bash
chartread demo
```

会打印一组可直接复制的命令，覆盖三种图表、出题、概况与 CSV 示例。

## 参数表

| 子命令 | 参数 | 说明 |
| --- | --- | --- |
| `chart` | `--type bar\|line\|pie` | 必选，图表类型 |
| `chart` | `--data TEXT` / `--file PATH` | 二选一，数据来源 |
| `chart` | `--out PATH` | 必选，SVG 输出路径 |
| `quiz` | `--type bar\|line\|pie` | 必选，图表类型 |
| `quiz` | `--data TEXT` / `--file PATH` | 二选一，数据来源 |
| `quiz` | `--seed N` | 随机种子，默认 0，相同种子结果一致 |
| `quiz` | `--count N` | 题目数量，默认 8，至少 1 |
| `quiz` | `--out PATH` | 必选，HTML 输出路径 |
| `summary` | `--data TEXT` / `--file PATH` | 二选一，数据来源 |
| `csv` | `--rows N` | 示例数据行数，默认 3，至少 1 |
| `demo` | 无 | 打印用法示例 |

数据约束：至少 2 个类目；类目去空格后非空且唯一；数值为非负数字（`True`/`False` 不算数字）；扇形图要求数值总和大于 0。出现错误时命令返回码为 2，并在标准错误输出 `错误：...`。

## 作为库使用

```python
from chartread.charts import build_bar_chart
from chartread.dataio import parse_inline
from chartread.questions import generate_questions

series = parse_inline("语文:88,数学:95,英语:79")
svg = build_bar_chart(series)
questions = generate_questions(series, "bar", seed=5, count=8)
print(len(svg))
print(questions[0].prompt)
```

输出：

```
2655
这幅柱状图共 3 项数据（语文、数学、英语），平均数是多少？（保留 1 位小数）
```

## 开发与测试

项目仅使用标准库，支持 Python 3.9 及以上版本。

```bash
python -m unittest discover -s tests -v
```

共 148 个测试，覆盖数据解析、SVG 结构、题目答案与命令行行为。CI 会在 Python 3.9 至 3.13 上运行同一套测试，并执行 `python -m chartread --help` 冒烟检查。

## License

[MIT](LICENSE) © 2026 eastyou
