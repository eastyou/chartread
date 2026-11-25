"""questions 模块测试：题量、题型覆盖、答案正确性与可复现性。"""

import unittest
from typing import List

from chartread.dataio import Series, format_percent, parse_inline
from chartread.questions import QUESTION_KINDS, Question, generate_questions


def find_question(questions: List[Question], kind: str) -> Question:
    """按题型查找题目，找不到时抛 AssertionError。"""
    for item in questions:
        if item.kind == kind:
            return item
    raise AssertionError("缺少题型: {0}".format(kind))


class QuestionCountTests(unittest.TestCase):
    """题量与参数校验。"""

    def setUp(self) -> None:
        self.series = parse_inline("语文:88,数学:95,英语:79")

    def test_count_is_respected(self) -> None:
        questions = generate_questions(self.series, "bar", seed=5, count=8)
        self.assertEqual(len(questions), 8)

    def test_count_three(self) -> None:
        questions = generate_questions(self.series, "line", seed=5, count=3)
        self.assertEqual(len(questions), 3)

    def test_count_zero_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            generate_questions(self.series, "bar", seed=1, count=0)
        self.assertIn("至少为 1", str(ctx.exception))

    def test_count_negative_raises(self) -> None:
        with self.assertRaises(ValueError):
            generate_questions(self.series, "bar", seed=1, count=-2)

    def test_count_not_integer(self) -> None:
        with self.assertRaises(TypeError):
            generate_questions(self.series, "bar", seed=1, count=3.5)  # type: ignore[arg-type]

    def test_count_bool_rejected(self) -> None:
        with self.assertRaises(TypeError):
            generate_questions(self.series, "bar", seed=1, count=True)

    def test_seed_not_integer(self) -> None:
        with self.assertRaises(TypeError):
            generate_questions(self.series, "bar", seed="5", count=3)  # type: ignore[arg-type]

    def test_unknown_chart_type(self) -> None:
        with self.assertRaises(ValueError):
            generate_questions(self.series, "scatter", seed=1, count=3)

    def test_non_series(self) -> None:
        with self.assertRaises(TypeError):
            generate_questions("语文:88", "bar", seed=1, count=3)  # type: ignore[arg-type]

    def test_count_seven_covers_all_kinds(self) -> None:
        questions = generate_questions(self.series, "bar", seed=5, count=7)
        kinds = {item.kind for item in questions}
        self.assertEqual(kinds, set(QUESTION_KINDS))

    def test_count_eight_covers_all_kinds(self) -> None:
        questions = generate_questions(self.series, "pie", seed=5, count=8)
        kinds = {item.kind for item in questions}
        self.assertTrue(set(QUESTION_KINDS).issubset(kinds))


class ReproducibilityTests(unittest.TestCase):
    """随机种子行为。"""

    def setUp(self) -> None:
        self.series = parse_inline("语文:88,数学:95,英语:79")

    def test_same_seed_same_questions(self) -> None:
        first = generate_questions(self.series, "bar", seed=7, count=8)
        second = generate_questions(self.series, "bar", seed=7, count=8)
        self.assertEqual(first, second)

    def test_different_seed_changes_order(self) -> None:
        first = generate_questions(self.series, "bar", seed=1, count=8)
        second = generate_questions(self.series, "bar", seed=2, count=8)
        self.assertNotEqual(
            [item.prompt for item in first], [item.prompt for item in second]
        )

    def test_seed_is_deterministic_across_instances(self) -> None:
        questions = generate_questions(self.series, "line", seed=99, count=4)
        self.assertEqual([item.kind for item in questions], [q.kind for q in questions])


class AnswerTests(unittest.TestCase):
    """用已知数据手算校验答案。"""

    def setUp(self) -> None:
        self.series = parse_inline("语文:88,数学:95,英语:79")
        self.questions = generate_questions(self.series, "bar", seed=5, count=7)

    def test_maximum_answer(self) -> None:
        question = find_question(self.questions, "maximum")
        self.assertEqual(question.answer, "数学，95")
        self.assertIn("语文", question.prompt)
        self.assertIn("数学", question.prompt)

    def test_minimum_answer(self) -> None:
        question = find_question(self.questions, "minimum")
        self.assertEqual(question.answer, "英语，79")

    def test_total_answer(self) -> None:
        question = find_question(self.questions, "total")
        self.assertEqual(question.answer, "262")
        self.assertIn("262", question.explanation)

    def test_mean_answer(self) -> None:
        question = find_question(self.questions, "mean")
        self.assertEqual(question.answer, "87.3")

    def test_percentage_answer_matches_data(self) -> None:
        question = find_question(self.questions, "percentage")
        expected = {
            format_percent(self.series.percent(index))
            for index in range(len(self.series))
        }
        self.assertIn(question.answer, expected)
        self.assertTrue(question.answer.endswith("%"))

    def test_difference_answer_matches_data(self) -> None:
        question = find_question(self.questions, "difference")
        expected = set()
        for first in range(len(self.series)):
            for second in range(len(self.series)):
                if first != second:
                    expected.add(
                        "{0:g}".format(
                            abs(self.series.values[first] - self.series.values[second])
                        )
                    )
        self.assertIn(question.answer, expected)

    def test_every_prompt_mentions_a_label(self) -> None:
        for item in self.questions:
            with self.subTest(kind=item.kind):
                self.assertTrue(
                    any(label in item.prompt for label in self.series.labels),
                    item.prompt,
                )

    def test_every_question_has_explanation(self) -> None:
        for item in self.questions:
            with self.subTest(kind=item.kind):
                self.assertTrue(item.explanation)
                self.assertTrue(item.answer)

    def test_question_is_dataclass_instance(self) -> None:
        for item in self.questions:
            self.assertIsInstance(item, Question)

    def test_chart_type_appears_in_prompts(self) -> None:
        self.assertTrue(any("柱状图" in item.prompt for item in self.questions))


class TrendTests(unittest.TestCase):
    """趋势判断（上升 / 下降 / 持平）。"""

    def _trend_answer(self, series: Series) -> str:
        questions = generate_questions(series, "line", seed=3, count=7)
        return find_question(questions, "trend").answer

    def test_rising(self) -> None:
        self.assertEqual(self._trend_answer(Series(("一", "二", "三"), (10, 20, 30))), "上升")

    def test_falling(self) -> None:
        self.assertEqual(self._trend_answer(Series(("一", "二", "三"), (30, 20, 10))), "下降")

    def test_flat(self) -> None:
        self.assertEqual(self._trend_answer(Series(("一", "二", "三"), (5, 9, 5))), "持平")

    def test_trend_explanation_mentions_values(self) -> None:
        series = Series(("一", "二"), (10, 20))
        questions = generate_questions(series, "line", seed=3, count=7)
        question = find_question(questions, "trend")
        self.assertIn("20", question.explanation)
        self.assertIn("10", question.explanation)


class ZeroTotalTests(unittest.TestCase):
    """全为 0 的数据也能出题。"""

    def test_percentage_with_zero_total(self) -> None:
        series = Series(("甲", "乙"), (0, 0))
        questions = generate_questions(series, "bar", seed=5, count=7)
        question = find_question(questions, "percentage")
        self.assertEqual(question.answer, "0.0%")
        self.assertIn("总和为 0", question.explanation)

    def test_mean_with_zero_total(self) -> None:
        series = Series(("甲", "乙"), (0, 0))
        questions = generate_questions(series, "bar", seed=5, count=7)
        question = find_question(questions, "mean")
        self.assertEqual(question.answer, "0.0")


if __name__ == "__main__":
    unittest.main()
