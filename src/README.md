# src

The src folder, lacking an `__init__.py`, creates a firebreak so that anything which does an `import fle` in the root folder of the project will lookup `fle` via `site-packages` rather than potentially importing directly from the source folder.
This ensures that when switching between editable installs, wheel, sdist testing etc. it is more likely you are importing the copy of `fle` that you intended.
