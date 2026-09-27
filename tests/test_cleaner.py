import pytest

from tests.support import NVIDIA_PARSED_10K

from etl_pipeline.cleaner import clean_10K


def test_clean_10k_removes_hidden_markup_and_converts_tables(data_directory):
    parsed_document = (
        "<TEXT><html><body>"
        '<div><div>Visible text <span style="display: none">secret</span><img src="x"/>'
        "<ix:nonnumeric>Revenue</ix:nonnumeric></div></div>"
        "<div><table><tr><th>Year</th><th>Revenue</th></tr>"
        "<tr><td>2026</td><td>$ 10</td></tr></table></div>"
        "</body></html></TEXT>"
    )
    source = data_directory / "parsed.txt"
    source.write_text(parsed_document)

    result = clean_10K(str(source))
    cleaned = (data_directory / "output_cleaner.txt").read_text()

    assert result is None
    assert "Visible text Revenue" in cleaned
    assert "secret" not in cleaned
    assert "<img" not in cleaned
    assert "<ix:nonnumeric" not in cleaned
    assert "| Year | Revenue |" in cleaned
    assert "| --- | --- |" in cleaned
    assert "| 2026 | $ 10 |" in cleaned


def test_clean_10k_writes_only_to_selected_path(data_directory):
    source = data_directory / "parsed.txt"
    source.write_text("<TEXT><html><body><div>Annual report text</div></body></html></TEXT>")
    selected = data_directory / "selected-filing"
    selected.mkdir()
    output_path = selected / "cleaned.txt"

    clean_10K(str(source), output_path=output_path)

    assert "Annual report text" in output_path.read_text()
    assert not (data_directory / "output_cleaner.txt").exists()


def test_clean_10k_processes_parsed_nvidia_filing(data_directory):
    clean_10K(str(NVIDIA_PARSED_10K))
    cleaned = (data_directory / "output_cleaner.txt").read_text()

    assert "Item 1A. Risk Factors" in cleaned
    assert "President and Chief Executive Officer" in cleaned
    assert "| NVIDIA Corporation |" in cleaned
    assert "<TEXT>" not in cleaned
    assert "<ix:" not in cleaned


def test_clean_10k_requires_a_text_block(data_directory):
    source = data_directory / "parsed-without-text.txt"
    source.write_text("<html><body>No TEXT wrapper</body></html>")

    with pytest.raises(ValueError, match="No TEXT block found"):
        clean_10K(str(source))

    assert not (data_directory / "output_cleaner.txt").exists()
