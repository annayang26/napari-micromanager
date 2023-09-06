# napari-micromanager

[![License](https://img.shields.io/pypi/l/napari-micromanager.svg?color=green)](https://github.com/napari/napari-micromanager/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-micromanager.svg?color=green)](https://pypi.org/project/napari-micromanager)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-micromanager.svg?color=green)](https://python.org)
[![Tests](https://github.com/pymmcore-plus/napari-micromanager/actions/workflows/test.yml/badge.svg)](https://github.com/pymmcore-plus/napari-micromanager/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/pymmcore-plus/napari-micromanager/branch/main/graph/badge.svg?token=tf6lYDWV1s)](https://codecov.io/gh/pymmcore-plus/napari-micromanager)

GUI interface between napari and micromanager powered by [pymmcore-plus](https://pymmcore-plus.readthedocs.io/) and [pymmcore-widgets](https://pymmcore-plus.github.io/pymmcore-widgets/)

🚧 Experimental!  Work in progress!  Here be 🐲 🚧

----------------------------------
<img width="1797" alt="mm" src="https://user-images.githubusercontent.com/1609449/138457506-787b7bec-7f30-4d92-b5cf-6e218c87225a.png">


## Installation

We recomend to use [conda] to first create a new environment:

```
conda create -n napari-mm python=3.10
```

You can then activate the newly created envirinment:

```
conda activate napari-mm
```

And install `napari-micromanager` via [pip]:

```
pip install napari-micromanager
```

Note that before start using `napari-micromanager`, you also have to install one of the [PyQt]/[PySide] backend, for example `PyQt6`:

```
pip install PyQt6
```


### Getting micromanager adapters:

The easiest way to get the micromanager adapters is to use:

```
mmcore install
```

this will install micromanager to the pymmcore_plus folder in your site-package; use this to see where:

```
python -c "from pymmcore_plus import find_micromanager; print(find_micromanager())"
```

alternatively, you can direct pymmcore_plus to your own micromanager installation with the `MICROMANAGER_PATH`
environment variable:

```
export MICROMANAGER_PATH='/path/to/Micro-Manager-...'
```

### Launching napari with plugin
You can launch napari and automatically load this plugin using:

```bash
napari -w napari-micromanager
```

### Contributing

Contributions are very welcome.


## License

Distributed under the terms of the [BSD-3] license,
"napari-micromanager" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin
[file an issue]: https://github.com/pymmcore-plus/napari-micromanager/issues
[napari]: https://github.com/napari/napari
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
[conda]: https://docs.conda.io/projects/miniconda/en/latest/
[PyQt]: https://riverbankcomputing.com/software/pyqt/
[PySide]: https://www.qt.io/qt-for-python
