from __future__ import annotations

from pathlib import Path
import tomllib


def _project_metadata() -> dict:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]


def test_package_metadata_matches_public_launch_positioning() -> None:
    project = _project_metadata()

    assert project["name"] == "labcheck"
    assert project["description"] == "No-key reproducibility audits for notebook-heavy research and ML repositories."
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == []

    keywords = set(project["keywords"])
    for keyword in [
        "reproducibility",
        "jupyter-notebook",
        "machine-learning",
        "research-software",
        "static-analysis",
        "github-action",
    ]:
        assert keyword in keywords


def test_package_metadata_exposes_public_project_urls() -> None:
    urls = _project_metadata()["urls"]

    assert urls["Homepage"] == "https://thomasaquinas14.github.io/labcheck/"
    assert urls["Documentation"] == "https://thomasaquinas14.github.io/labcheck/README.md"
    assert urls["Repository"] == "https://github.com/ThomasAquinas14/labcheck"
    assert urls["Issues"] == "https://github.com/ThomasAquinas14/labcheck/issues"
    assert urls["Demo"] == "https://thomasaquinas14.github.io/labcheck/demo.html"
    assert urls["Safety"] == "https://thomasaquinas14.github.io/labcheck/docs/privacy-and-safety.md"


def test_package_metadata_has_discovery_classifiers() -> None:
    classifiers = set(_project_metadata()["classifiers"])

    for classifier in [
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ]:
        assert classifier in classifiers
