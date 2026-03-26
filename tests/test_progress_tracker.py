"""Tests for the Progress Tracker Service."""

from uuid import uuid4

from src.models.skill import AssessmentCriteria, ChecklistItem, Skill
from src.services.progress_tracker import ProgressTrackerService


def _make_skill(
    num_areas: int = 1, items_per_area: int = 2, name: str = "Test Skill"
) -> Skill:
    """Create a Skill with the given number of areas and checklist items."""
    skill_id = uuid4()
    criteria: list[AssessmentCriteria] = []
    for i in range(num_areas):
        crit_id = uuid4()
        items = [
            ChecklistItem(
                description=f"Item {i}-{j}",
                assessment_criteria_id=crit_id,
                order_index=j,
                id=uuid4(),
            )
            for j in range(items_per_area)
        ]
        criteria.append(
            AssessmentCriteria(
                name=f"Area {i}",
                skill_id=skill_id,
                order_index=i,
                id=crit_id,
                checklist_items=items,
            )
        )
    return Skill(
        name=name,
        definition=f"Definition of {name}",
        id=skill_id,
        assessment_criteria=criteria,
    )


def _all_checklist_ids(skill: Skill) -> list[str]:
    """Return all checklist item IDs from a skill."""
    ids: list[str] = []
    for c in skill.assessment_criteria:
        for item in c.checklist_items:
            ids.append(str(item.id))
    return ids


class TestZeroProgress:
    """Progress at 0% — no items marked complete."""

    def test_percent_is_zero(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=2, items_per_area=3)
        progress = tracker.get_progress("user-1", skill)
        assert progress.percent_complete == 0.0
        assert progress.completed_checklist_items == 0
        assert progress.total_checklist_items == 6

    def test_is_not_completed(self):
        tracker = ProgressTrackerService()
        skill = _make_skill()
        assert tracker.is_skill_completed("user-1", skill) is False

    def test_all_statuses_false(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=3)
        progress = tracker.get_progress("user-1", skill)
        assert all(not s.is_completed for s in progress.checklist_status)
        assert all(s.completed_at is None for s in progress.checklist_status)


class TestPartialProgress:
    """Progress between 0% and 100%."""

    def test_partial_percent(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=4)
        ids = _all_checklist_ids(skill)
        tracker.mark_checklist_item_complete("user-1", ids[0])
        progress = tracker.get_progress("user-1", skill)
        assert progress.completed_checklist_items == 1
        assert progress.total_checklist_items == 4
        assert progress.percent_complete == 25.0
        assert progress.is_completed is False

    def test_half_complete(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=2)
        ids = _all_checklist_ids(skill)
        tracker.mark_checklist_item_complete("user-1", ids[0])
        progress = tracker.get_progress("user-1", skill)
        assert progress.percent_complete == 50.0
        assert progress.is_completed is False


class TestFullProgress:
    """Progress at 100% — all items complete."""

    def test_is_completed_true(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=2, items_per_area=2)
        for cid in _all_checklist_ids(skill):
            tracker.mark_checklist_item_complete("user-1", cid)
        progress = tracker.get_progress("user-1", skill)
        assert progress.percent_complete == 100.0
        assert progress.is_completed is True
        assert progress.completed_checklist_items == 4

    def test_is_skill_completed_returns_true(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=3)
        for cid in _all_checklist_ids(skill):
            tracker.mark_checklist_item_complete("user-1", cid)
        assert tracker.is_skill_completed("user-1", skill) is True

    def test_completed_at_is_set(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=1)
        cid = _all_checklist_ids(skill)[0]
        tracker.mark_checklist_item_complete("user-1", cid)
        progress = tracker.get_progress("user-1", skill)
        assert progress.checklist_status[0].completed_at is not None


class TestIdempotentMarking:
    """Marking an already-complete item again should be a no-op."""

    def test_double_mark_no_change(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=2)
        cid = _all_checklist_ids(skill)[0]
        tracker.mark_checklist_item_complete("user-1", cid)
        first = tracker.get_progress("user-1", skill)
        tracker.mark_checklist_item_complete("user-1", cid)
        second = tracker.get_progress("user-1", skill)
        assert first.completed_checklist_items == second.completed_checklist_items
        assert first.percent_complete == second.percent_complete

    def test_completed_at_unchanged(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=1)
        cid = _all_checklist_ids(skill)[0]
        tracker.mark_checklist_item_complete("user-1", cid)
        ts1 = tracker.get_progress("user-1", skill).checklist_status[0].completed_at
        tracker.mark_checklist_item_complete("user-1", cid)
        ts2 = tracker.get_progress("user-1", skill).checklist_status[0].completed_at
        assert ts1 == ts2


class TestPercentCalculation:
    """Verify percent_complete formula: (completed / total) * 100."""

    def test_one_of_three(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=3)
        ids = _all_checklist_ids(skill)
        tracker.mark_checklist_item_complete("user-1", ids[0])
        progress = tracker.get_progress("user-1", skill)
        expected = (1 / 3) * 100
        assert abs(progress.percent_complete - expected) < 0.01

    def test_zero_total_items(self):
        tracker = ProgressTrackerService()
        skill = Skill(name="Empty", definition="No criteria", id=uuid4())
        progress = tracker.get_progress("user-1", skill)
        assert progress.percent_complete == 0.0
        assert progress.total_checklist_items == 0
        assert progress.is_completed is False


class TestGetAllProgress:
    """get_all_progress returns progress for every skill."""

    def test_returns_all_skills(self):
        tracker = ProgressTrackerService()
        s1 = _make_skill(name="Skill A")
        s2 = _make_skill(name="Skill B")
        results = tracker.get_all_progress("user-1", [s1, s2])
        assert len(results) == 2
        assert results[0].skill_name == "Skill A"
        assert results[1].skill_name == "Skill B"


class TestChecklistStatusContent:
    """Verify checklist_status entries have correct fields."""

    def test_status_has_description_and_area(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=2, items_per_area=1)
        progress = tracker.get_progress("user-1", skill)
        assert len(progress.checklist_status) == 2
        assert progress.checklist_status[0].area_of_measurement == "Area 0"
        assert progress.checklist_status[1].area_of_measurement == "Area 1"
        assert progress.checklist_status[0].description == "Item 0-0"
        assert progress.checklist_status[1].description == "Item 1-0"


class TestUserIsolation:
    """Different users have independent progress."""

    def test_separate_users(self):
        tracker = ProgressTrackerService()
        skill = _make_skill(num_areas=1, items_per_area=2)
        ids = _all_checklist_ids(skill)
        tracker.mark_checklist_item_complete("user-a", ids[0])
        pa = tracker.get_progress("user-a", skill)
        pb = tracker.get_progress("user-b", skill)
        assert pa.completed_checklist_items == 1
        assert pb.completed_checklist_items == 0
