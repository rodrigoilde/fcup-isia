import spade

import cemr


def test_package_imports():
    assert cemr.__version__
    assert spade.__version__ == "4.1.4"
