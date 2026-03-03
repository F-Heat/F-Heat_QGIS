# F|Heat – Detaillierte Dateneingänge, Verarbeitung & Klassennutzung

---

## ═══ PHASE 1: DOWNLOAD ═══
**Klasse/Funktion:** `HeatNetTool.download_files()` (heat_net_tool.py)

```
Eingabe (GUI):       Stadt- oder Gemeindename (String, Dropdown aus gemarkungen_df)
                     Ausgabepfade (String, Dateisystem)

Interne Referenz:    gemarkungen_df   (internes CSV mit 'name', 'gemeinde', 'schluessel', 'bbox')

Download-Funktionen (src/download_files.py):
  file_list_from_URL_QGIS(url)         → ruft OpenGeoData NRW API ab → Dateiliste
  search_filename(files, city_id)      → filtert Dateiliste nach Gemeindeschlüssel
  read_file_from_zip_QGIS(url, ...)    → lädt ZIP, extrahiert .shp → GeoDataFrame
  get_shape_from_wfs(url, key, bbox, layer) → lädt Flurstücke via WFS → GeoDataFrame
  filter_df(name, df, parameter)       → filtert interne Tabelle nach Stadt/Gemeinde

Ausgabe:
  buildings_gdf  → Gebäude-Shapefile (.shp)
  streets_gdf    → Straßen-Shapefile (.shp)
  parcels_gdf    → Flurstück-Shapefile (.shp)
```

---

## ═══ PHASE 2: ADJUST FILES ═══
**Klassen:** `Buildings_adj`, `Streets_adj`, `Parcels_adj`, `spatial_join` (src/adjust_files.py)  
**Orchestrierung:** `HeatNetTool.adjust_files()` (heat_net_tool.py)

### 2a. Buildings_adj

| Schritt | Methode | Gelesene Felder | Erzeugte/Geänderte Felder |
|---------|---------|-----------------|---------------------------|
| Init    | `__init__(path, heat_att)` | alle Felder aus .shp, `heat_att` (z.B. `RW_WW`) | `self.gdf`, `self.heat_att` |
| Filter  | `gdf[gdf[heat_att]>0]` | `heat_att` (z.B. `RW_WW`) | Zeilen ohne Wärmebedarf entfernt |
| Typ/Alter | `add_LANUV_age_and_type()` | `GEBAEUDETY` (Format: "EFH_1960"), `WG_NWG` | `type` (EFH/MFH/NWG), `age_LANUV` |
| Merge   | `merge_buildings()` | `Flurstueck`, `citygml_fu`, `Fortschrei`, `type`, `Fest_ID`, `Nutzung`, `NF`, `RW_spez`, `RW`, `WW_spez`, `WW`, `RW_WW_spez`, `RW_WW`, `age_LANUV` | Geometrien aufgelöst, Werte aggregiert |
| ID      | `gdf.index` | Index | `new_ID` (Int32) |
| Spatial Join | `spatial_join(buildings, parcels, ['validFrom'])` | `geometry` (Gebäude + Flurstück), Flurstück.`validFrom` | `validFrom` auf Gebäude übertragen |
| Baualtersklasse | `add_BAK(bins, labels)` | `validFrom` (String "YYYY-MM-DD") | `BAK` (String, z.B. "1950-1969") |
| Lastprofil | `add_Vlh_Loadprofile(excel_building_info)` | `citygml_fu` (letzte 4 Stellen), `type` | `Lastprofil` (EFH/MFH/GHA/GMK/GKO), `Vlh` [h] |
| Filter 2 | `drop_unwanted()` | `Lastprofil` | Gebäude ohne Lastprofil entfernt |
| Leistung | `add_power()` | `heat_att`, `Vlh` | `power_th` [kW] |
| Spez. WB | `add_custom_heat_demand(wg_data, nwg_data)` | `BAK`, `Lastprofil`, `NF`, `citygml_fu` | `Spez_Waermebedarf`, `Waermebedarf` |
| Anschluss | `add_connect_option()` | – | `Anschluss` = 1 |
| Umbenennen | `rename_and_order_columns()` | alle obigen | Spalten umbenannt & geordnet |

