from random import randrange
from requests import get as req_get
from bs4 import BeautifulSoup

BASE_URL = "https://coppermind.net"
URL = "https://coppermind.net/wiki/Cosmere"

done = False


def table_to_markdown(table):
    table = table.find_all("tr")
    markdown_table = ""
    header = True

    for row in table:
        if row.find("table"):
            continue
        else:
            for collumn in row:
                if collumn.name == "th" or collumn.name == "td":
                    markdown_table += "|"
                    col_text = element_to_markdown(collumn).replace("\n", "")
                    markdown_table += col_text
            markdown_table += "|\n"
        if header:
            markdown_table += "|-|-|\n"
            header = False

    return markdown_table


def html_to_markdown(element):
    markdown = ""
    global done
    if done:
        return ""
    for child in element:
        if done:
            return markdown
        markdown += element_to_markdown(child)

    return markdown


def __element_a_to_markdown__(element):
    try:
        if element["class"][0] in ["external", "extiw", "image"]:
            return ""
    except KeyError:
        pass
    return link_to_markdown(element)


def __element_h2_to_markdown__(element):
    global done
    try:
        if element.text == "Notes[edit]":
            done = True
            return ""
    except KeyError:
        pass  # or some other fallback action
    return "## " + html_to_markdown(element)


def __element_span_to_markdown__(element):
    try:
        if element["class"][0] == "mw-editsection":
            return ""
    except KeyError:
        pass  # or some other fallback action
    return html_to_markdown(element)


def __element_div_to_markdown__(element):
    try:
        if element["class"][0] == "notice quality quality-partial stub":
            return ""
    except KeyError:
        pass  # or some other fallback action
    return html_to_markdown(element)


def __element_blockquote_to_markdown__(element):
    blockquote = ">" + html_to_markdown(element.p).replace("\n", "")
    blockquote = str(blockquote) + "\n"
    if len(element.contents) > 1:
        blockquote += "\-" + element.contents[1].text.replace("—", "")
        blockquote = str(blockquote) + "\n"
    return blockquote


def element_to_markdown(element):
    global done

    match element.name:
        case None:
            return element.text
        case "b" | "th":
            return f"**{element.text}**"
        case "em" | "i":
            return f"*{element.text}*"
        case "ul" | "li" | "td" | "p":
            return html_to_markdown(element)
        case "h3":
            return "### " + html_to_markdown(element)
        case "h4":
            return "#### " + html_to_markdown(element)
        case "table":
            return table_to_markdown(element)
        case "a":
            return __element_a_to_markdown__(element)
        case "h2":
            return __element_h2_to_markdown__(element)
        case "span":
            return __element_span_to_markdown__(element)
        case "div":
            return __element_div_to_markdown__(element)
        case "blockquote":
            return __element_blockquote_to_markdown__(element)
        # case 'sup':
        # footnote_to_markdown(element)
        # return ""
        case _:
            # print(f"{element.name} is not a match")
            return ""


def link_to_markdown(a):
    ref = a.get("href")
    ref = str(ref)
    if (
        "File:" in ref
        or "Artists" in ref
        or "#" in ref
        or ":" in ref
        or "wikipedia" in ref
    ):
        return a.text
    if "wiki" in ref:
        if BASE_URL + ref not in wiki_queue and BASE_URL + ref not in wiki_done:
            wiki_queue.append(BASE_URL + ref)
            print("wiki_queue: " + BASE_URL + ref)

        title = ref.replace("/wiki/", "").replace("_", " ").replace("%27", "'")

        return f"[[{title}\|{a.text}]]"
    return ""


if __name__ == "__main__":
    wiki_queue = [URL]
    wiki_done = []

    while len(wiki_queue) > 0:
        wiki_page = wiki_queue.pop(randrange(0, len(wiki_queue)))
        html_page = req_get(wiki_page)
        doc = BeautifulSoup(html_page.text, "html.parser")
        content = doc.find(class_="mw-parser-output")
        if content is not None:
            title = doc.find(id="firstHeading").text
            if (
                "File:" in title
                or "Artists" in title
                or "#" in title
                or "/" in title
                or ":" in title
                or "wikipedia" in title
            ):
                continue
            print(
                "URL: "
                + wiki_page
                + "    "
                + str(len(wiki_queue))
                + " left"
                + " | "
                + str(len(wiki_done))
                + " completed"
            )
            page = html_to_markdown(content)
            page += "\n\n" + wiki_page
            f = open(f"Cosmere/{title}.md", "w", encoding="utf-8")
            f.write(page)
            f.close()
            wiki_done.append(wiki_page)
            done = False
