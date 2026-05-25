"""Tests for utils.to_xml.step_compaction.compact_step_values."""
from utils.to_xml.step_compaction import compact_step_values


def test_empty_input():
    assert compact_step_values([]) == ([], 0)


def test_all_nonzero_unchanged():
    chunks = ["1:0,113,2,162", "2:5,200"]
    out, count = compact_step_values(chunks)
    assert out == chunks
    assert count == 3  # (1,0,113), (1,2,162), (2,5,200)


def test_drops_zero_pairs_within_fixture():
    chunks = ["1:0,113,2,0,5,255,7,0"]
    out, count = compact_step_values(chunks)
    assert out == ["1:0,113,5,255"]
    assert count == 2


def test_drops_fixture_when_all_zero():
    chunks = ["1:0,0,2,0", "2:5,200"]
    out, count = compact_step_values(chunks)
    assert out == ["2:5,200"]
    assert count == 1


def test_drops_all_when_step_is_all_zero():
    chunks = ["1:0,0", "2:5,0,6,0"]
    out, count = compact_step_values(chunks)
    assert out == []
    assert count == 0


def test_handles_empty_fixture_chunk():
    # Older code emits "fixtureID:" when channels_dict is empty; should be dropped.
    chunks = ["1:", "2:5,128"]
    out, count = compact_step_values(chunks)
    assert out == ["2:5,128"]
    assert count == 1


def test_preserves_channel_zero_with_nonzero_value():
    # channel=0, value=128: NOT a zero-skip target.
    chunks = ["1:0,128"]
    out, count = compact_step_values(chunks)
    assert out == ["1:0,128"]
    assert count == 1


def test_does_not_match_substring_zeros():
    # value="20" must not be skipped because it ends in "0".
    chunks = ["1:0,20,2,100,3,200"]
    out, count = compact_step_values(chunks)
    assert out == chunks
    assert count == 3


def test_drops_chunks_without_colon():
    # Defensive: malformed chunks (no ":") are dropped silently.
    chunks = ["1:0,128", "garbage", "2:5,200"]
    out, count = compact_step_values(chunks)
    assert out == ["1:0,128", "2:5,200"]
    assert count == 2


def test_realistic_step_from_profile():
    # Pulled from workspace_generated.qxw step 0 of SBD_black_and_blues_MH:
    chunks = [
        "3:0,113,2,162,5,255,7,12,8,0,9,0,10,127,11,0",
        "5:0,102,2,174,5,0,7,12,8,0,9,0,10,127,11,0",
    ]
    out, count = compact_step_values(chunks)
    # Fixture 3: keep (0,113), (2,162), (5,255), (7,12), (10,127) -> drop 8,9,11
    # Fixture 5: keep (0,102), (2,174), (7,12), (10,127) -> drop 5,8,9,11
    assert out == [
        "3:0,113,2,162,5,255,7,12,10,127",
        "5:0,102,2,174,7,12,10,127",
    ]
    assert count == 5 + 4
