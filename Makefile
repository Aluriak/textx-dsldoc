
most-working-poc:
	python poc_as_cls.py


show-out-html:
	xdg-open out.html

clear:
	- rm -r build dist __pycache__ textx_dsldoc.egg-info

test_textx_integration:
	yes | pip uninstall textx textx-dsldoc
	cd textX && python setup.py install
	python setup.py install
	textx autodoc examples/example.py -m METAMODEL
