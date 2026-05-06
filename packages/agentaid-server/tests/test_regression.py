from agentaid_server.orchestrator.regression import score_against_expected

def test_score_against_expected_rewards_overlap() -> None:
    expected = {"expected_paper_ids": ["2401.00001", "2402.00012"],
                "expected_themes": ["concept drift", "Hoeffding bound"]}
    actual_digest = "## 2401.00001\nNotes about concept drift and Hoeffding bound."
    actual_papers = ["2401.00001"]
    s = score_against_expected(expected, actual_digest, actual_papers)
    assert 0.0 <= s.recall_paper_ids <= 1.0
    assert 0.0 <= s.theme_coverage <= 1.0
    assert s.recall_paper_ids == 0.5

def test_score_against_expected_zero_when_no_overlap() -> None:
    s = score_against_expected({"expected_paper_ids": ["x"], "expected_themes": ["y"]},
                               "completely off-topic", [])
    assert s.recall_paper_ids == 0.0
    assert s.theme_coverage == 0.0
