from random import randrange
import re
from requests import get as req_get
from bs4 import BeautifulSoup, Tag as bs_tag
from os.path import basename, exists
from re import match
from urllib.parse import unquote

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
        if (
            isinstance(child, bs_tag)
            and child.get("class") is not None
            and child["class"][0] == "thumbcaption"
            and match(r".*\[\[attachments/File:[\w\.]+\]\]\s*$", markdown)
        ):
            markdown = markdown.replace("]]", f"|{element_to_markdown(child)}]] ")
        else:
            markdown += element_to_markdown(child)

    return markdown


def __download_image__(element):
    src_url = str(element.contents[0]["src"])
    if src_url.startswith("https://"):
        image_url = src_url
    else:
        image_url = BASE_URL + element.contents[0]["src"]
    image_name = f"Cosmere/attachments/{basename(element['href'].replace(':', '-'))}"

    with open(image_name, "wb") as f:
        f.write(req_get(image_url).content)


def __element_a_to_markdown__(element):
    try:
        if element["class"][0] in ["external", "extiw"]:
            return ""
        elif element["class"][0] == "image":
            __download_image__(element)
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
        if element["class"][0] in [
            "notice quality quality-partial stub",
            "thumb tright",
            "magnify",
            "attribution",
        ]:
            return ""
        if element.get("id") is not None and element["id"] == "spoilers":
            return f"> [!warning] {html_to_markdown(element)}"
        if element["class"][0] == "notice-main-text" and not (
            element.parent.get("id") is not None and element.parent["id"] == "spoilers"
        ):
            return f"> [!info] {html_to_markdown(element)}"

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
            return f"**{html_to_markdown(element)}**"
        case "em" | "i":
            return f"*{html_to_markdown(element)}*"
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


def __parse_toc_indexes__(index: str, text: str):
    if match(r"\d(\.\d)*", index):
        levels = index.split(".")
        last_index = index.split(".")[-1]
        tabs = "\t" * (len(levels) - 1)
        return f"{tabs}{last_index}. [[{text.replace('_', ' ')}]] "
    else:
        return f"[[{text.replace('_', ' ')}]]"


def __parse_wiki_links__(parent, text, ref):
    if BASE_URL + ref not in wiki_queue and BASE_URL + ref not in wiki_done:
        wiki_queue.append(BASE_URL + ref)
        print("wiki_queue: " + BASE_URL + ref)

    title = ref.replace("/wiki/", "").replace("_", " ").replace("%27", "'")

    try:
        if (
            parent["class"][0] == "thumbcaption"
            or parent.parent["class"][0] == "thumbcaption"
        ):
            return f"<<{title}\|{text}>>"
    except KeyError:
        pass
    return f"[[{title}\|{text}]]"


def link_to_markdown(a):
    ref = a.get("href")
    ref = str(ref)

    if "File:" in ref:
        if exists(f"Cosmere/attachments/{basename(ref)}"):
            return f"![[attachments/{basename(ref)}]]"
        else:
            return a.text

    if "Artists" in ref or ":" in ref or "wikipedia" in ref:
        return a.text

    if "#" in ref:
        return __parse_toc_indexes__(a.text.split(".")[0], ref)

    if "wiki" in ref:
        return __parse_wiki_links__(a.parent, a.text, ref)

    return ""

def __get_page_title__(document, page_name):
    title = document.find(id="firstHeading").text
    redirected = None
    if "/" in title:
        return title

    sp_page_name = unquote(page_name).replace("_", " ")

    if title != sp_page_name:
        redirected = document.find(class_="mw-redirect").text

    if redirected is None or redirected == title:
        return title
    else:
        return redirected


if __name__ == "__main__":
    wiki_queue = [URL]
    wiki_done = []

    if not exists("Cosmere/attachments"):
        from os import mkdir
        mkdir("Cosmere/attachments")

    while len(wiki_queue) > 0:
        wiki_page = wiki_queue.pop(randrange(0, len(wiki_queue)))
        html_page = req_get(wiki_page)
        doc = BeautifulSoup(html_page.text, "html.parser")
        content = doc.find(class_="mw-parser-output")
        if content is not None:
            title = __get_page_title__(doc, wiki_page.split("/")[-1])

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
