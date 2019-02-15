
most-working-poc:
	python poc_as_cls.py


show-out-html:
	xdg-open out.html

clear:
	- rm -r build dist __pycache__ textx_dsldoc.egg-info
