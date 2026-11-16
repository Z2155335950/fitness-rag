from __future__ import annotations

import unittest

from src.query.pipeline import QueryPipeline


class QueryPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = QueryPipeline()

    def test_action_group_route(self) -> None:
        routed = self.pipeline.process("深蹲怎么做")
        self.assertEqual(routed.intent.value, "action_detail")

    def test_muscle_with_generic_action_word(self) -> None:
        routed = self.pipeline.process("三角肌后束的动作")
        self.assertEqual(routed.intent.value, "muscle_to_actions")

    def test_body_part_alias_is_group(self) -> None:
        routed = self.pipeline.process("背怎么练")
        self.assertEqual(routed.intent.value, "muscle_to_actions")
        self.assertEqual(routed.entities[0].type.value, "muscle_group")

    def test_negative_equipment_filter(self) -> None:
        routed = self.pipeline.process("没器械怎么练背")
        self.assertIn("equipment_exclude", routed.filters)
        self.assertTrue(routed.filters["prefer_bodyweight"])

    def test_home_with_equipment_is_positive(self) -> None:
        routed = self.pipeline.process("家里有哑铃怎么练胸")
        self.assertEqual(
            routed.filters.get("equipment_include"), ["哑铃"]
        )
        self.assertNotIn("equipment_exclude", routed.filters)

    def test_injury_question_is_semantic(self) -> None:
        routed = self.pipeline.process("深蹲伤膝盖吗")
        self.assertEqual(routed.intent.value, "semantic")

    def test_new_action_and_alias_resolution(self) -> None:
        routed = self.pipeline.process("器械推胸（坐姿固定器械）")
        self.assertEqual(routed.entities[0].canonical, "坐姿器械推胸")
        self.assertEqual(
            routed.entities[0].ids, ["action_坐姿器械推胸"]
        )

    def test_technique_variation_maps_to_parent_action(self) -> None:
        routed = self.pipeline.process("停顿卧推（底位暂停卧推）")
        self.assertEqual(routed.entities[0].canonical, "平板杠铃卧推")
        self.assertEqual(
            routed.entities[0].ids, ["action_平板杠铃卧推"]
        )

    def test_field_query_detection(self) -> None:
        errors = self.pipeline.process("平板卧推常见错误有哪些")
        self.assertEqual(errors.filters.get("fields"), ["errors"])

        tips = self.pipeline.process("深蹲训练节奏怎么安排")
        self.assertEqual(tips.filters.get("fields"), ["tips"])


if __name__ == "__main__":
    unittest.main()
