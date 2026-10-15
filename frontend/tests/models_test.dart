import 'package:flutter_test/flutter_test.dart';
import 'package:qissago/core/format.dart';
import 'package:qissago/core/models.dart';

Map<String, dynamic> samplePlan() => {
      'id': 'abc',
      'batch_id': 'b1',
      'city_id': 'lahore',
      'city_name': 'Lahore',
      'variant': 'balanced',
      'title': 'Balanced Explorer',
      'label': 'Best match',
      'match_score': 92,
      'total_cost': 74100,
      'start_date': '2026-10-16',
      'days': 1,
      'saved': false,
      'image': '/static/images/pois/lhr_fort.jpg',
      'preferences': {'group_type': 'family', 'group_size': null},
      'plan': {
        'stats': {'stops': 1, 'km': 2.5},
        'totals': {'total': 74100, 'budget': 80000, 'left': 5900, 'meals': 22500, 'stay': 36000, 'hotel': 'budget'},
        'days': [
          {
            'day': 1,
            'date': '2026-10-16',
            'weekday': 'Fri',
            'weather': {'tmax': 33, 'tmin': 18, 'rain_pct': 5, 'icon': 'sunny', 'text': 'Clear', 'source': 'seasonal'},
            'route_url': 'https://www.google.com/maps/dir/?api=1',
            'km': 2.5,
            'cost': 1500,
            'items': [
              {
                'kind': 'stop',
                'id': 'lhr_fort',
                'name': 'Lahore Fort',
                'category': 'landmark',
                'tags': ['history', 'art'],
                'start': '09:00',
                'end': '11:00',
                'minutes': 120,
                'cost_group': 1500,
                'outdoor': true,
                'lat': 31.588,
                'lon': 74.315,
                'leg': null,
              },
              {'kind': 'break', 'type': 'lunch', 'title': 'Lunch', 'start': '12:30', 'end': '13:15'},
            ],
          },
        ],
      },
    };

void main() {
  test('itinerary JSON is read correctly', () {
    final it = Itinerary.fromJson(samplePlan());
    expect(it.title, 'Balanced Explorer');
    expect(it.people, 4); // family without a size -> default 4
    expect(it.totals.left, 5900);
    final day = it.dayPlans.single;
    expect(day.weather.tmax, 33);
    expect(day.items.length, 2);
    expect(day.stops.single.name, 'Lahore Fort');
    expect(day.items.last.isStop, false);
    expect(day.items.last.name, 'Lunch');
  });

  test('chat turn JSON is read correctly', () {
    final t = ChatTurn.fromJson({
      'session_id': 's1',
      'reply': 'Which city?',
      'suggestions': ['Lahore', 'Karachi'],
      'awaiting': 'city',
      'missing': ['city'],
      'ready': false,
      'action': '',
      'preferences': {'city': null},
    });
    expect(t.suggestions, ['Lahore', 'Karachi']);
    expect(t.ready, false);
  });

  test('formatting helpers', () {
    expect(rupees(150000), 'Rs 150,000');
    expect(duration(45), '45 min');
    expect(duration(90), '1 h 30 min');
    expect(duration(120), '2 h');
    expect(isoDate(DateTime(2026, 1, 5)), '2026-01-05');
    expect(titleCase('food street'), 'Food street');
  });
}
