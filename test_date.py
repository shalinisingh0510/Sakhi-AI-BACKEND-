import datetime
try:
    d = datetime.date(2023, 1, 1)
    td = datetime.timedelta(days=28.5)
    result = d + td
    with open("test_date.txt", "w") as f:
        f.write(str(type(result)))
except Exception as e:
    with open("test_date.txt", "w") as f:
        f.write(str(e))