**Excel-Eingaben (building_info.xlsx):**
- Sheet `database`: Felder `Funktion` (=citygml_fu letzte 4), `Lastprofil`, `Vlh`
- Sheet `Grunddaten_Gebaeude` (A:D, 13 Zeilen): `Baualtersklasse`, `Waerme_MFH kWh/m²·a`, `Waerme_EFH kWh/m²·a`
- Sheet `database` (auch): `Funktion`, `WVBRpEBF` (für NWG)

### 2b. Streets_adj

| Schritt | Methode | Gelesene Felder | Erzeugte/Geänderte Felder |
|---------|---------|-----------------|---------------------------|
| Init    | `__init__(path)` | `geometry` (LineString) | `self.gdf` |
| Runden  | `round_streets()` | `geometry` | `geometry` (auf 3 Dezimalstellen gerundet, MultiLineString → LineString) |
| Route   | `add_bool_column()` | – | `Moegliche_Route` = 1 |

### 2c. Parcels_adj

| Schritt | Methode | Gelesene Felder | Erzeugte/Geänderte Felder |
|---------|---------|-----------------|---------------------------|
| Init    | `__init__(path)` | `geometry` (Polygon), `validFrom` | `self.gdf` |

### 2d. spatial_join (Funktion)

| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `shape1`  | GeoDataFrame | Gebäude (Ziel) |
| `shape2`  | GeoDataFrame | Flurstücke (Quelle) |
| `attributes` | list | `['validFrom']` |
| Intern    | `intersection_area` | Größte Überlappung bestimmt Zuordnung |

---

## ═══ PHASE 3: STATUS-ANALYSE (WLD) ═══
**Klassen:** `WLD`, `Polygons` (src/status_analysis.py)  
**Orchestrierung:** `HeatNetTool.status_analysis()` (heat_net_tool.py)

### 3a. WLD (Wärmeliniendichte)

| Schritt | Methode | Gelesene Felder | Erzeugte/Geänderte Felder |
|---------|---------|-----------------|---------------------------|
| Init    | `__init__(buildings, streets)` | Gebäude-GDF, Straßen-GDF | `self.buildings`, `self.streets` |
| Zentroid | `get_centroid()` | `geometry` (Gebäude-Polygon) | `centroid` (Point) |
| Straße zuordnen | `closest_street_buildings()` | `centroid`, Straßen-`geometry` | `street_id` (Int) |
| Länge   | `add_lenght()` | Straßen-`geometry` | `length` [m] |
| Wärme   | `add_heat_att(heat_att)` | `heat_att` (z.B. `WB [kWh/a]`), `new_ID`, `street_id` | Straßen: `{heat_att}` (Float), `connected` (String "id1,id2,...") |
| WLD     | `add_WLD(heat_att)` | `{heat_att}`, `length` | `WLD [kWh/a*m]` |

### 3b. Polygons (Versorgungsgebiets-Polygone)

| Schritt | Methode | Gelesene Felder | Erzeugte/Geänderte Felder |
|---------|---------|-----------------|---------------------------|
| Init    | `__init__(parcels, wld, buildings)` | Alle drei GDFs | Instanzattribute |
| Parzel auswählen | `select_parcels_by_building_connection(WLD_value)` | `WLD [kWh/a*m]`, `connected`, `new_ID`, `geometry` | `selected_parcels` GDF |
| Buffer  | `buffer_dissolve_and_explode(buffer_distance)` | `selected_parcels` | `polygons` (gepuffert, aufgelöst) |
| Attribute | `add_attributes(heat_att, power_att)` | `geometry`, `heat_att`, `power_att` | `Area [m²]`, `Connections`, `Heat_Demand [kWh/a]`, `Power_th [kW]`, `Demand/Area [MWh/ha*a]`, `Mean_Power_th [kW]` |

