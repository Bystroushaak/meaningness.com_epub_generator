#! /usr/bin/env python3
import sys
import logging
import os.path
import hashlib
import argparse

import requests
import dhtmlparser
from ebooklib import epub

PROJECT_URL = "https://github.com/Bystroushaak/meaningness.com_epub_generator"


logger = logging.getLogger("convertor")
stderr_logger = logging.StreamHandler(sys.stderr)
stderr_logger.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s"
))
logger.addHandler(stderr_logger)
logger.setLevel(logging.DEBUG)


class BookGenerator:
    """
    Just to keep track about chapters, automatically generate table of contents
    and so on.
    """
    def __init__(self, title):
        self.book = epub.EpubBook()
        self.title = title
        self.chapters = []
        self.toc = []

        self.book.set_title(self.title)

    def generate_ebook(self, path):
        self._add_css()
        self._add_toc()

        epub.write_epub(path, self.book, {})

    def set_language(self, lang):
        return self.book.set_language(lang)

    def add_metadata(self, namespace, name, value, others=None):
        return self.book.add_metadata(namespace, name, value, others)

    def add_chapter(self, chapter):
        self.book.add_item(chapter)
        self.chapters.append(chapter)

    def add_image(self, image):
        self.book.add_item(image)

    def add_author(self, author):
        self.book.add_author(author)

    def _add_toc(self):
        if self.toc:
            self.book.toc = self.toc
        else:
            self.book.toc = (
                (epub.Section(self.title),
                 self.chapters),
            )

        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        self.book.spine = ['nav'] + self.chapters

    def _add_css(self):
        # define CSS style
        style = 'BODY {color: white;}'
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )

        self.book.add_item(nav_css)


class MeaningnessEbook:
    def __init__(self, html_root, tmp_path):
        self.tmp_path = tmp_path

        self.html_root = html_root
        self.book = BookGenerator('Meaningness')

        self.book.add_author('David Chapman')
        self.book.set_language('en')
        self.book.add_metadata('DC', 'date', "2020-01-27")
        self.book.add_metadata('DC', 'generator', '', {'name': 'generator',
                                                       'content': PROJECT_URL})

        self.chapters_metadata = list(self.parse_book_contents(html_root))

        path_chapter_map = {}
        for article_path, chapter_fn in self.chapters_metadata:
            chapter = self.convert_chapter(article_path, chapter_fn)
            self.book.add_chapter(chapter)
            path_chapter_map[article_path] = chapter

        self.book.toc = self.parse_toc(path_chapter_map)

    def parse_book_contents(self, html_root):
        logger.info("Parsing book contents..")

        with open(os.path.join(html_root, "index.html")) as f:
            index_html = f.read()

        index_dom = dhtmlparser.parseString(index_html)
        toc_dom = index_dom.find("nav", {"class": "book-tree"})[0]
        for a_el in toc_dom.find("a"):
            href = a_el.params["href"]
            yield (href, href)

    def parse_toc(self, path_chapter_map):
        logger.info("Parsing TOC structure from index.html..")

        with open(os.path.join(self.html_root, "index.html")) as f:
            index_html = f.read()

        index_dom = dhtmlparser.parseString(index_html)
        toc_dom = index_dom.find("nav", {"class": "book-tree"})[0]

        def process(toc_dom):
            li_structure = []
            for li in toc_dom.wfind("li").childs:
                if li.params.get("class", "") == "":
                    sub_chapters = process(li.find("ul")[0])
                    last_li = li_structure.pop()
                    li_structure.append([last_li, sub_chapters])
                else:
                    href = li.find("a")[0].params["href"]
                    li_structure.append(path_chapter_map[href])

            return li_structure

        return process(toc_dom)

    def convert_chapter(self, article_path, chapter_fn, title=None):
        logger.info("Converting %s", article_path)

        full_path = os.path.join(self.html_root, article_path)
        if os.path.isdir(full_path):
            raise ValueError(full_path)

        with open(full_path) as f:
            dom = dhtmlparser.parseString(f.read())

        if not title:
            title = dom.find("title")[0].getContent()
            title = title.replace(" | Meaningness", "", 1)

        body = dom.find("body")[0]

        self.remove_fluff(body)
        self._inline_images(body, article_path)

        chapter = epub.EpubHtml(title=title, file_name=chapter_fn)
        chapter.content = body.getContent()

        return chapter

    def remove_fluff(self, body):
        empty = dhtmlparser.parseString("")

        def replace(selector):
            for el in selector:
                el.replaceWith(empty)

        replace(body.find("div", {"class": "nocontent"}))
        replace(body.find("div", {"class": "tertiary-content-wrapper"}))
        replace(body.find("div", {"class": "more-link"}))
        replace(body.find("div", {"class": "view-content"}))
        replace(body.find("div", {"class": "block-content content"}))
        replace(body.find("div", {"class": "region region-content-aside"}))
        replace(body.find("div", {"role": "search"}))
        replace(body.find("div", {"class": "comment_bubble_wrapper"}))
        replace(body.find("div", fn=lambda x: "block-meaningness-navigation" in x.params.get("class", "")))
        replace(body.find("header"))
        replace(body.find("footer"))
        replace(body.find("div", {"id": "tertiary-content-wrapper"}))
        replace(body.find("nav", {"class": "clearfix"}))

        return body.find("main")[0]

    def _inline_images(self, body, article_path):
        for img in body.find("img"):
            src = img.params["src"]

            if src.startswith("../"):
                src = src.replace("../", "")

            try:
                if src.startswith("http://") or src.startswith("https://"):
                    epub_img = self._inline_remote_image(src)
                else:
                    epub_img = self._inline_local_image(img, src)
            except IOError:
                continue

            self.book.add_image(epub_img)

            root = ""
            if "/" in article_path:
                root = "../"
            img.params["src"] = root + epub_img.file_name


    def _inline_remote_image(self, src):
        epub_img = epub.EpubImage()

        digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
        digest_name = "{}.{}".format(digest, src.rsplit(".")[-1])
        epub_img.file_name = os.path.join(self.tmp_path, digest_name)

        if not os.path.exists(epub_img.file_name):
            logger.info("Downloading remote image %s", src)

            resp = requests.get(src)
            with open(epub_img.file_name, "wb") as f:
                f.write(resp.content)

        logger.info("Remote image %s added as %s", src, epub_img.file_name)

        return epub_img

    def _inline_local_image(self, img, src):
        epub_img = epub.EpubImage()
        epub_img.file_name = src

        image_path = os.path.join(self.html_root, src)
        if not os.path.exists(image_path):
            logger.error("File %s doesn't exists, skipping!", image_path)
            raise IOError("Can't open %s" % image_path, image_path)

        with open(image_path, "rb") as f:
            epub_img.content = f.read()

        if "style" in img.params:
            del img.params["style"]

        logger.info("Local image %s added", epub_img.file_name)

        return epub_img

    def generate_ebook(self, path):
        return self.book.generate_ebook(path)


def put_ebook_together(html_path):
    tmp_name = "tmp_images"

    if not os.path.exists(tmp_name):
        os.mkdir(tmp_name)

    book = MeaningnessEbook(html_path, tmp_name)
    book.generate_ebook('meaningness.epub')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
            "PATH",
            help="Path to the directory with the blog section about Self."
    )
    args = parser.parse_args()

    put_ebook_together(args.PATH)
