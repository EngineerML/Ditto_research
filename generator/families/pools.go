package families

var cities = []string{
	"Lisbon", "Tallinn", "Porto", "Ljubljana", "Valencia", "Krakow", "Bergen",
	"Ghent", "Bologna", "Tbilisi", "Seville", "Gdansk", "Leipzig", "Utrecht",
	"Aarhus", "Brno", "Cluj", "Graz", "Malmo", "Riga", "Turku", "Vilnius",
	"Zadar", "Lyon", "Nantes", "Bilbao", "Salzburg", "Plovdiv", "Tartu", "Split",
	"Coimbra", "Trieste", "Kaunas", "Pecs", "Bratislava", "Uppsala", "Lille",
	"Groningen", "Innsbruck", "Varna", "Debrecen", "Oulu", "Antwerp", "Bruges",
	"Rotterdam", "Eindhoven", "Maastricht", "Hamburg", "Dresden", "Freiburg",
	"Heidelberg", "Nuremberg", "Bremen", "Hanover", "Zurich", "Basel", "Geneva",
	"Lausanne", "Lucerne", "Vienna", "Linz", "Prague", "Ostrava", "Olomouc",
	"Wroclaw", "Poznan", "Lublin", "Szeged", "Budapest", "Timisoara", "Iasi",
	"Sibiu", "Burgas", "Skopje", "Ohrid", "Belgrade", "Novi Sad", "Zagreb",
	"Rijeka", "Sarajevo", "Mostar", "Podgorica", "Tirana", "Thessaloniki",
	"Patras", "Heraklion", "Naples", "Palermo", "Turin", "Verona", "Genoa",
	"Parma", "Padua", "Marseille", "Bordeaux", "Toulouse", "Strasbourg",
	"Montpellier", "Rennes", "Grenoble", "Granada", "Malaga", "Zaragoza",
	"Cordoba", "Santander", "Oviedo", "Braga", "Faro", "Aveiro", "Cork", "Galway",
	"Limerick", "Belfast", "Glasgow", "Edinburgh", "Aberdeen", "Cardiff",
	"Bristol", "Leeds", "Oslo", "Trondheim", "Stavanger", "Gothenburg", "Lund",
	"Odense", "Aalborg", "Tampere", "Espoo", "Helsinki", "Reykjavik", "Akureyri",
	"Osaka", "Kyoto", "Sapporo", "Fukuoka", "Nagoya", "Busan", "Daegu", "Incheon",
	"Taipei", "Kaohsiung", "Hanoi", "Da Nang", "Bangkok", "Chiang Mai", "Penang",
	"Ipoh", "Cebu", "Davao", "Jakarta", "Bandung", "Surabaya", "Yogyakarta",
	"Kathmandu", "Pokhara", "Colombo", "Kandy", "Mumbai", "Pune", "Jaipur",
	"Udaipur", "Kochi", "Mysore", "Chennai", "Hyderabad", "Lahore", "Karachi",
	"Muscat", "Doha", "Amman", "Beirut", "Tunis", "Marrakesh", "Fez", "Casablanca",
	"Dakar", "Accra", "Kumasi", "Lagos", "Nairobi", "Mombasa", "Arusha", "Kigali",
	"Kampala", "Lusaka", "Harare", "Windhoek", "Durban", "Cape Town", "Montreal",
	"Quebec City", "Halifax", "Calgary", "Winnipeg", "Vancouver", "Seattle",
	"Portland", "Denver", "Memphis", "Boston", "Chicago", "Detroit", "Phoenix",
	"Tucson", "Oaxaca", "Puebla", "Merida", "Guadalajara", "Havana", "Bogota",
	"Medellin", "Cali", "Quito", "Cuenca", "Lima", "Cusco", "Arequipa", "La Paz",
	"Santiago", "Valparaiso", "Mendoza", "Rosario", "Montevideo", "Asuncion",
	"Recife", "Curitiba", "Manaus", "Auckland", "Wellington", "Hobart", "Perth",
	"Adelaide", "Brisbane", "Darwin",
}

// Pool sizes bound MaxCases: each round of the four default families draws at
// most 10 cities, 5 names and 2 drinks, and Builder.Pick never reuses a value
// within a pack. Events are drawn with Builder.Any, since a reserved name
// already makes each question unique. MaxCases (80, twenty rounds) therefore
// needs at least 200 cities, 100 names and 40 drinks; TestPoolsFillMaxCases
// holds that. Values must also stay apart:
// no value may contain another value from any pool, so one case's gold can
// never ground or decoy another's.

