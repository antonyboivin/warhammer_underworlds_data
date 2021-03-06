import csv
import json
import requests
import os

locales = ['en_UK']

gw_name_inaccuracies = {
    "Deathly Fortitude": "Deathly Fortune"
}

set_prefixes = {
    143: "L"
}

int_fields = [
    "glory",
    "id",
    "number"
]

EN = "en"
DE = "de"
supported_locales = [EN, DE]

def main():
    for locale in supported_locales:
        process_locale(locale)

def process_locale(locale):
    gw_data = fetch_gw_data(locale)
    cards = gw_to_cards(gw_data)
    gw_name_map = {}
    gw_number_map = {}
    for c in cards:
        gw_name_map[c["name"]] = c
        number = int(c["gw_number"])
        gw_number_map[number] = c

    csv_data = read_csv('cards-{}.csv'.format(locale))
    csv_name_map = {}
    for c in csv_data:
        name = c["name"]
        if name in gw_name_inaccuracies:
            name = gw_name_inaccuracies[name]
        if name not in gw_name_map:
            correct_name = gw_number_map[c["number"]]["name"]
            print("Name mismatch (#{}): {} -> {}".format(c["number"], name, correct_name))
            c["name"] = correct_name
            name = correct_name
        hydrate_card_with_gw_data(c, gw_name_map[name])
        intify(c)
        csv_name_map[name] = c

    with open('cards-Missing-{}.csv'.format(locale), 'w+') as missing_cards_csvfile:
        writer = csv.DictWriter(missing_cards_csvfile, fieldnames=cards[0].keys())
        writer.writeheader()
        for c in cards:
            if c["name"] not in csv_name_map:
                writer.writerow(c)

    with open('cards-{}.json'.format(locale), 'w+') as jsonfile:
        json.dump(list(csv_name_map.values()), jsonfile, sort_keys=True, indent=2)

    for c in csv_name_map.values():
        image_folder = os.path.join('card_images')
        if not os.path.isdir(image_folder):
            os.makedirs(image_folder)
        filepath = os.path.join(image_folder, c["image_filename"])
        if not os.path.exists(filepath):
            response = requests.get(c["image_url"], allow_redirects=True)
            with open(filepath, 'wb') as imgfile:
                imgfile.write(response.content)

def intify(c):
    for field in int_fields:
        try:
            c[field] = int(c[field])
        except:
            c[field] = 0
    return c

def hydrate_card_with_gw_data(card, gw):
    for key, value in gw.items():
        # we skip "name" here cause that's our identifier. We don't want to stomp it, ever.
        if key != "name" and key in card and card[key] != gw[key]:
            print("GW data for '{}' differs from data stored in CSV:\n  GW:  {}: {}\n  CSV: {}: {}".format(card["name"], key, gw[key], key, card[key]))
            print("Skipping field.")
            continue

        card[key] = value

    if card["gw_card_set_id"] in set_prefixes:
        card["set_prefix"] = set_prefixes[card["gw_card_set_id"]]

def fetch_gw_data(locale):
    locale_query = ""
    if locale != "en":
        locale_query = "&lang=" + locale
    url = "https://warhammerunderworlds.com/wp-json/wp/v2/cards/?ver=13&per_page=1000" + locale_query
    print(url)
    response = requests.get(url)
    if response.status_code != 200:
        print("Error ({}) fetching GW data".format(response.status_code))
        return None
    
    return response.json()

def gw_to_cards(gw_data):
    return [create_card_from_gw(gw) for gw in gw_data]

# some names in GW data are '123. Foo' and others are just 'Foo'
def normalize_name(name):   
    if '.' in name:
        name = '.'.join(name.split('.')[1:]).strip()
    return name.replace(u"\u2018", "'").replace(u"\u2019", "'").replace("&#8217;", "'").replace("&#8216;", "'")

def create_card_from_gw(gw):
    return {
        "gw_id": gw["id"],
        "name": normalize_name(gw["title"]["rendered"]),
        "gw_card_type_id": gw["card_types"][0],
        "gw_card_set_id": gw["sets"][0],
        "gw_warband_id": gw["warbands"][0],
        "gw_number": gw["acf"]["card_number"],
        "image_url": gw["acf"]["card_image"]["url"],
        "image_filename": gw["acf"]["card_image"]["filename"],
        "is_new": gw["acf"]["is_new"]
    }

def read_csv(csvpath):
    with open(csvpath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        return [intify(card) for card in reader]

main()