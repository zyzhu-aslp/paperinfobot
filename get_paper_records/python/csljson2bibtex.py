import json


def format_authors(authors):
    """Convert CSL author list to BibTeX author format"""
    if not authors:
        return ""
    names = []
    for a in authors:
        family = a.get("family", "")
        given = a.get("given", "")
        names.append(f"{family}, {given}".strip(", "))
    return " and ".join(names)


def get_year(entry):
    try:
        return str(entry["issued"]["date-parts"][0][0])
    except:
        return ""


def make_key(entry, index):
    """Generate a simple BibTeX key"""
    authors = entry.get("author", [])
    year = get_year(entry)

    if authors:
        first_author = authors[0]["family"]
        return f"{first_author}{year}"
    else:
        return f"entry{index}"


def csl_json_to_bibtex(csl_json):

    entries = []
    seen_doi = set()

    for i, e in enumerate(csl_json):

        doi = e.get("DOI", "")
        if doi in seen_doi:
            continue
        seen_doi.add(doi)

        title = e.get("title", "")
        authors = format_authors(e.get("author", []))
        journal = e.get("container-title", "")
        year = get_year(e)
        pages = e.get("page", "")
        volume = e.get("volume", "")
        publisher = e.get("publisher", "")
        url = e.get("URL", "")

        entry_type = "article"
        if e.get("type") == "proceedings-article":
            entry_type = "inproceedings"

        key = make_key(e, i)

        bibtex = f"""@{entry_type}{{{key},
  title = {{{title}}},
  author = {{{authors}}},
  year = {{{year}}},
  journal = {{{journal}}},
  volume = {{{volume}}},
  pages = {{{pages}}},
  publisher = {{{publisher}}},
  doi = {{{doi}}},
  url = {{{url}}}
}}"""

        entries.append(bibtex)

    return "\n\n".join(entries)


def convert(csl_json_path, bibtex_path):

    with open(csl_json_path, "r", encoding="utf-8") as f:
        csl_json = json.load(f)

    bibtex_output = csl_json_to_bibtex(csl_json)

    with open(bibtex_path, "w", encoding="utf-8") as f:
        f.write(bibtex_output)


if __name__ == "__main__":

    csl_json_path = "/Users/yjliao/Downloads/lark-samples-main/get_paper_records/csl.json"
    bibtex_path = "/Users/yjliao/Downloads/lark-samples-main/out/publications.bib"

    convert(csl_json_path, bibtex_path)

    print("BibTeX generated:", bibtex_path)