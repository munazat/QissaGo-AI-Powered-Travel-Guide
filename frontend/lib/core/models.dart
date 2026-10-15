// Data classes for what the API returns.

int _int(dynamic v) => (v as num?)?.toInt() ?? 0;
double _double(dynamic v) => (v as num?)?.toDouble() ?? 0;
String _str(dynamic v) => v == null ? '' : v.toString();
List<String> _strings(dynamic v) => (v as List? ?? const []).map((e) => e.toString()).toList();

class AppUser {
  final int id;
  final String name;
  final String email;

  const AppUser({required this.id, required this.name, required this.email});

  factory AppUser.fromJson(Map<String, dynamic> j) =>
      AppUser(id: _int(j['id']), name: _str(j['name']), email: _str(j['email']));

  Map<String, dynamic> toJson() => {'id': id, 'name': name, 'email': email};
}

class City {
  final String id;
  final String name;
  final String province;
  final String image;
  final String description;
  final int places;

  const City({
    required this.id,
    required this.name,
    required this.province,
    required this.image,
    required this.description,
    required this.places,
  });

  factory City.fromJson(Map<String, dynamic> j) => City(
        id: _str(j['id']),
        name: _str(j['name']),
        province: _str(j['province']),
        image: _str(j['image']),
        description: _str(j['description']),
        places: _int(j['places']),
      );
}

class Option {
  final String id;
  final String label;

  const Option(this.id, this.label);

  factory Option.fromJson(Map<String, dynamic> j) => Option(_str(j['id']), _str(j['label']));
}

class Meta {
  final List<City> cities;
  final List<Option> interests;
  final List<Option> needs;

  const Meta({required this.cities, required this.interests, required this.needs});

  factory Meta.fromJson(Map<String, dynamic> j) => Meta(
        cities: (j['cities'] as List? ?? []).map((e) => City.fromJson(e as Map<String, dynamic>)).toList(),
        interests: (j['interests'] as List? ?? []).map((e) => Option.fromJson(e as Map<String, dynamic>)).toList(),
        needs: (j['needs'] as List? ?? []).map((e) => Option.fromJson(e as Map<String, dynamic>)).toList(),
      );

  City? city(String id) {
    for (final c in cities) {
      if (c.id == id) return c;
    }
    return null;
  }
}

class ChatTurn {
  final String sessionId;
  final String reply;
  final List<String> suggestions;
  final String awaiting;
  final bool ready;
  final String action;
  final Map<String, dynamic> preferences;

  const ChatTurn({
    required this.sessionId,
    required this.reply,
    required this.suggestions,
    required this.awaiting,
    required this.ready,
    required this.action,
    required this.preferences,
  });

  factory ChatTurn.fromJson(Map<String, dynamic> j) => ChatTurn(
        sessionId: _str(j['session_id']),
        reply: _str(j['reply']),
        suggestions: _strings(j['suggestions']),
        awaiting: _str(j['awaiting']),
        ready: j['ready'] == true,
        action: _str(j['action']),
        preferences: (j['preferences'] as Map?)?.cast<String, dynamic>() ?? {},
      );
}

class ChatMessage {
  final bool fromUser;
  final String text;

  const ChatMessage({required this.fromUser, required this.text});
}

class Weather {
  final int tmax;
  final int tmin;
  final int rainPct;
  final String icon;
  final String text;
  final String source;

  const Weather({
    required this.tmax,
    required this.tmin,
    required this.rainPct,
    required this.icon,
    required this.text,
    required this.source,
  });

  factory Weather.fromJson(Map<String, dynamic> j) => Weather(
        tmax: _int(j['tmax']),
        tmin: _int(j['tmin']),
        rainPct: _int(j['rain_pct']),
        icon: _str(j['icon']),
        text: _str(j['text']),
        source: _str(j['source']),
      );
}

class Leg {
  final double km;
  final int minutes;
  final int cost;

  /// "jeep" when the day's hired jeep covers this drive.
  final String mode;

  const Leg({required this.km, required this.minutes, required this.cost, this.mode = ''});

  bool get byJeep => mode == 'jeep';

  factory Leg.fromJson(Map<String, dynamic> j) =>
      Leg(km: _double(j['km']), minutes: _int(j['minutes']), cost: _int(j['cost']), mode: _str(j['mode']));
}

/// One row in a day: a place to visit ("stop") or a break ("lunch" / "rest").
class PlanItem {
  final String kind;
  final String type;
  final String id;
  final String name;
  final String category;
  final List<String> tags;
  final String start;
  final String end;
  final int minutes;
  final int costGroup;
  final bool outdoor;
  final double lat;
  final double lon;
  final String image;
  final String imageCredit;
  final String imageLicense;
  final String description;
  final String wikiUrl;
  final String mapUrl;
  final String osmUrl;
  final String weatherNote;
  final String open;
  final String close;
  final Leg? leg;

  const PlanItem({
    required this.kind,
    required this.type,
    required this.id,
    required this.name,
    required this.category,
    required this.tags,
    required this.start,
    required this.end,
    required this.minutes,
    required this.costGroup,
    required this.outdoor,
    required this.lat,
    required this.lon,
    required this.image,
    required this.imageCredit,
    this.imageLicense = '',
    required this.description,
    required this.wikiUrl,
    required this.mapUrl,
    required this.osmUrl,
    required this.weatherNote,
    required this.open,
    required this.close,
    this.leg,
  });

  bool get isStop => kind == 'stop';

