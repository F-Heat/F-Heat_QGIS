# Changelog

Alle relevanten Änderungen am Plugin werden hier dokumentiert.

## [Unreleased] - 2026-02-18

### Fixed

#### 1) Bestandsanalyse: `IndexError: single positional indexer is out-of-bounds`
**Betroffene Datei:** `FHeat_QGIS/src/status_analysis.py`
**Betroffene Methode:** `Polygons.select_parcels_by_building_connection(...)`

**Fehlerbild**
- Beim Ausführen der Bestandsanalyse mit externen Daten trat ein `IndexError` auf:
  - `single positional indexer is out-of-bounds`
- Der Fehler wurde in der Berechnung von `overlap_area` ausgelöst.

**Ursache**
- Nach `gpd.sjoin(...)` wurde `index_right` als Positionsindex behandelt und mit `.iloc[...]` adressiert.
- `index_right` enthält bei GeoPandas-Join jedoch Index-Labels des rechten DataFrames.
- Bei nicht-sequentiellen/externen Indizes führt das zu Out-of-Bounds-Zugriffen.

**Implementierter Fix**
- Zugriff von positionsbasiert auf labelbasiert umgestellt:
  - `.iloc[...]` ➜ `.loc[...]`
- Vor der Überlappungsberechnung zusätzliche Bereinigung:
  - `dropna(subset=['index_right'])`
  - `index_right` explizit nach `int` konvertiert
- Leere Join-Ergebnisse werden sauber abgefangen:
  - bei `join_result.empty` wird `overlap_area` defensiv gesetzt

**Ergebnis**
- Robuste Flächenüberlappungsberechnung auch bei externen Datensätzen mit nicht-fortlaufenden Indizes.
- Der ursprüngliche Index-Fehler tritt nicht mehr auf.

---

#### 2) Netzwerkanalyse: `NotImplementedError` bei Multi-Part-Geometrien
**Betroffene Datei:** `FHeat_QGIS/src/net_analysis.py`
**Betroffene Stellen:** Verarbeitung von Straßengeometrien in:
- `Source.closest_points_sources(...)`
- `Streets.add_connection_to_streets(...)`
- `Graph.create_street_network(...)`

**Fehlerbild**
- Beim Start der Netzwerkanalyse trat folgender Fehler auf:
  - `NotImplementedError: Sub-geometries may have coordinate sequences, but multi-part geometries do not`

**Ursache**
- Direkter Zugriff auf `.coords` wurde auf Geometrien angewendet, die `MultiLineString` (oder andere Multi-Part-Typen) sein können.
- `.coords` ist in Shapely für Multi-Part-Geometrien nicht direkt implementiert.

**Implementierter Fix**
- Einführung einer robusten Hilfsfunktion:
  - `_line_parts(geometry)`
- Verhalten der Hilfsfunktion:
  - `None`/leer ➜ `[]`
  - `LineString` ➜ `[geometry]`
  - `MultiLineString` ➜ Liste aller `LineString`-Teile
  - Geometrien mit `.geoms` ➜ gefilterte `LineString`-Teile
- Alle relevanten Routinen iterieren nun über `_line_parts(...)` statt direkt über `geometry.coords`.
- Zusätzliche Schutzlogik:
  - Wenn keine valide Liniengeometrie gefunden wird, wird kein Absturz ausgelöst (defensive Behandlung).

**Ergebnis**
- Netzwerkanalyse läuft stabil mit Multi-Part-Straßengeometrien.
- Der `NotImplementedError` durch `.coords` auf Multi-Geometrien ist behoben.

---

#### 3) Bestandsanalyse: `ValueError: GeoDataFrame cannot contain duplicated column names`
**Betroffene Datei:** `FHeat_QGIS/heat_net_tool.py`
**Betroffene Methoden:** `HeatNetTool.status_analysis(...)` und `HeatNetTool.on_task_finished(...)`

**Fehlerbild**
- Beim wiederholten Ausführen der Bestandsanalyse auf bereits verarbeiteten Dateien trat folgender Fehler beim Speichern auf:
  - `ValueError: GeoDataFrame cannot contain duplicated column names`

**Ursache**
- Beim erneuten Laden und Bearbeiten von Straßen-/Polygon-Dateien, die in einem vorherigen Lauf bereits mit Attributspalten (`connected`, `WLD [kWh/a*m]`, `Laenge` usw.) befüllt wurden, werden diese Spalten durch `sjoin` oder `merge`-Operationen wie dupliziert.
- `GeoDataFrame.to_file(...)` wirft bei duplizierten Spaltennamen einen Fehler.

**Implementierter Fix**
- Nach Abschluss der WLD-Berechnung und vor den `to_file`-Aufrufen:
  ```python
  wld_streets = wld_streets.loc[:, ~wld_streets.columns.duplicated()]
  pol_polygons = pol_polygons.loc[:, ~pol_polygons.columns.duplicated()]
  ```