var firstNames = []string{
	"Ines", "Tobias", "Marisol", "Henrik", "Aiyana", "Dmitri", "Noor", "Callum",
	"Yuki", "Bastian", "Leilani", "Oskar", "Priya", "Teodor", "Ama", "Rasmus",
	"Zofia", "Emeka", "Liesel", "Joaquin", "Saoirse", "Kenji", "Farida", "Mateo",
	"Ingrid", "Tariq", "Ottilie", "Ravi", "Signe", "Dario", "Hana", "Lorcan",
	"Mirela", "Anselm", "Keziah", "Bram", "Yasmin", "Florin", "Thandiwe", "Ilan",
	"Wren", "Casimir", "Odalys", "Pavel", "Nkiru", "Soren", "Ximena", "Halvard",
	"Annika", "Dagny", "Kofi", "Rosalind", "Adaeze", "Bjorn", "Celestine",
	"Darius", "Elodie", "Fintan", "Gisela", "Hamish", "Ifeoma", "Jarrah",
	"Katarina", "Leopold", "Magnus", "Nadia", "Orla", "Philippa", "Quentin",
	"Rhiannon", "Stellan", "Tamsin", "Ulrich", "Valentina", "Wilhelmina",
	"Xavier", "Yara", "Zoltan", "Anouk", "Benedikt", "Cosima", "Desmond",
	"Esperanza", "Fabian", "Greta", "Horatio", "Imogen", "Jovan", "Klaus",
	"Ludmila", "Mihail", "Nikolai", "Ophelia", "Piotr", "Radu", "Svetlana",
	"Thaddeus", "Vesna", "Wolfgang", "Yevgenia", "Zuzana", "Agnieszka", "Bartosz",
	"Cormac", "Dorotea", "Eamon", "Fenna", "Gunnar", "Hedda", "Ignatius",
	"Jolanda", "Kasimir", "Lavinia", "Marek", "Niamh", "Olafur", "Petra",
	"Ragnhild", "Sebastiano", "Tomasz", "Ursula", "Viktor", "Wiebke", "Yannick",
	"Zelda", "Aurelio", "Beatrix", "Cyprian", "Delphine", "Emrys", "Frieda",
}

var events = []string{
	"team offsite", "book club retreat", "alumni reunion", "product summit",
	"family reunion", "choir tour", "wedding rehearsal", "charity gala",
	"hackathon", "quiz night", "garden party", "board game night",
	"cooking class", "film screening", "photo walk", "baby shower",
	"retirement party", "housewarming", "chess tournament", "pottery workshop",
	"wine tasting", "farewell dinner", "science fair", "yoga retreat",
	"trivia final", "sailing regatta",
}

var drinksPool = []string{
	"espresso", "matcha", "rooibos", "kombucha", "chai", "yerba mate",
	"cold brew", "oat latte", "green tea", "hot chocolate", "kefir", "cortado",
	"hojicha", "corn silk tea", "turmeric latte", "lassi", "genmaicha", "americano",
	"flat white", "ginger tea", "sencha", "mint tea", "macchiato", "chamomile",
	"golden milk", "pu-erh", "horchata", "earl grey", "lapsang souchong",
	"oolong", "jasmine tea", "hibiscus tea", "lemon verbena", "rosehip tea",
	"nettle tea", "dandelion coffee", "chicory coffee", "mocha", "affogato",
	"ristretto", "lungo", "cappuccino", "cafe au lait", "turkish coffee",
	"vietnamese coffee", "bubble tea", "yuzu tea", "sparkling water",
	"carrot juice", "beet juice", "apple cider", "elderflower cordial",
	"ginger beer", "kvass", "ayran", "chaga tea", "guayusa", "cascara", "bancha",
	"kukicha", "gyokuro", "white tea", "drip coffee", "piccolo", "red eye",
	"breve", "sikhye",
}

var filler = [][2]string{
	{"Remind me to water the plants on Thursday.", "I'll remind you Thursday."},
	{"Watched a documentary about octopuses last night.", "They're fascinating."},
	{"Thinking about learning to bake sourdough.", "Start with a simple starter."},
	{"It's been unusually windy this week.", "Windy weeks can be draining."},
	{"Need to renew my passport sometime this year.", "Worth starting early."},
	{"My bike chain keeps slipping on hills.", "It might need a new chain or a tune-up."},
	{"Finally finished the jigsaw puzzle, all thousand pieces.", "That's a satisfying feeling."},
	{"The neighbours are redoing their kitchen, so it's loud all day.", "Noise-cancelling headphones might help."},
	{"I keep forgetting where I put my reading glasses.", "A fixed spot by the door can help."},
	{"Started journaling before bed.", "That's a nice way to wind down."},
	{"My laptop fan has been really loud lately.", "Cleaning the vents often fixes that."},
	{"Got a parking ticket outside the library, annoying.", "Sorry, that's frustrating."},
	{"Thinking of repainting the hallway a lighter colour.", "Lighter colours make hallways feel bigger."},
	{"The new season of that detective show is out.", "Enjoy the binge."},
	{"I signed up for a beginner pottery class online.", "Sounds like a relaxing hobby."},
	{"My phone screen cracked again.", "A sturdier case might be worth it."},
	{"We're thinking about getting a rescue dog.", "Rescue dogs can be wonderful companions."},
	{"Spent the whole weekend sorting old photos.", "That can bring back a lot of memories."},
	{"The printer at work jammed three times today.", "Printers have a talent for bad timing."},
	{"Trying to drink more water during the day.", "A marked bottle can help you keep track."},
	{"I should really back up my files this week.", "Good idea, before something goes wrong."},
	{"Had a strange dream about missing a train.", "Those dreams are surprisingly common."},
	{"The streetlight outside my window keeps flickering.", "Worth reporting it to the council."},
	{"I'm trying to read one book a month this year.", "That's a very doable goal."},
	{"Our team switched to a new chat app at work.", "Switching tools always takes some getting used to."},
	{"My houseplant finally put out a new leaf.", "Nice, it must like its spot."},
	{"Forgot my umbrella and got soaked on the way home.", "Hope you dried off quickly."},
	{"Looking for a good podcast for my commute.", "Do you prefer stories or interviews?"},
	{"The gym was packed this morning.", "Early mornings get busy after the holidays."},
	{"I've been meaning to call my grandmother.", "She'd probably love to hear from you."},
}
