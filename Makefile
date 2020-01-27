.PHONY: epub, download, clean

epub: download
	./make.py "meaningness.com"

download:
	if [ ! -d "meaningness.com" ]; then \
		wget -r -l 1 -k -p -E https://meaningness.com/; \
	fi

clean:
	rm -r "meaningness.com"