---

## ═══ PHASE 4: NETZANALYSE ═══
**Klassen:** `Streets`, `Source`, `Buildings`, `Graph`, `Net` (src/net_analysis.py)  
**Orchestrierung:** `HeatNetTool.network_analysis()` (heat_net_tool.py)

### Nutzer-Eingaben (GUI):
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `t_supply` | Float (°C) | Vorlauftemperatur |
| `t_return` | Float (°C) | Rücklauftemperatur (< t_supply!) |
| `heat_attribute` | String | Wärmebedarfs-Attributname (z.B. `WB [kWh/a]`) |
| `power_attribute` | String | Leistungs-Attributname (z.B. `Leistung_th [kW]`) |
| Ausgabepfad Netz | Path | Speicherpfad für Netz-Shapefile |

### 4a. Source

| Schritt | Methode | Gelesene Felder | Erzeugte Felder |
|---------|---------|-----------------|-----------------|
| Init    | `__init__(path)` | `geometry` (Point) | `self.gdf` |
| Anschluss | `closest_points_sources(streets)` | `geometry`, Straßen-`geometry` | `Anschlusspunkt` (Point), `street_id` (Int) |

### 4b. Buildings (net_analysis)

| Schritt | Methode | Gelesene Felder | Erzeugte Felder |
|---------|---------|-----------------|-----------------|
| Init    | `__init__(path, heat_att)` | `heat_att` (filtert > 0), `geometry` | `self.gdf`, `self.buildings_all` |
| Zentroid | `add_centroid()` | `geometry` | `centroid` (Point) |
| Anschluss | `closest_points_buildings(streets)` | `centroid`, Straßen-`geometry` | `Anschlusspunkt` (Point), `street_id` (Int) |

### 4c. Streets (net_analysis)

| Schritt | Methode | Gelesene Felder | Erzeugte Felder |
|---------|---------|-----------------|-----------------|
| Init    | `__init__(path)` | `geometry` (LineString) | `self.gdf` |
| Anschlüsse einfügen | `add_connection_to_streets(buildings, sources)` | `street_id`, `Anschlusspunkt`, `geometry` | `geometry` (Anschlusspunkte eingefügt) |

### 4d. Graph

| Schritt | Methode | Gelesene Felder | Beschreibung |
|---------|---------|-----------------|--------------|
| Straßennetz | `create_street_network(streets)` | `geometry` | nx.Graph aus LineString-Koordinaten |
| Gebäude verbinden | `connect_centroids(buildings)` | `centroid`, `Anschlusspunkt` | Edge: centroid ↔ Anschlusspunkt |
| Quelle verbinden | `connect_source(sources)` | `geometry`, `Anschlusspunkt` | Edge: source ↔ Anschlusspunkt |
| Länge | `add_attribute_length()` | Knotenkoordinaten | Edge-Attribut `length [m]` |

### 4e. Net (Netzberechnung)

| Schritt | Methode | Eingaben | Ausgaben |
|---------|---------|---------|---------|
| Kürzester Pfad | `network_analysis(G, buildings, sources, pipe_info, power_th_att)` | Graph, `power_th_att`, `centroid`, Quelle | Netz-Graph mit `power_th [kW]`, `n_building` |
| Rohrattribute | `add_edge_attributes(pipe_info)` | `power_th [kW]`, `n_building`, `length [m]`, `type`, `htemp`, `ltemp`, `pipe_info` | `GLF`, `power_th_GLF [kW]`, `Volumeflow [l/s]`, `DN [mm]`, `velocity [m/s]`, `loss [kWh/a]`, `loss_extra [kWh/a]` |
| GDF konvertieren | `graph_to_gdf()` | Netz-Graph | `self.gdf` (GeoDataFrame LineStrings) |

