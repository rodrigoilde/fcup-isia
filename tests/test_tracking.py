"""Testes do acompanhamento das adjudicações: atrasos e novo recrutamento (OL6) e dispensa dos excedentes (OL8)."""

from cemr.behaviours.tracking import AwardInfo, enough_on_scene, late_awards, surplus_awards, uncovered_tasks

GO = "GO_TO_PATIENT"
FETCH = "FETCH_AED"


# --- OL6: atrasos e tarefas por cobrir ----------------------------------------------------------------
def test_an_award_is_late_only_after_arrive_by():
    awards = {"vol1": AwardInfo(GO, 60.0, arrive_by=180.0)}
    assert late_awards(awards, 180.0) == []
    assert late_awards(awards, 181.0) == ["vol1"]


def test_an_award_already_flagged_or_on_scene_is_not_late_again():
    awards = {"vol1": AwardInfo(GO, 60.0, arrive_by=180.0, late=True),
              "vol2": AwardInfo(GO, 60.0, arrive_by=180.0, on_scene_t=170.0)}
    assert late_awards(awards, 300.0) == []


def test_a_late_award_no_longer_covers_its_task():
    awards = {"vol1": AwardInfo(GO, 60.0, late=True), "vol2": AwardInfo(GO, 60.0)}
    assert uncovered_tasks({GO: 2}, awards) == {GO: 1}


def test_a_late_volunteer_who_arrived_still_covers():
    awards = {"vol1": AwardInfo(GO, 60.0, late=True, on_scene_t=200.0)}
    assert uncovered_tasks({GO: 1}, awards) == {}


def test_a_failed_award_no_longer_covers_its_task():
    awards = {"vol1": AwardInfo(FETCH, 90.0, aed_id=3, status="failed")}
    assert uncovered_tasks({FETCH: 1}, awards) == {FETCH: 1}


def test_fetch_aed_is_not_needed_once_an_aed_was_delivered():
    awards = {"vol1": AwardInfo(GO, 60.0, aed_delivered=True)}
    assert uncovered_tasks({FETCH: 1}, awards) == {}


# --- OL8: dispensa dos excedentes -----------------------------------------------------------------------
def test_surplus_is_released_only_with_n_need_on_scene():
    awards = {"vol1": AwardInfo(GO, 60.0, on_scene_t=100.0), "vol2": AwardInfo(GO, 90.0)}
    assert enough_on_scene(awards, 1)
    assert not enough_on_scene(awards, 2)


def test_volunteers_still_on_the_way_are_surplus():
    awards = {"vol1": AwardInfo(GO, 60.0, on_scene_t=100.0), "vol2": AwardInfo(GO, 90.0),
              "vol3": AwardInfo(GO, 95.0, status="failed")}
    assert surplus_awards(awards) == ["vol2"]


def test_the_aed_runner_is_kept_until_an_aed_is_delivered():
    awards = {"vol1": AwardInfo(GO, 60.0, on_scene_t=100.0), "vol2": AwardInfo(FETCH, 200.0, aed_id=3)}
    assert surplus_awards(awards) == []
    awards["vol1"].aed_delivered = True
    assert surplus_awards(awards) == ["vol2"]
