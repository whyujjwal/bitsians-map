// Generates public/map/night.json from OpenFreeMap's positron layer structure (the
// "dark" style uses different layer ids), recoloured to the v3 night palette.
// Run once (node scripts/build-map-styles.mjs); the output is committed as a static file.
// Drops the raster source and everything except land, water, major roads, borders and labels.
import { mkdirSync, writeFileSync } from 'node:fs';

const P = {
  space: '#060C11', land: '#0E1A22', park: '#101F28', wood: '#101F28',
  country: '#21384A', state: '#172A36', road: 'rgba(241,161,10,0.28)',
  labelCountry: '#3B5566', labelCity: '#5E7A89', halo: '#0E1A22',
};
const KEEP = new Set([
  'background', 'park', 'water', 'landcover_wood',
  'highway_motorway_inner', 'highway_major_inner', 'boundary_3', 'boundary_2',
  'label_city', 'label_city_capital', 'label_town',
  'label_country_3', 'label_country_2', 'label_country_1',
]);

const res = await fetch('https://tiles.openfreemap.org/styles/positron');
if (!res.ok) throw new Error(`positron: ${res.status}`);
const base = await res.json();

const layers = [];
for (const l0 of base.layers) {
  if (!KEEP.has(l0.id)) continue;
  const l = structuredClone(l0);
  l.paint ??= {}; l.layout ??= {};
  switch (l.id) {
    case 'background': l.paint['background-color'] = P.land; break;
    case 'park': l.paint['fill-color'] = P.park; break;
    case 'landcover_wood': l.paint['fill-color'] = P.wood; break;
    case 'water': l.paint['fill-color'] = P.space; l.paint['fill-antialias'] = true; break;
    case 'highway_motorway_inner': case 'highway_major_inner':
      l.filter = JSON.parse(JSON.stringify(l.filter).replace('["primary","secondary","tertiary","trunk"]', '["primary","trunk"]'));
      l.minzoom = 7;
      l.layout = { 'line-cap': 'round', 'line-join': 'round' };
      l.paint = {
        'line-color': P.road, 'line-blur': 1,
        'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.4, 13, 2],
      };
      break;
    case 'boundary_2': l.paint = { 'line-color': P.country, 'line-width': 0.6 }; l.layout = {}; break;
    case 'boundary_3': l.minzoom = 4; l.paint = { 'line-color': P.state, 'line-width': 0.5, 'line-dasharray': [3, 2] }; break;
    default: { // symbol layers
      const country = l.id.startsWith('label_country');
      l.paint = {
        'text-color': country ? P.labelCountry : P.labelCity,
        'text-halo-color': P.halo, 'text-halo-width': 1.2, 'text-halo-blur': 0,
      };
      for (const k of ['icon-image', 'icon-size', 'icon-allow-overlap', 'icon-optional', 'text-transform', 'text-offset']) delete l.layout[k];
      l.layout['text-anchor'] = 'center';
      l.layout['text-font'] = ['Noto Sans Regular'];
      l.layout['text-size'] = country ? 11 : 12;
      // City labels start where the DOM city lights hand over to tiles (z9).
      if (!country) l.minzoom = 9;
    }
  }
  if (!Object.keys(l.layout).length) delete l.layout;
  layers.push(l);
}
const rank = (l) => (l.type === 'background' ? 0 : l.type === 'fill' ? 1 : l.id.startsWith('boundary') ? 2 : l.type === 'line' ? 3 : 4);
layers.sort((a, b) => rank(a) - rank(b));

const { ne2_shaded, ...sources } = base.sources;
const style = {
  version: 8, name: 'bitsians-night', sources, sprite: base.sprite, glyphs: base.glyphs,
  projection: { type: 'globe' },
  sky: {
    'sky-color': '#1E6A72', 'horizon-color': '#1E6A72', 'fog-color': '#060C11',
    'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.5, 'fog-ground-blend': 0.5,
    'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 4, 0.9, 6, 0],
  },
  layers,
};
mkdirSync('public/map', { recursive: true });
writeFileSync('public/map/night.json', JSON.stringify(style));
console.log('night', layers.length, 'layers');
