from app import app, db, Settings

with app.app_context():
    s = {s.key: s.value for s in Settings.query.all()}
    print(s)