**Berechnungsfunktionen (frei, net_analysis.py):**
- `calculate_GLF(n)` → Gleichzeitigkeitsfaktor GLF aus Gebäudeanzahl
- `calculate_volumeflow(kW_GLF, htemp, ltemp)` → Volumenstrom [l/s]
- `calculate_diameter_velocity_loss(volumeflow, htemp, ltemp, length, pipe_info, edge_type)` → DN, Geschwindigkeit, Verlust

**pipe_info (Excel, intern):**

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `DN` | Int | Rohrdurchmesser [mm] |
| `di` | Float | Innendurchmesser [mm] |
| `U-Value` | Float | Wärmedurchgangskoeffizient [W/(m·K)] |
| `U-Value_extra_insulation` | Float | U-Wert extra Dämmung |
| `v_max` | Float | Maximale Strömungsgeschwindigkeit [m/s] |
| `max_volumeFlow` | Float | Maximaler Volumenstrom [l/s] |

---

## ═══ PHASE 5: ERGEBNIS / LASTPROFIL ═══
**Klassen:** `Result`, `Temperature`, `LoadProfile` (src/net_analysis.py, src/load_curve.py)  
**Orchestrierung:** `HeatNetTool.create_result()` (heat_net_tool.py)

### 5a. Result

| Methode | Eingaben | Ausgaben |
|---------|---------|---------|
| `create_data_dict(buildings, net, types, dn_list, heat_att, h_temp, l_temp)` | Gebäude-GDF, Netz-GDF | `df` (Zusammenfassung), `statistic` (Rohrlängen, Verluste) |
| `save_in_excel(...)` | df | Excel-Datei |

### 5b. Temperature (optional, wenn kein CSV)

| Methode | Eingaben | Ausgaben |
|---------|---------|---------|
| `stationsfromtxt()` | DWD URL | GeoDataFrame aller Wetterstationen |
| `nearestStation(poi, gdf)` | Koordinaten (POI), Stationsliste | Nächste Wetterstation |
| `tempdata(url, station_id, start_date, end_date, n=10)` | Station-ID, Datumsbereich | Stündliche Temperaturen (10-Jahres-Mittel) [°C] |

### 5c. LoadProfile

| Methode | Eingaben | Ausgaben |
|---------|---------|---------|
| `__init__(net_result, excel_path, year, temperature_data, holidays)` | Result-Obj., Excel-Pfad, Jahr, Temperaturen, Feiertage | Instanz |
| `create_heat_demand_profile(type, class, wind_class, ww_incl, annual_demand)` | BDEW-Typ (EFH/MFH/...), Gebäudeklasse 1-11, Windklasse, WW inklusive, Jahreswärmebedarf [MWh] | Stündliches Lastprofil (8760 Werte) |
| `save_in_excel(df)` | Lastprofil-DataFrame | Excel-Sheet "Lastprofil" |

---

## ═══ ATTRIBUT-PFLICHTLISTE ═══

### ✅ PFLICHTATTRIBUTE – GEBÄUDE (.shp)

