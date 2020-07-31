.PHONY: epub, download, clean, help

.DEFAULT: download_and_make
download_and_make: download epub
	echo "Done"

epub: download
	./make.py "meaningness.com"

download:
	if [ ! -d "meaningness.com" ]; then \
		wget -r -l 1 -k -p -E https://meaningness.com/; \
	fi

clean:
	ebook-convert meaningness.epub meaningness_clean.epub

help:
	echo "meaningness.com generator"
	echo
	echo -e "\tepub"
	echo -e "\t\tGenerate epub from downloaded files."
	echo
	echo -e "\tdownload"
	echo -e "\t\tDownload files on meaningness.com which can be used to generate epub."
	echo
	echo -e "\tclean"
	echo -e "\t\tConvert generated epub with calibre for cleaner version."
	echo
