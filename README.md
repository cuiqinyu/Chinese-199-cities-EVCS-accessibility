# Chinese 199 Cities EVCS Accessibility

This repository hosts the data products, metadata, and reproducible code for a multiscale electric vehicle charging station (EVCS) accessibility dataset covering 199 Chinese cities.

The repository is organized in the same spirit as open Scientific Data / data descriptor repositories: the paper describes the dataset and validation, while this repository maintains the reusable files, field dictionary, processing notes, and future updates.

## Repository Status

This repository is under preparation for manuscript submission. File names, field dictionaries, and release archives may be updated before the first formal release.

Planned release URL:

`https://github.com/cuiqinyu/Chinese-199-cities-EVCS-accessibility`

## Contents

```text
data/
  2SFCA_1to8km_EVCS_Conservative_Map/
    a_1000mGrid_g2sfca_core.*
    b_district_g2sfca_accessibility.*
    c_city_2sfca_accessibility.*
    d_province_g2sfca.*
code/
  README.md
metadata/
  dataset_manifest.csv
  field_dictionary_core.csv
LICENSE
CITATION.cff
README.md
```

## Core Data Products

The first public release is expected to include processed accessibility products rather than all restricted raw inputs.

| File group | Spatial scale | CRS | Records | Description |
| --- | --- | --- | ---: | --- |
| `a_1000mGrid_g2sfca_core.*` | 1 km grid | EPSG:6933 | 1,860,012 | Population, EV demand, and weighted 2SFCA accessibility summaries. |
| `b_district_g2sfca_accessibility.*` | District/county | EPSG:4326 | 1,834 | District-scale accessibility summaries. |
| `c_city_2sfca_accessibility.*` | City | EPSG:4326 | 199 | City-scale accessibility summaries for the 199 study cities. |
| `d_province_g2sfca.*` | Province | China Lambert Conformal Conic | 23 | Province-scale accessibility summaries for study-area portions. |

Additional CSV and GeoTIFF versions may be added in later releases when they are generated from the same source tables and identifiers.

## Restricted Inputs

Some raw inputs are not redistributed because they depend on third-party platform terms or API credentials. These include raw EVCS platform records, raw map API responses, and API keys. The released dataset contains derived accessibility products and metadata sufficient for reuse and validation.

## License

Unless otherwise noted, the processed data, documentation, and metadata in this repository are released for non-commercial academic use under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

Users must cite the associated paper and this repository/release when using the data. Commercial use requires prior written permission from the authors.

## Citation

A formal citation will be added after manuscript acceptance and/or DOI release. For now, cite this repository as:

> Cui, Q. et al. Chinese 199 Cities EVCS Accessibility. GitHub repository, version to be released.

## Maintenance

This repository is intended for long-term maintenance. Issues may be used for reporting file problems, field-definition questions, or reproducibility notes after the first release.

