
# import pymupdf

# pdf = pymupdf.open(r"data\UCS310\UCS310_2025_O_EST.pdf")

# all_text = ""

# for page_num, page in enumerate(pdf):
#     text = page.get_text("text")
#     all_text += text + "\n"

#     print(f"Page {page_num + 1}:\n{text}")

# pdf.close()

# # Save extracted text to a file
# with open("output.txt", "w", encoding="utf-8") as f:
#     f.write(all_text)


import pymupdf4llm

md = pymupdf4llm.to_markdown(r"C:\Users\HP\Desktop\prodsss\PaperTrail\data\UCS310\UCS310_2025_O_EST.pdf")
print(md)

with open("output.md", "w", encoding="utf-8") as f:
    f.write(md)

# per-page chunks with metadata (page number etc.)
# pages = pymupdf4llm.to_markdown("file.pdf", page_chunks=True)
