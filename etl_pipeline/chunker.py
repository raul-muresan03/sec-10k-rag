from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import hashlib


class Chunker:
    """
    Responsible for splitting the cleaned 10-K text into semantic chunks
    enriched with metadata (page number, section, ticker, year).
    """

    def __init__(self, text: str, ticker: str, year: str):
        self.text = text
        self.ticker = ticker
        self.year = year

    def _create_logical_segments(self) -> List[Dict[str, Any]]:
        """
        Parses the text to identify [[PAGE_...]] and [[SECTION_...]] markers.
        Splits the text into 'logical segments' where each segment has a specific
        page and section context.
        """

        current_page = "Unknown"
        current_section = "Header"
        last_pos = 0
        segments = []

        all_markers = list(re.finditer(r"\[\[(PAGE|SECTION)_(.*?)\]\]", self.text))

        for marker in all_markers:
            if marker.group(1) == "PAGE":
                current_page = marker.group(2)
                break

        for marker in all_markers:
            marker_type = marker.group(1)
            marker_value = marker.group(2)

            if last_pos < marker.start():
                segment_text = self.text[last_pos:marker.start()].strip()
                if segment_text:
                    segments.append({
                        "text": segment_text,
                        "page": current_page,
                        "section": current_section,
                        "ticker": self.ticker,
                        "year": self.year
                    })

            if marker_type == "PAGE":
                current_page = marker_value
            elif marker_type == "SECTION":
                current_section = marker_value

            last_pos = marker.end()

        if last_pos < len(self.text):
            remaining_text = self.text[last_pos:].strip()
            if remaining_text:
                segments.append({
                    "text": remaining_text,
                    "page": current_page,
                    "section": current_section,
                    "ticker": self.ticker,
                    "year": self.year
                })

        return segments


    def _split_physically(self, logical_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes logical segments and applies RecursiveCharacterTextSplitter
        to ensure chunks fit within the context window (e.g., 1000 chars).
        It also generates a stable, unique ID for each chunk.
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""])
        physical_chunks = []
        for segment_idx, segment in enumerate(logical_segments):
            text_chunks = splitter.split_text(segment["text"])
            for chunk_idx, chunk_text in enumerate(text_chunks):
                unique_string = f"{segment['ticker']}-{segment['year']}-{segment_idx}-{chunk_idx}"
                chunk_id = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

                physical_chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "page": segment["page"],
                    "section": segment["section"],
                    "ticker": segment["ticker"],
                    "year": segment["year"]
                })
        return physical_chunks


    def run(self) -> List[Dict[str, Any]]:
        logical_segments = self._create_logical_segments()
        physical_chunks = self._split_physically(logical_segments)
        return physical_chunks
