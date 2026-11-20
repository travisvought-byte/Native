// Draws the outlines of reservations and other tribal lands for the map, and the inside point of each.
// Source: U.S. Census Bureau cartographic boundary file of American Indian, Alaska Native and Native
// Hawaiian areas (1:500,000). Names are kept as the Census Bureau writes them.
//   npm install && npm run lands
// Writes data/map/lands.geojson (outlines, simplified) and data/map/land-points.json (inside points),
// which scripts/import_lands.py reads for map positions.
import mapshaper from 'mapshaper';
import { writeFile, mkdir } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const URL = 'https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_aiannh_500k.zip';
const dir = join(tmpdir(), 'ninas-map-lands');
await mkdir(dir, { recursive: true });
const zip = join(dir, 'lands.zip');
await writeFile(zip, Buffer.from(await (await fetch(URL)).arrayBuffer()));
execFileSync('unzip', ['-o', '-q', zip, '-d', dir]);
const shp = join(dir, 'cb_2023_us_aiannh_500k.shp');
await mapshaper.runCommands(`-i ${shp} -points inner -each 'lat=Math.round(this.y*1e4)/1e4, lon=Math.round(this.x*1e4)/1e4' -filter-fields GEOID,lat,lon -o data/map/land-points.json format=json`);
await mapshaper.runCommands(`-i ${shp} -simplify 6% keep-shapes -filter-fields GEOID,NAMELSAD,MTFCC -rename-fields id=GEOID,n=NAMELSAD,k=MTFCC -o data/map/lands.geojson format=geojson precision=0.001`);
console.log('wrote data/map/lands.geojson and data/map/land-points.json');