  factory PlanItem.fromJson(Map<String, dynamic> j) => PlanItem(
        kind: _str(j['kind']),
        type: _str(j['type']),
        id: _str(j['id']),
        name: _str(j['name'] ?? j['title']),
        category: _str(j['category']),
        tags: _strings(j['tags']),
        start: _str(j['start']),
        end: _str(j['end']),
        minutes: _int(j['minutes']),
        costGroup: _int(j['cost_group']),
        outdoor: j['outdoor'] == true,
        lat: _double(j['lat']),
        lon: _double(j['lon']),
        image: _str(j['image']),
        imageCredit: _str(j['image_credit']),
        imageLicense: _str(j['image_license']),
        description: _str(j['description']),
        wikiUrl: _str(j['wiki_url']),
        mapUrl: _str(j['map_url']),
        osmUrl: _str(j['osm_url']),
        weatherNote: _str(j['weather_note']),
        open: _str(j['open']),
        close: _str(j['close']),
        leg: j['leg'] is Map ? Leg.fromJson((j['leg'] as Map).cast<String, dynamic>()) : null,
      );
}

class PlanDay {
  final int day;
  final String date;
  final String weekday;
  final Weather weather;
  final List<PlanItem> items;
  final String routeUrl;
  final double km;
  final int travelMinutes;
  final int cost;

  const PlanDay({
    required this.day,
    required this.date,
    required this.weekday,
    required this.weather,
    required this.items,
    required this.routeUrl,
    required this.km,
    required this.travelMinutes,
    required this.cost,
  });

  List<PlanItem> get stops => items.where((i) => i.isStop).toList();

  factory PlanDay.fromJson(Map<String, dynamic> j) => PlanDay(
        day: _int(j['day']),
        date: _str(j['date']),
        weekday: _str(j['weekday']),
        weather: Weather.fromJson((j['weather'] as Map? ?? {}).cast<String, dynamic>()),
        items: (j['items'] as List? ?? []).map((e) => PlanItem.fromJson((e as Map).cast<String, dynamic>())).toList(),
        routeUrl: _str(j['route_url']),
        km: _double(j['km']),
        travelMinutes: _int(j['travel_minutes']),
        cost: _int(j['cost']),
      );
}

class Totals {
  final int entries;
  final int transport;
  final int meals;
  final int stay;
  final String hotel;
  final int total;
  final int budget;
  final int left;
  final int perPerson;
  final int jeep;
  final int jeepDays;
  final int travelToCity;
  final String homeCity;
  final String travelMode;
  final String travellerType;

  const Totals({
    required this.entries,
    required this.transport,
    required this.meals,
    required this.stay,
    required this.hotel,
    required this.total,
    required this.budget,
    required this.left,
    required this.perPerson,
    this.jeep = 0,
    this.jeepDays = 0,
    this.travelToCity = 0,
    this.homeCity = '',
    this.travelMode = 'bus',
    this.travellerType = 'local',
  });

  factory Totals.fromJson(Map<String, dynamic> j) => Totals(
        entries: _int(j['entries']),
        transport: _int(j['transport']),
        meals: _int(j['meals']),
        stay: _int(j['stay']),
        hotel: _str(j['hotel']),
        total: _int(j['total']),
        budget: _int(j['budget']),
        left: _int(j['left']),
        perPerson: _int(j['per_person']),
        jeep: _int(j['jeep']),
        jeepDays: _int(j['jeep_days']),
        travelToCity: _int(j['travel_to_city']),
        homeCity: _str(j['home_city']),
        travelMode: j['travel_mode'] == 'car' ? 'car' : 'bus',
        travellerType: j['traveller_type'] == 'foreign' ? 'foreign' : 'local',
      );
}

class Itinerary {
  final String id;
  final String batchId;
  final String cityId;
  final String cityName;
  final String variant;
  final String title;
  final String label;
  final int matchScore;
  final int totalCost;
  final DateTime startDate;
  final int days;
  bool saved;
  final String image;
  final Map<String, dynamic> preferences;
  final Map<String, dynamic> plan;

  Itinerary({
    required this.id,
    required this.batchId,
    required this.cityId,
    required this.cityName,
    required this.variant,
    required this.title,
    required this.label,
    required this.matchScore,
    required this.totalCost,
    required this.startDate,
    required this.days,
    required this.saved,
    required this.image,
    required this.preferences,
    required this.plan,
  });

  factory Itinerary.fromJson(Map<String, dynamic> j) => Itinerary(
        id: _str(j['id']),
        batchId: _str(j['batch_id']),
        cityId: _str(j['city_id']),
        cityName: _str(j['city_name']),
        variant: _str(j['variant']),
        title: _str(j['title']),
        label: _str(j['label']),
        matchScore: _int(j['match_score']),
        totalCost: _int(j['total_cost']),
        startDate: DateTime.tryParse(_str(j['start_date'])) ?? DateTime.now(),
        days: _int(j['days']),
        saved: j['saved'] == true,
        image: _str(j['image']),
        preferences: (j['preferences'] as Map?)?.cast<String, dynamic>() ?? {},
        plan: (j['plan'] as Map?)?.cast<String, dynamic>() ?? {},
      );

  bool get hasPlan => plan.isNotEmpty;

  List<PlanDay> get dayPlans =>
      (plan['days'] as List? ?? []).map((e) => PlanDay.fromJson((e as Map).cast<String, dynamic>())).toList();

  Totals get totals => Totals.fromJson((plan['totals'] as Map? ?? {}).cast<String, dynamic>());

  int get stopCount => _int((plan['stats'] as Map? ?? {})['stops']);

  double get km => _double((plan['stats'] as Map? ?? {})['km']);

  int get people {
    final n = _int(preferences['group_size']);
    if (n > 0) return n;
    const defaults = {'solo': 1, 'couple': 2};
    return defaults[_str(preferences['group_type'])] ?? 4;
  }

  String get weatherSource => _str(plan['weather_source']);
}
