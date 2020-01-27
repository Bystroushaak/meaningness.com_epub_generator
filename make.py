#! /usr/bin/env python3
import sys
import shutil
import logging
import os.path
import hashlib
import argparse
import tempfile

import requests
import dhtmlparser
from ebooklib import epub

PROJECT_URL = ""  # TODO: add github url


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

        self.chapters_metadata = [
            ('Environment and the programming language Self part.html',
             'chap_01.xhtml'),
        ]
        self.chapters_metadata = list(self.parse_toc(html_root))

        logger.debug(self.chapters_metadata)

        for article_path, chapter_fn in self.chapters_metadata:
            self.convert_chapter(article_path, chapter_fn)

    def parse_toc(self, html_root):
        logger.info("Parsing toc..")

        with open(os.path.join(html_root, "index.html")) as f:
            index_html = f.read()

        index_dom = dhtmlparser.parseString(index_html)
        toc_dom = index_dom.find("ul", {"class": "book-toc"})[0]
        for a_el in toc_dom.find("a"):
            href = a_el.params["href"]
            yield (href, href)

    def convert_chapter(self, article_path, chapter_fn, title=None):
        logger.info("Converting %s", article_path)

        full_path = os.path.join(self.html_root, article_path)
        if os.path.isdir(full_path):
            raise ValueError(full_path)

        with open(full_path) as f:
            dom = dhtmlparser.parseString(f.read())

        if not title:
            title = dom.find("title")[0].getContent()
            title = title.split("(")[-1].split(")")[0].capitalize()

        body = dom.find("body")[0]

        # self._remove_fluff_from_the_beginning(body)
        # self._remove_fluff_from_the_end(body)
        self._inline_images(body)

        chapter = epub.EpubHtml(title=title, file_name=chapter_fn)
        chapter.content = body.getContent()
        self.book.add_chapter(chapter)
    #
    # def _remove_fluff_from_the_beginning(self, body):
    #     while body.childs[0].getTagName() != "hr":
    #         body.childs.pop(0)
    #     body.childs.pop(0)
    #
    # def _remove_fluff_from_the_end(sefl, body):
    #     look_for = ["Next episodes", "Next episode", "Last episode", "Relevant discussions"]
    #
    #     selected_phrase = ""
    #     for phrase in look_for:
    #         if body.find("h1", fn=lambda x: x.getContent() == phrase):
    #             selected_phrase = phrase
    #             break
    #     else:
    #         return
    #
    #     while body.childs[-1].getContent() != selected_phrase:
    #         body.childs.pop()
    #     body.childs.pop()

    def _inline_images(self, body):
        for img in body.find("img"):
            epub_img = epub.EpubImage()

            src = img.params["src"]

            if src.startswith("../"):
                src = src.replace("../", "")

            if src.startswith("http://") or src.startswith("https://"):
                digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
                digest_name = "{}.{}".format(digest, src.rsplit(".")[-1])
                epub_img.file_name = os.path.join(self.tmp_path, digest_name)

                if not os.path.exists(epub_img.file_name):
                    logger.info("Downloading remote image %s", src)

                    resp = requests.get(src)
                    with open(epub_img.file_name, "wb") as f:
                        f.write(resp.content)

                logger.info("Remote image %s added as %s", src,
                             epub_img.file_name)
            else:
                epub_img.file_name = os.path.basename(src)
                image_path = os.path.join(self.html_root, src)

                if not os.path.exists(image_path):
                    logger.error("File %s doesn't exists, skipping!", image_path)
                    continue

                with open(image_path, "rb") as f:
                    epub_img.content = f.read()

                if "style" in img.params:
                    del img.params["style"]

                logger.info("Local image %s added", epub_img.file_name)

            self.book.add_image(epub_img)
            img.params["src"] = epub_img.file_name

    def generate_ebook(self, path):
        return self.book.generate_ebook(path)


def put_ebook_together(html_path):
    tmp_name = "tmp_images"

    if not os.path.exists(tmp_name):
        os.mkdir(tmp_name)

    book = MeaningnessEbook(html_path, tmp_name)
    book.generate_ebook('meanigness.epub')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
            "PATH",
            help="Path to the directory with the blog section about Self."
    )
    args = parser.parse_args()

    put_ebook_together(args.PATH)
