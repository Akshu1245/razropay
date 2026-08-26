from bailiff.recoverytruth_eval import (
    ExactLookupResolver,
    KeywordTaxonomyResolver,
    evaluate_resolver,
    load_challenge,
)
from bailiff.resolver import DeterministicStateResolver


def test_unseen_state_challenge_is_frozen_nontrivial_and_unique():
    dataset_hash, cases = load_challenge()

    assert dataset_hash.startswith("sha256:")
    assert len(cases) == 24
    assert len({case.case_id for case in cases}) == 24
    assert len({case.family for case in cases}) == 24
    assert {case.gold_state.value for case in cases} >= {
        "recoverable_failure",
        "terminal_failure",
        "money_already_moved",
        "entitlement_mismatch",
        "mandate_not_actionable",
        "unknown_conflict",
    }


def test_every_baseline_is_scored_on_exactly_the_same_heldout_cases():
    _dataset_hash, cases = load_challenge()
    summaries = [
        evaluate_resolver("exact", ExactLookupResolver(), cases),
        evaluate_resolver("status", DeterministicStateResolver(), cases),
        evaluate_resolver("keyword", KeywordTaxonomyResolver(), cases),
    ]

    assert all(summary.n == 24 for summary in summaries)
    case_sets = [{row.case_id for row in summary.rows} for summary in summaries]
    assert case_sets[0] == case_sets[1] == case_sets[2]


def test_status_only_baseline_exposes_the_unsafe_high_coverage_failure_mode():
    _dataset_hash, cases = load_challenge()
    summary = evaluate_resolver("status", DeterministicStateResolver(), cases)

    assert summary.automation_coverage > 0.5
    assert summary.unsafe_recovery_rate > 0.0
    assert summary.terminal_wrong_allow_rate > 0.0
    assert summary.unknown_wrong_allow_rate > 0.0
    assert summary.dangerous_second_action_rate == 0.0  # hard provider-state preflight still protects this class


def test_exact_lookup_is_safer_but_misses_unseen_recoverable_cases():
    _dataset_hash, cases = load_challenge()
    summary = evaluate_resolver("exact", ExactLookupResolver(), cases)

    assert summary.dangerous_second_action_rate == 0.0
    assert summary.missed_recovery_rate > 0.0
    assert summary.automation_coverage < 1.0


def test_keyword_taxonomy_does_not_get_a_free_pass_on_contradictory_semantics():
    _dataset_hash, cases = load_challenge()
    summary = evaluate_resolver("keyword", KeywordTaxonomyResolver(), cases)
    row = next(row for row in summary.rows if row.case_id == "u10")

    assert row.gold_state == "unknown_conflict"
    assert row.recovery_action_allowed is False
    assert row.decision == "ABSTAIN"
