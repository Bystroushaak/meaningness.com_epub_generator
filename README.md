# Meaningness.com ebook generator

This is a script that takes a bunch of .html files from [meaningness.com](https://meaningness.com/) online ebook and converts them to epub.

## How to use

Install requirements:

    pip3 install --user -r requirements.txt

Run make script:

    ./make.py

Optionally, you can also run the calibre conversion script to fix all kind of wrongness with the epub:

    ebook-convert meaningness.epub meaningness_cleaned.epub
