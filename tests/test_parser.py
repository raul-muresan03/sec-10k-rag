import pytest

from tests.support import NVIDIA_PARSED_10K

from etl_pipeline.parser import parse_10K


def test_parse_10k_extracts_first_document_body(data_directory):
    submission = """submission header
<DOCUMENT>
<TYPE>10-K
<TEXT>annual report</TEXT>
</DOCUMENT>
<DOCUMENT>
<TYPE>EX-99
<TEXT>exhibit</TEXT>
</DOCUMENT>
"""
    source = data_directory / "submission.txt"
    source.write_text(submission)

    result = parse_10K(str(source))
    parsed = (data_directory / "output_parser.txt").read_text()

    assert result is None
    assert "<TYPE>10-K" in parsed
    assert "annual report" in parsed
    assert "<DOCUMENT>" not in parsed
    assert "</DOCUMENT>" not in parsed
    assert "EX-99" not in parsed
    assert "exhibit" not in parsed


def test_parsed_nvidia_fixture_has_expected_10k_structure():
    parsed = NVIDIA_PARSED_10K.read_text()

    assert "<TYPE>10-K" in parsed
    assert "<FILENAME>nvda-20260125.htm" in parsed
    assert parsed.count("<TEXT>") == 1
    assert parsed.count("</TEXT>") == 1
    assert "Item 1A" in parsed
    assert parsed.rstrip().endswith("</TEXT>")


def test_parse_10k_requires_a_document_block(data_directory):
    source = data_directory / "invalid-submission.txt"
    source.write_text("submission without a DOCUMENT block")

    with pytest.raises(ValueError, match="No document block found"):
        parse_10K(str(source))

    assert not (data_directory / "output_parser.txt").exists()
