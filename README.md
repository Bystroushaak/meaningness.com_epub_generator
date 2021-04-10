# Meaningness.com ebook generator

This is a script that takes a bunch of .html files from [meaningness.com](https://meaningness.com/) online ebook and converts them to epub.

## What to do when it breaks

Obviously, the project is a parser strapped together with epub generator with ducktape, twigs and mud, so it breaks all the time. If that happens to you, just report the issue on github.

## How to use

Install requirements:

    pip3 install --user -r requirements.txt
    
Note: On some of the newer environments (like Ubuntu 20.10, or Linux Mint 20.1 Ulyssa), `pip` is configured to install `python3` packages, so use `pip` instead of `pip3` (see [#1](https://github.com/Bystroushaak/meaningness.com_epub_generator/issues/1) for details).

Run Makefile:

    make epub

Optionally, you can also run the calibre conversion script to fix all kind of wrongness with the epub:

    ebook-convert meaningness.epub meaningness_clean.epub

## Download

Unoficial (possibly broken) serialised version can be found here:

* http://kitakitsune.org/sync/ebooks/meaningness_clean.epub (compiled 2021.02.06)
