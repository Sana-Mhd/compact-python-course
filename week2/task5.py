events = {
    "DEW21 Museumsnacht": "19.09.2026",
    "Naturmuseum Dortmund - Pantomime Bastian": "19.09.2026",
    "Museum fuer Kunst und Kulturgeschichte - Guided Tours": "19.09.2026",
    "Dortmunder U - 3D Fassadenmapping": "19.09.2026",
    "Konzerthaus Dortmund - Live Music": "19.09.2026",
    "Deutsches Fussballmuseum - Exhibition": "19.09.2026",
    "Hoesch-Museum - Carrerabahn and Fotobox": "19.09.2026",
    "Kindermuseum Adlerturm - Ritter Fuehrung": "19.09.2026",
    "Baukunstarchiv NRW - Moderne Kunst": "19.09.2026",
    "Dortmunder Kunstverein - Noise Workshop": "19.09.2026",
    "Marquess Concert at Friedensplatz": "19.09.2026",
    "Musikfeuerwerk over Rathaus": "19.09.2026",
    "Weihnachtsmarkt Dortmund": "19.11.2026",
    "BVB vs Bayern Muenchen": "05.10.2026"
}
 
search_date = "19.09.2026"
print("Events during Night of Museums on", search_date + ":")
 
for event, date in events.items():
    if date == search_date:
        print("-", event)
