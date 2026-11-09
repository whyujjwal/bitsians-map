// Continent and state lookups for the location filter. The dataset stores city + country only,
// so states come from this table (every city in the data as of 2026-11-09). A city missing here
// still filters by country and continent; add it to STATE when new cities appear.

const CONTINENT: Record<string, string> = {
  India: 'Asia', UAE: 'Asia', Singapore: 'Asia', Indonesia: 'Asia',
  USA: 'North America', Canada: 'North America',
  UK: 'Europe', Iceland: 'Europe', Germany: 'Europe', France: 'Europe', Netherlands: 'Europe',
  Australia: 'Oceania',
};
export const continentOf = (country: string) => CONTINENT[country] ?? '';

const STATE: Record<string, Record<string, string>> = {
  India: {
    Ahmedabad: 'Gujarat', Barbil: 'Odisha', Bengaluru: 'Karnataka', Bhubaneswar: 'Odisha', Chennai: 'Tamil Nadu',
    Delhi: 'Delhi', Ghaziabad: 'Uttar Pradesh', Gurugram: 'Haryana', Hyderabad: 'Telangana', Jaipur: 'Rajasthan',
    Mumbai: 'Maharashtra', Noida: 'Uttar Pradesh', 'Verna, Goa': 'Goa', Pune: 'Maharashtra', Kolkata: 'West Bengal',
  },
  USA: {
    Atlanta: 'Georgia', Suwanee: 'Georgia', Bellevue: 'Washington', Seattle: 'Washington',
    Boston: 'Massachusetts', Cambridge: 'Massachusetts', Dedham: 'Massachusetts', 'Westford, Massachusetts': 'Massachusetts',
    Brooklyn: 'New York', 'New York': 'New York', Chicago: 'Illinois', Mundelein: 'Illinois', Herndon: 'Virginia',
    'North Brunswick': 'New Jersey', Plano: 'Texas', Raleigh: 'North Carolina',
    Belmont: 'California', Milpitas: 'California', 'Mountain View': 'California', 'Palo Alto': 'California',
    'Redwood City': 'California', 'Redwood Shores': 'California', 'San Francisco': 'California', 'San Jose': 'California',
    'San Mateo': 'California', 'San Ramon': 'California', 'Santa Clara': 'California', Sunnyvale: 'California',
  },
  UAE: { Dubai: 'Dubai' },
  Australia: { Sydney: 'New South Wales' },
  Indonesia: { Jakarta: 'Jakarta' },
  UK: { London: 'England' },
};
export const stateOf = (country: string, city: string) => STATE[country]?.[city] ?? '';
