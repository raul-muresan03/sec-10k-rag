from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re


class Chunker:
    """
    Responsible for splitting the cleaned 10-K text into semantic chunks 
    enriched with metadata (page number, section, ticker, year).
    """

    def __init__(self, text: str, ticker: str, year: str):
        """
        Initializes the Chunker with the full text and global metadata.
        """
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
            marker_type = marker.group(1)
            marker_value = marker.group(2)

            if marker_type == "PAGE":
                current_page = marker_value

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

            if marker_type == "SECTION":
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
        """
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""])
        physical_chunks = []
        for segment in logical_segments:
            text_chunks = splitter.split_text(segment["text"])
            for chunk in text_chunks:
                physical_chunks.append({
                    "text": chunk,
                    "page": segment["page"],
                    "section": segment["section"],
                    "ticker": segment["ticker"],
                    "year": segment["year"]
                })
        return physical_chunks


    def run(self) -> List[Dict[str, Any]]:
        """
        Main execution method. Orchestrates logical segmentation followed by physical chunking.
        """
        logical_segments = self._create_logical_segments()
        physical_chunks = self._split_physically(logical_segments)
        return physical_chunks
