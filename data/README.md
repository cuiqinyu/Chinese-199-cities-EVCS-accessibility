# Data Directory

Place public processed data products here.

Recommended first-release structure, matching the current manuscript data-record table:

```text
data/
  TravelDistance/
    Nearest1to8EVCS/
      100m/     # city-split CSV files
      Merge/    # merged or aggregated SHP products
  2SFCA/
    1to8km/
      100m/     # city-split CSV files
      Merge/    # merged or aggregated SHP products
  Derivatives/
    DoubleIndex_Accessibility_Map/
    Accessibility_Gini_Map/
  Validation/
    EVCS_Dataset/
    DoubleMethods_TravelDistance/
    DifferentNearestEVCS_TravelDistance/
    DifferentDistanceThreshold_2SFCA/
```

Use the folder names exactly as listed above so that the repository structure remains consistent with the manuscript and `metadata/dataset_manifest.csv`.

Large files may be uploaded through GitHub Releases or Git LFS if needed. If files are released outside the git history, keep a small README or manifest entry in the corresponding folder that records the release asset name, checksum, and version.

Raw third-party EVCS platform records, map API responses, and API keys should not be committed.

