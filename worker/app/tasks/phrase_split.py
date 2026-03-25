from app.models.segment import TranscriptSegment, WordTimestamp


def split_into_phrases(segment: TranscriptSegment, gap_ms: float = 400) -> list[TranscriptSegment]:
    """
    Split a segment into sub-segments (phrases) wherever the gap between consecutive
    words exceeds `gap_ms` milliseconds.

    Falls back to a single phrase (the original segment) when word timestamps are absent.
    Very short phrases (< 2 words) are merged with the preceding phrase to avoid
    XTTS v2 synthesis failures on single-word inputs.
    """
    if not segment.words:
        return [segment]

    gap_s = gap_ms / 1000.0
    phrases: list[list[WordTimestamp]] = [[segment.words[0]]]

    for prev, curr in zip(segment.words, segment.words[1:]):
        if (curr.start - prev.end) >= gap_s:
            phrases.append([])
        phrases[-1].append(curr)

    # Merge phrases that are too short (< 2 words) into the preceding phrase.
    merged: list[list[WordTimestamp]] = []
    for phrase in phrases:
        if len(phrase) < 2 and merged:
            merged[-1].extend(phrase)
        else:
            merged.append(phrase)

    result = []
    for words in merged:
        text = " ".join(w.word.strip() for w in words).strip()
        result.append(TranscriptSegment(
            start=words[0].start,
            end=words[-1].end,
            text=text,
            words=words,
        ))
    return result