- Defensive Deduplizierung an zwei Stellen implementiert: direkt nach der Analyse und unmittelbar vor dem Speichern.

**Ergebnis**
- Wiederholte Ausführung der Bestandsanalyse auf zuvor verarbeiteten Dateien wirft keinen Fehler mehr.

---

#### 4) Bestandsanalyse: 274 Gebäude fehlen in der Parzellen-Aggregation
**Betroffene Datei:** `FHeat_QGIS/src/status_analysis.py`
**Betroffene Methode:** `Polygons.select_parcels_by_building_connection(...)`

**Fehlerbild**
- Bei Verwendung des Testdatensatzes `kea_bw` wurden mit dem ursprünglichen Algorithmus 274 von 3093 Gebäuden nicht in der Ergebnispolygonschicht repräsentiert (2819/3093 abgedeckt).
- Kein Fehler oder Warnung – die Gebäude wurden still verworfen.

**Ursache**
- Die Parzellenauswahl basierte auf einem flächenbasierten Coverage-Schwellwert von 10 % (Überschneidungsfläche / Gebäudefläche ≥ 0,1).
- Alle 274 fehlenden Gebäude besitzen `MultiPolygon`-Geometrie und überspannen mehrere Flurstückgrenzen.
- Keine einzelne Parzelle erfasste dabei ≥ 10 % der Gebäudefläche, weshalb das `groupby().first()`-Muster diese Gebäude nicht auswählte.
- Diagnose: Zentroid-Test bestätigte, dass alle 274 Zentroide innerhalb einer Parzelle liegen – die Daten sind konsistent, der Algorithmus war zu restriktiv.

**Implementierter Fix**
Zweistufige Parzellenauswahl:

**Stufe 1 – Primär (flächenbasiert, Schwellwert ≥ 10 %):**
- Unveränderte Logik: `coverage_ratio = overlap_area / building_area`, bestes Match pro Parzelle, Schwellwert ≥ 0,1.

**Stufe 2 – Fallback (zentroidbasiert, kein Schwellwert):**
- Für alle Gebäude ohne Abdeckung durch Stufe 1:
  1. Gebäude-Zentroide als Geometrie setzen: `set_geometry('centroid')`
  2. Räumlicher Join mit Parzellen: `gpd.sjoin(..., predicate='within')`
  3. Passende `join_result`-Zeile per `(new_ID, parcel_idx)`-Paar lookupbasiert auswählen
  4. Bei fehlendem Treffer: Fallback auf die Zeile mit höchster Coverage im `sorted_joined`
- CRS des Fallback-DataFrames wird bei Bedarf an die primäre Auswahl angeglichen.
- Beide Stufen werden mit `pd.concat` zusammengeführt. Dopppelte Parzellen sind zulässig (Geometrie-basiertes `dissolve()` in `buffer_dissolve_and_explode` verarbeitet sie korrekt).

**Ergebnis**
- **3093/3093 Gebäude** abgedeckt (vorher 2819/3093).
- 321 Ergebnispolygone, vollständige Pipeline ohne Fehler verifiziert.

---

### Neu

#### `tests/aggregating_approaches/aggregating_geodata.py`
**Zweck:** MST-basierte Gebäudaggregation für reale Gebäude-NRW-Daten (Endstruktur-Format)

**Funktionen:**
- Liest `Gebaeude_NRW_Endstruktur_KEA.gpkg` direkt ein
- Räumlicher Join mit `Flurstücke_Geometrie_NRW_Endstruktur.gpkg` für Flurstückzuordnung
- Einheitenschätzung: `NF [m²] / 60`
- Verarbeitet Spalten `WB [kWh/a]`, `Spez_WB [kWh/a*m²]`, `Lastprofil`
- MST-basierte Aggregation mit `MIN_UNITS = 5` (Mindestanzahl Wohneinheiten je Gruppe)
- Optionaler Parameter `MIN_BUILDINGS`: Mindestanzahl Gebäude je Gruppe (zusätzlich zu `MIN_UNITS`)
- CLI-Unterstützung: `--min-buildings N`
- Standardausgabe: `testdata/output_results/aggregated_groups.gpkg`

**Verifiziert:** 1096 Gruppen aus 3096 Gebäuden (Testlauf `kea_bw`)

---

### Hinweise zur Auslieferung / Test

- Wenn QGIS das Plugin aus dem Profilpfad lädt, müssen Änderungen dorthin übernommen werden:
  - `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\FHeat_QGIS`
- Nach Deployment Plugin neu laden (oder QGIS neu starten) und:
  1. Bestandsanalyse mit externen Flurstück-/Gebäude-/Straßendaten erneut ausführen
  2. Netzwerkanalyse mit Datensätzen inkl. Multi-Part-Straßen verifizieren
  3. Wiederholten Analysedurchgang auf bereits verarbeiteten Dateien testen (Fix 3)
  4. Vollabdeckung der Gebäude in Ergebnispolygonen prüfen (Fix 4)
