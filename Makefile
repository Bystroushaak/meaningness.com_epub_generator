.PHONY: html, clean

html:
	if [ ! -d "meaningness.com" ]; then \
		wget -r -l 1 -k -p https://meaningness.com/; \
	fi


clean:
	rm -r "meaningness.com"