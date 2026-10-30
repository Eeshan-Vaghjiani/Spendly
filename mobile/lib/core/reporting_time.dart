// Kenya uses UTC+03:00 throughout the year. Calendar-only values are never shifted.
DateTime nairobiWallTime(DateTime instant) {
  final value = instant.toUtc().add(const Duration(hours: 3));
  return DateTime.utc(
    value.year,
    value.month,
    value.day,
    value.hour,
    value.minute,
    value.second,
    value.millisecond,
    value.microsecond,
  );
}

DateTime nairobiInstant(DateTime wallTime) => DateTime.utc(
  wallTime.year,
  wallTime.month,
  wallTime.day,
  wallTime.hour,
  wallTime.minute,
  wallTime.second,
  wallTime.millisecond,
  wallTime.microsecond,
).subtract(const Duration(hours: 3));

DateTime calendarDate(DateTime value) =>
    DateTime.utc(value.year, value.month, value.day);
DateTime nairobiDate(DateTime instant) =>
    calendarDate(nairobiWallTime(instant));
