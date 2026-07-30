.PHONY: test lint install uninstall

test:
	python3 -m unittest discover -s tests -v

lint:
	python3 -m compileall -q c64app tests c64

install:
	./install.sh

uninstall:
	./uninstall.sh
