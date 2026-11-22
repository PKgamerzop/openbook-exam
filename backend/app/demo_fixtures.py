"""Original DBMS teaching notes. The list order is the physical PDF page order."""

from io import BytesIO
from textwrap import wrap

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

NOTES = {
    "indexing-guide": [
        (
            "Choosing a B-tree",
            "A branch separator guides a lookup toward one leaf. For the campus "
            "repair ledger, index the ticket number when most requests retrieve a "
            "single ticket.",
        ),
        (
            "Scanning a range",
            "For tickets between 120 and 145, descend once and follow ordered leaf "
            "entries until the upper bound. Compare the number of visited leaves "
            "with a full scan.",
        ),
    ],
    "transactions-guide": [
        (
            "Snapshot visibility",
            "An analyst reads the same ledger twice while a clerk commits a "
            "correction. A stable snapshot keeps the analyst's two reads "
            "consistent.",
        ),
        (
            "Detecting a deadlock",
            "Mira locks shelf A then waits for shelf B. Ravi holds B and waits for "
            "A. Draw the wait graph. Abort one participant to let the other finish, "
            "then retry the interrupted transfer.",
        ),
    ],
    "query-optimization": [
        (
            "Reading a plan",
            "Compare estimated cardinality with rows observed after a filter. If "
            "the estimate for active tickets is low by a factor of fifty, "
            "investigate stale statistics.",
        ),
        (
            "Building a hashjoin",
            "For an equality join, build a hash table from the smaller input and "
            "probe it with the larger stream. Account for spill cost if the build "
            "side exceeds memory.",
        ),
    ],
    "normalization-guide": [
        (
            "Functional dependency",
            "In a workshop roster, a bench code determines its room. Storing the "
            "room on every reservation duplicates a fact and makes corrections "
            "expensive.",
        ),
        (
            "Lossless decomposition",
            "Split bench locations from reservations using bench code as the common "
            "key. Rejoin the tables and verify that each reservation recovers "
            "precisely one room.",
        ),
    ],
}
CANONICAL = {
    "leaf": ("indexing-guide", [1, 2]),
    "snapshot": ("transactions-guide", [1]),
    "deadlock": ("transactions-guide", [2]),
    "cardinality": ("query-optimization", [1]),
    "hashjoin": ("query-optimization", [2]),
    "dependency": ("normalization-guide", [1]),
    "decomposition": ("normalization-guide", [2]),
}


def fixture(name):
    if name == "malformed":
        return b"This is a synthetic invalid PDF."
    writer = PdfWriter()
    for heading, paragraph in NOTES.get(name, [("", "")]):
        page = writer.add_blank_page(width=480, height=620)
        stream = DecodedStreamObject()
        if name == "scan":
            # Inline 2x2 grayscale raster of a checkerboard.
            content = b"q 240 0 0 240 80 200 cm BI /W 2 /H 2 /CS /G "
            content += b"/BPC 8 ID \x00\xff\xff\x00 EI Q"
        else:
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            page[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
            )
            lines = [heading, "", *wrap(paragraph, 65)]
            content = (
                "BT /F1 12 Tf 18 TL 30 560 Td "
                + " T* ".join(f"({line}) Tj" for line in lines)
                + " ET"
            ).encode("ascii")
        stream.set_data(content)
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
