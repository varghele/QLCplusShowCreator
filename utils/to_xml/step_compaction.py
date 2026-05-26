"""Zero-skip compaction for QLC+ Sequence step values.

QLC+'s own saver (engine/src/chaserstep.cpp::saveXML, line 293) skips
channels whose value is 0 when writing a sequence step:

    foreach (SceneValue scv, values)
    {
        // save non-zero values only
        if (scv.value != 0)
            ...
    }

The loader (chaserstep.cpp:209-237) does not pre-populate the step's value
list, so an absent channel ends up with value 0 in the resulting scene.
Skipping zero-valued channels is therefore byte-identical playback.

Profiling a representative export found 44.1% of all (fixture, channel,
value) triples were zero-valued, accounting for roughly 30% of file size.

A step's values list serializes as:
    "fixtureID:channel,value,channel,value:fixtureID:channel,value,..."

`compact_step_values` parses that list-of-fixture-chunks and drops every
",0" pair, plus any fixture whose chunk becomes empty.
"""
from __future__ import annotations
from typing import List, Tuple


def compact_step_values(fixture_chunks: List[str]) -> Tuple[List[str], int]:
    """Drop zero-valued channels (and now-empty fixture chunks) from a step.

    Args:
        fixture_chunks: list of `"fixtureID:channel,value,channel,value"`
                        strings (one per fixture). May include empty
                        `"fixtureID:"` chunks; those are dropped.

    Returns:
        (compacted_chunks, total_nonzero_pairs)
            compacted_chunks: input minus zero-valued pairs and empty fixtures
            total_nonzero_pairs: count of surviving (channel, value) pairs,
                                 suitable for the `<Step Values="...">` attr.
    """
    compacted: List[str] = []
    total_pairs = 0
    for chunk in fixture_chunks:
        if ":" not in chunk:
            continue
        fixture_part, _, pair_part = chunk.partition(":")
        if not pair_part:
            continue
        tokens = pair_part.split(",")
        # tokens alternate ch, val, ch, val, ...; drop pairs where val == "0"
        surviving: List[str] = []
        i = 0
        while i + 1 < len(tokens):
            ch_tok, val_tok = tokens[i], tokens[i + 1]
            if val_tok != "0":
                surviving.append(ch_tok)
                surviving.append(val_tok)
            i += 2
        if surviving:
            compacted.append(f"{fixture_part}:{','.join(surviving)}")
            total_pairs += len(surviving) // 2
    return compacted, total_pairs
