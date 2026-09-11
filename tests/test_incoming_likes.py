from state.session_store import SessionStore


def test_incoming_likes_queue():
    store = SessionStore()
    profiles = [{'login': 'u1'}, {'login': 'u2'}, {'login': 'u3'}]
    store.set_incoming_likes(42, profiles)

    queue, index, total = store.get_incoming_likes_state(42)
    assert queue == profiles
    assert index == 0
    assert total == 3

    store.advance_incoming_like(42)
    queue, index, total = store.get_incoming_likes_state(42)
    assert index == 1
    assert total == 3

    store.clear_incoming_likes(42)
    queue, index, total = store.get_incoming_likes_state(42)
    assert queue == []
    assert index == 0
    assert total == 0


if __name__ == '__main__':
    test_incoming_likes_queue()
    print('incoming_likes: all assertions passed')
