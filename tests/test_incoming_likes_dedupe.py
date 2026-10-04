from state.session_store import SessionStore
from utils.incoming_likes import (
    compact_incoming_likes_queue,
    dedupe_profiles_by_login,
    remap_index_after_dedupe,
)


def test_dedupe_profiles_by_login():
    profiles = [
        {'login': 'skyline'},
        {'login': 'skyline'},
        {'login': 'anna'},
    ]
    assert dedupe_profiles_by_login(profiles) == [
        {'login': 'skyline'},
        {'login': 'anna'},
    ]


def test_remap_index_skips_duplicate_rows():
    queue = [
        {'login': 'skyline'},
        {'login': 'skyline'},
        {'login': 'anna'},
    ]
    deduped = dedupe_profiles_by_login(queue)
    assert remap_index_after_dedupe(queue, 0, deduped) == 0
    assert remap_index_after_dedupe(queue, 1, deduped) == 1
    assert remap_index_after_dedupe(queue, 2, deduped) == 1


def test_session_store_compacts_legacy_queue():
    store = SessionStore()
    store.get(7)['incoming_likes_queue'] = [
        {'login': 'a'},
        {'login': 'a'},
        {'login': 'b'},
    ]
    store.get(7)['incoming_likes_index'] = 1
    store.get(7)['incoming_likes_total'] = 3

    queue, index, total = store.get_incoming_likes_state(7)
    assert [p['login'] for p in queue] == ['a', 'b']
    assert index == 1
    assert total == 2


if __name__ == '__main__':
    test_dedupe_profiles_by_login()
    test_remap_index_skips_duplicate_rows()
    test_session_store_compacts_legacy_queue()
    compact_incoming_likes_queue(
        [{'login': 'x'}, {'login': 'x'}],
        1,
    )
    print('incoming_likes_dedupe: ok')
