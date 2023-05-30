# Changelog
All notable changes to the `colifer` repository will be documented in this file. 
The content is organised by merged pull requests.

When updating this file, please bear in mind that the goal of the changelog is to be:
- a *human-readable* list of changes to `colifer`,
- a resource for users of `colifer` to quickly identify how to resolve breaking changes.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). 
Also, please add the MR link to each item in this Changelog.

## [0.0.3]
from [os] - 2023-04-28
### Added
- Done Aggregation script to incorporate "Done Stuff.md" into the weekly report.
### Changed
- Made Past tense rules file optional. If it's not defined, then verbs are not converted to past tense.
    - This is made to simplify Done aggregation. Otherwise, it's harder to match entry names between done and report.

## [0.0.2]
from [os] - 2023-04-19
### Added
- `__version__.py` file.
- Basic documentation in `README.md`.

## [0.0.1]
from [os] - 2022-10-30
### Added
- `CHANGELOG.md`, `README.md`, `setup.py`, and `test_requirments.txt` files. 
- Script `reportextenders/articles/pocket_stats.py` and endpoint `pocket_stats`.
- `setup.py` file to be able create a package.
- A script for calculating simple Pocket stats.
### Changed
- Moved `colifer` into `src` folder.
- Flattened tags order for making reports simpler.
- Pruned constant section configuration.

[os]: https://github.com/oshev