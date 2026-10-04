from handlers.bot_handlers import _dedupe_profiles_by_login


def test_dedupe_profiles_by_login():
    profiles = [
        {'login': 'skyline'},
        {'login': 'skyline'},
        {'login': 'anna'},
    ]
    assert _dedupe_profiles_by_login(profiles) == [
        {'login': 'skyline'},
        {'login': 'anna'},
    ]


if __name__ == '__main__':
    test_dedupe_profiles_by_login()
    print('incoming_likes_dedupe: ok')
