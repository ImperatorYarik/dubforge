import pytest
from app.models.segment import TranscriptSegment, WordTimestamp
from app.tasks.phrase_split import split_into_phrases


def make_segment(words: list[tuple[str, float, float]]) -> TranscriptSegment:
    word_objs = [WordTimestamp(word=w, start=s, end=e) for w, s, e in words]
    text = " ".join(w for w, _, _ in words)
    start = words[0][1] if words else 0.0
    end = words[-1][2] if words else 0.0
    return TranscriptSegment(start=start, end=end, text=text, words=word_objs)


class TestSplitIntoPhrases:
    def test_returns_single_phrase_when_no_words(self):
        seg = TranscriptSegment(start=0.0, end=5.0, text="Hello world")
        result = split_into_phrases(seg)
        assert len(result) == 1
        assert result[0].text == "Hello world"

    def test_returns_single_phrase_when_no_gap(self):
        seg = make_segment([("Hello", 0.0, 0.5), ("world", 0.6, 1.0)])
        result = split_into_phrases(seg, gap_ms=400)
        assert len(result) == 1
        assert result[0].text == "Hello world"

    def test_splits_on_gap_above_threshold(self):
        seg = make_segment([
            ("Hello", 0.0, 0.5),
            ("world", 0.6, 1.0),
            ("how", 2.0, 2.3),
            ("are", 2.4, 2.6),
            ("you", 2.7, 3.0),
        ])
        result = split_into_phrases(seg, gap_ms=400)
        assert len(result) == 2
        assert result[0].text == "Hello world"
        assert result[1].text == "how are you"

    def test_single_word_phrase_from_gap_is_merged_back(self):
        # Gap of exactly 400ms produces a split, but the resulting 1-word phrase
        # ("there") is merged back into the preceding phrase by the merge step.
        seg = make_segment([
            ("Hello", 0.0, 0.5),
            ("world", 0.6, 1.0),
            ("there", 1.4, 1.8),
        ])
        result = split_into_phrases(seg, gap_ms=400)
        assert len(result) == 1
        assert "there" in result[0].text

    def test_merges_single_word_phrase_into_preceding(self):
        seg = make_segment([
            ("Hello", 0.0, 0.5),
            ("world", 0.6, 1.0),
            ("how", 2.0, 2.3),
        ])
        result = split_into_phrases(seg, gap_ms=400)
        # "how" would be a 1-word phrase, merged into "Hello world"
        assert len(result) == 1
        assert "how" in result[0].text

    def test_preserves_timing_of_phrases(self):
        seg = make_segment([
            ("Hello", 1.0, 1.5),
            ("world", 1.6, 2.0),
            ("how", 3.0, 3.3),
            ("are", 3.4, 3.6),
            ("you", 3.7, 4.0),
        ])
        result = split_into_phrases(seg, gap_ms=400)
        assert result[0].start == 1.0
        assert result[0].end == 2.0
        assert result[1].start == 3.0
        assert result[1].end == 4.0

    def test_phrase_words_are_subset_of_original(self):
        seg = make_segment([
            ("Hello", 0.0, 0.5),
            ("world", 0.6, 1.0),
            ("how", 2.0, 2.3),
            ("are", 2.4, 2.6),
            ("you", 2.7, 3.0),
        ])
        result = split_into_phrases(seg, gap_ms=400)
        first_words = [w.word for w in result[0].words]
        second_words = [w.word for w in result[1].words]
        assert first_words == ["Hello", "world"]
        assert second_words == ["how", "are", "you"]

    def test_multiple_gaps_produce_multiple_phrases(self):
        seg = make_segment([
            ("one", 0.0, 0.5),
            ("two", 0.6, 1.0),
            ("three", 2.0, 2.5),
            ("four", 2.6, 3.0),
            ("five", 4.0, 4.5),
            ("six", 4.6, 5.0),
        ])
        result = split_into_phrases(seg, gap_ms=400)
        assert len(result) == 3