| Attribut | Datentyp | Genutzt in | Grund |
|----------|----------|------------|-------|
| `geometry` | Polygon | alle Phasen | räumliche Basis |
| `Flurstueck` | String | `merge_buildings()` | Merge-Schlüssel |
| `citygml_fu` | String | `merge_buildings()`, `add_Vlh_Loadprofile()`, `add_custom_heat_demand()` | Funktionsklasse (ALKIS-Code), letzte 4 Ziffern als Lookup-Key |
| `Fortschrei` | String | `merge_buildings()` | Merge-Schlüssel |
| `NF` | Float | `merge_buildings()` (sum), `add_custom_heat_demand()` | Nettofläche für Wärmebedarfsberechnung |
| `RW_WW` | Float | als `heat_att` genutzt (Standardwert) | Gesamtwärmebedarf → Filter + Leistungsberechnung |
| `GEBAEUDETY` | String | `add_LANUV_age_and_type()` | Extrahiert `type` und `age_LANUV` (Format: "EFH_1960") |
| `WG_NWG` | String | `add_LANUV_age_and_type()` | Klassifikation NWG → überschreibt `type` |
| `RW_spez` | Float | `merge_buildings()` (gewichteter Durchschnitt) | Spez. Raumwärme |
| `RW` | Float | `merge_buildings()` (sum) | Raumwärme gesamt |
| `WW_spez` | Float | `merge_buildings()` (gewichteter Durchschnitt) | Spez. Warmwasser |
| `WW` | Float | `merge_buildings()` (sum) | Warmwasser gesamt |
| `RW_WW_spez` | Float | `merge_buildings()` (gewichteter Durchschnitt) | Spez. Gesamt |
| `Fest_ID` | String | `merge_buildings()` (first) | Identifikator |
| `Nutzung` | String | `merge_buildings()` (first) | Nutzungsart |

### ✅ PFLICHTATTRIBUTE – STRASSEN (.shp)

| Attribut | Datentyp | Genutzt in | Grund |
|----------|----------|------------|-------|
| `geometry` | LineString | alle Phasen | Netzgeometrie, Routing |

### ✅ PFLICHTATTRIBUTE – FLURSTÜCKE (.shp)

| Attribut | Datentyp | Genutzt in | Grund |
|----------|----------|------------|-------|
| `geometry` | Polygon | `spatial_join()`, `Polygons` | Räumliche Zuordnung zu Gebäuden |
| `validFrom` | String (YYYY-MM-DD) | `spatial_join()` → `add_BAK()` | Baujahr → Baualtersklasse |

### ✅ PFLICHTATTRIBUTE – WÄRMEQUELLE (.shp, manuell)

| Attribut | Datentyp | Genutzt in | Grund |
|----------|----------|------------|-------|
| `geometry` | Point | `Source.closest_points_sources()`, `Graph.connect_source()`, `Net.network_analysis()` | Position der Wärmezentrale, Startpunkt für Routing |

### ✅ PFLICHTFELDER – building_info.xlsx (Sheet: database)

| Spalte | Datentyp | Genutzt in | Grund |
|--------|----------|------------|-------|
| `Funktion` | String (4-stellig) | `add_Vlh_Loadprofile()` | Lookup-Schlüssel = letzte 4 Stellen von `citygml_fu` |
| `Lastprofil` | String (EFH/MFH/GHA/GMK/GKO) | `add_Vlh_Loadprofile()`, `LoadProfile` | SLP-Profiltyp |
| `Vlh` | Float | `add_Vlh_Loadprofile()`, `add_power()` | Volllaststunden → Leistungsberechnung |
| `WVBRpEBF` | Float | `add_custom_heat_demand()` (NWG-Pfad) | Spez. Wärmebedarf NWG [kWh/(m²·a)] |

### ✅ PFLICHTFELDER – building_info.xlsx (Sheet: Grunddaten_Gebaeude, A:D, 13 Zeilen)

| Spalte | Datentyp | Genutzt in | Grund |
|--------|----------|------------|-------|
| `Baualtersklasse` | String | `add_custom_heat_demand()` (WG-Pfad) | Altersklassen-Lookup |
| `Waerme_MFH kWh/m²·a` | Float | `add_custom_heat_demand()` | Spez. Wärmebedarf MFH |
| `Waerme_EFH kWh/m²·a` | Float | `add_custom_heat_demand()` | Spez. Wärmebedarf EFH |

### ✅ PFLICHTFELDER – pipe_info / result.xlsx (intern)

