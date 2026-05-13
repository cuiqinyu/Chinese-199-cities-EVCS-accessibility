# Data Directory

Place public processed data products here.

Recommended first-release structure:

```text
data/
  2SFCA_1to8km_EVCS_Conservative_Map/
    a_1000mGrid_g2sfca_core.shp
    a_1000mGrid_g2sfca_core.dbf
    a_1000mGrid_g2sfca_core.shx
    a_1000mGrid_g2sfca_core.prj
    b_district_g2sfca_accessibility.*
    c_city_2sfca_accessibility.*
    d_province_g2sfca.*
```

Large files may be uploaded through GitHub Releases or Git LFS if needed.

Raw third-party EVCS platform records, map API responses, and API keys should not be committed.

