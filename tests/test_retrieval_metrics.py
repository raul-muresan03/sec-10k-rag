import pytest

from eval.retrieval_metrics import score_retrieval, summarize_retrieval


def question(evidence, question_type="narrative"):
    return {"type": question_type, "evidence": evidence}


@pytest.mark.parametrize(
    ("rank", "at_five", "at_ten", "reciprocal_rank"),
    [
        (1, True, True, 1.0),
        (5, True, True, 0.2),
        (6, False, True, 1 / 6),
        (10, False, True, 0.1),
    ],
)
def test_retrieval_rank_boundaries(rank, at_five, at_ten, reciprocal_rank):
    chunks = [(0.9, "irrelevant")] * 10
    chunks[rank - 1] = (0.1, "Target\n EVIDENCE")

    score = score_retrieval(question(["target evidence"]), chunks)

    assert score == {
        "evidence_ranks": [rank],
        "hit_at_5": at_five,
        "hit_at_10": at_ten,
        "reciprocal_rank_at_10": pytest.approx(reciprocal_rank),
        "all_evidence_at_5": None,
        "all_evidence_at_10": None,
    }


def test_multiple_passages_in_one_chunk_count_as_complete_multi_hop():
    score = score_retrieval(
        question(["first passage", "SECOND passage"], "multi_hop"),
        [(0.9, "first passage; second passage")],
    )

    assert score["evidence_ranks"] == [1, 1]
    assert score["all_evidence_at_5"] is True
    assert score["all_evidence_at_10"] is True
    assert score["reciprocal_rank_at_10"] == 1.0


def test_mrr_uses_earliest_relevant_rank_not_gold_passage_order():
    chunks = [(0.9, "irrelevant")] * 10
    chunks[1] = (0.8, "second passage")
    chunks[7] = (0.2, "first passage")

    score = score_retrieval(question(["first passage", "second passage"], "multi_hop"), chunks)

    assert score["evidence_ranks"] == [8, 2]
    assert score["reciprocal_rank_at_10"] == 0.5
    assert score["all_evidence_at_5"] is False
    assert score["all_evidence_at_10"] is True


def test_multi_hop_partial_retrieval_and_no_hit():
    partial = score_retrieval(
        question(["first", "second"], "multi_hop"),
        [(0.9, "first")],
    )
    absent = score_retrieval(question(["missing"]), [(0.9, "other")])

    assert partial["evidence_ranks"] == [1, None]
    assert partial["hit_at_5"] is True
    assert partial["all_evidence_at_5"] is False
    assert partial["all_evidence_at_10"] is False
    assert absent["evidence_ranks"] == [None]
    assert absent["hit_at_10"] is False
    assert absent["reciprocal_rank_at_10"] == 0.0


def test_alternative_evidence_is_not_an_exact_match_and_no_answer_is_excluded():
    alternative = score_retrieval(question(["Revenue was $3.8 billion"]), [(0.9, "2019 | $3,782.8 million")])
    no_answer = score_retrieval(question([], "no_answer"), [(0.9, "some text")])

    assert alternative["evidence_ranks"] == [None]
    assert alternative["hit_at_5"] is False
    assert no_answer["evidence_ranks"] == []
    assert no_answer["hit_at_5"] is None
    assert no_answer["hit_at_10"] is None
    assert no_answer["reciprocal_rank_at_10"] is None


def test_rank_eleven_does_not_count_and_all_no_answer_rates_are_undefined():
    score = score_retrieval(question(["late"]), [(0.9, "other")] * 10 + [(0.1, "late")])
    summary = summarize_retrieval([(question([], "no_answer"), score_retrieval(question([], "no_answer"), []))])

    assert score["evidence_ranks"] == [None]
    assert summary["hit_at_5"] == {"hits": 0, "questions": 0, "rate": None}
    assert summary["mrr_at_10"] == {"reciprocal_rank_sum": 0, "questions": 0, "rate": None}
    assert summary["multi_hop_all_evidence_at_10"] == {"complete": 0, "questions": 0, "rate": None}


def test_summary_excludes_no_answer_and_keeps_multi_hop_denominator_separate():
    scored = [
        (question(["A"]), score_retrieval(question(["A"]), [(1.0, "A")])),
        (question(["A", "B"], "multi_hop"), score_retrieval(
            question(["A", "B"], "multi_hop"),
            [(1.0, "other")] * 5 + [(0.5, "A and B")],
        )),
        (question([], "no_answer"), score_retrieval(question([], "no_answer"), [])),
    ]

    summary = summarize_retrieval(scored)

    assert summary["hit_at_5"] == {"hits": 1, "questions": 2, "rate": 0.5}
    assert summary["hit_at_10"] == {"hits": 2, "questions": 2, "rate": 1.0}
    assert summary["mrr_at_10"] == {"reciprocal_rank_sum": pytest.approx(1 + 1 / 6), "questions": 2,
                                    "rate": pytest.approx((1 + 1 / 6) / 2)}
    assert summary["multi_hop_all_evidence_at_5"] == {"complete": 0, "questions": 1, "rate": 0.0}
    assert summary["multi_hop_all_evidence_at_10"] == {"complete": 1, "questions": 1, "rate": 1.0}