| Spalte | Datentyp | Genutzt in | Grund |
|--------|----------|------------|-------|
| `DN` | Int | `calculate_diameter_velocity_loss()` | Rohrdurchmesser |
| `di` | Float | `calculate_diameter_velocity_loss()` | Innendurchmesser |
| `U-Value` | Float | `calculate_diameter_velocity_loss()` | Wärmeverlustberechnung |
| `U-Value_extra_insulation` | Float | `calculate_diameter_velocity_loss()` | Verlust extra Dämmung |
| `max_volumeFlow` | Float | `calculate_diameter_velocity_loss()` | Rohrdimensionierung |

### ✅ PFLICHTPARAMETER – GUI (Nutzer)

| Parameter | Datentyp | Genutzt in | Grund |
|-----------|----------|------------|-------|
| `t_supply` (°C) | Float | `Net.__init__()`, `calculate_volumeflow()`, `calculate_diameter_velocity_loss()` | Vorlauftemperatur |
| `t_return` (°C) | Float | `Net.__init__()`, `calculate_volumeflow()`, `calculate_diameter_velocity_loss()` | Rücklauftemperatur |
| Stadt/Gemeinde | String | `filter_df()`, `search_filename()` | Auswahl des Gebiets |
| Wärmeattribut | String | `Buildings_adj.__init__()`, `WLD.add_heat_att()`, `Buildings.__init__()` | Auswahl welches Attribut als Wärmebedarf gilt |
| Leistungsattribut | String | `Net.network_analysis()`, `Polygons.add_attributes()` | Auswahl welches Attribut als Leistung gilt |

---

## ═══ NICHT-PFLICHT-ATTRIBUTE (optionale Felder) ═══

### ❌ OPTIONALE ATTRIBUTE – GEBÄUDE

| Attribut | Datentyp | Grund für Optional |
|----------|----------|--------------------|
| `Alter_LANUV` / `age_LANUV` | String | Nur für Anzeige im Output, keine Berechnung davon abhängig |
| `BAK nach Flurstueck` | String | Wird intern erzeugt – kein Eingangsfeld |
| `Anschluss` | Int (0/1) | Kann vom Nutzer nachträglich auf 0 gesetzt werden; Standard=1; Netzanalyse filtert danach |
| `Alter_Flurstueck` | String | Nur Anzeige (aus `validFrom` abgeleitet) |

### ❌ OPTIONALE EINGABEN / PHASEN

| Eingabe | Genutzt in | Grund für Optional |
|---------|------------|--------------------|
| `Versorgungsgebiet-Polygon` (.shp) | `HeatNetTool.network_analysis()` | Ohne Polygon = alle Gebäude werden berücksichtigt |
| `Temperaturdaten` (CSV/Excel) | `LoadProfile.__init__()` | Wird automatisch vom DWD geladen wenn nicht angegeben |
| `Windklasse` (GUI) | `LoadProfile.create_heat_demand_profile()` | Hat Standardwert |
| `Gebäudeklasse 1-11` (GUI) | `LoadProfile.create_heat_demand_profile()` | Hat Standardwert (NRW=3) |
| `WW inkl.` (GUI-Checkbox) | `LoadProfile.create_heat_demand_profile()` | Standardwert vorhanden |
| `Moegliche_Route` auf Straßen | `Graph.create_street_network()` | Wird auf 1 gesetzt; Nutzer kann es manuell auf 0 setzen um Straßen auszuschließen |

### ❌ OPTIONALE ATTRIBUTE – FLURSTÜCKE (vom WFS)

| Attribut | Grund für Optional |
|----------|--------------------|
| `nationalCadastralReference` | Wird nur für WFS-internen Filter genutzt; im gespeicherten SHP nicht weiterverwendet |
| alle anderen WFS-Attribute | Nur `geometry` und `validFrom` werden weiterverarbeitet |

### ❌ OPTIONALE ATTRIBUTE – STRASSEN

| Attribut | Grund für Optional |
|----------|--------------------|
| Alle Originalattribute | Nur `geometry` wird verarbeitet; alle anderen werden ignoriert |