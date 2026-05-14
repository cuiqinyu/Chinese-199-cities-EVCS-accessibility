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
  TravelDistance/
    Nearest1to8EVCS/
      100m/
      Merge/
  2SFCA/
    1to8km/
      100m/
      Merge/
  Derivatives/
    DoubleIndex_Accessibility_Map/
    Accessibility_Gini_Map/
  Validation/
    EVCS_Dataset/
    DoubleMethods_TravelDistance/
    DifferentNearestEVCS_TravelDistance/
    DifferentDistanceThreshold_2SFCA/
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

The first public release is expected to include processed accessibility products rather than all restricted raw inputs. The data records follow the current manuscript overview table.

| Group | Data record | Format | Spatial scale | Main contents |
| --- | --- | --- | --- | --- |
| Travel distance for accessibility | `data/TravelDistance/Nearest1to8EVCS/100m/` | CSV | 100 m research units | City-split fine-scale travel-distance records from each research unit to the nearest 1--8 ordinary EVCS and fast EVCS, in km. |
| Travel distance for accessibility | `data/TravelDistance/Nearest1to8EVCS/Merge/` | SHP | Grid, county/district, city, province | National travel-distance maps and multiscale summaries merged or aggregated from the 100 m city CSV records. |
| 2SFCA for accessibility | `data/2SFCA/1to8km/100m/` | CSV | 100 m research units | City-split fine-scale 2SFCA accessibility records for 1, 1.5, and 2--8 km distance thresholds, including aggressive and conservative charging-power assumptions. |
| 2SFCA for accessibility | `data/2SFCA/1to8km/Merge/` | SHP | Grid, county/district, city, province | National 2SFCA accessibility maps and multiscale summaries under the conservative charging-power scenario. |
| Derivatives | `data/Derivatives/DoubleIndex_Accessibility_Map/` | SHP | City | Combined travel-distance and 2SFCA accessibility classification for identifying different types of accessibility deficits. |
| Derivatives | `data/Derivatives/Accessibility_Gini_Map/` | SHP | City | Within-city inequality indicators for 2SFCA accessibility. |
| Technical validation | `data/Validation/EVCS_Dataset/` | CSV | City and county/district | Aggregate-scale validation of the Star Charge EVCS data against independent Amap EVCS records. |
| Technical validation | `data/Validation/DoubleMethods_TravelDistance/` | CSV | OD samples | Comparison records between OSM road distances and map API route distances. |
| Technical validation | `data/Validation/DifferentNearestEVCS_TravelDistance/` | CSV | City | Consistency checks for nearest 1--8 EVCS travel-distance indicators. |
| Technical validation | `data/Validation/DifferentDistanceThreshold_2SFCA/` | CSV | City | Consistency checks for city-level 2SFCA accessibility under 1, 1.5, and 2--8 km thresholds. |

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

