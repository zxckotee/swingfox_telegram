"""Helpers for incoming-likes swipe queue."""

from typing import List, Optional, Tuple


def dedupe_profiles_by_login(profiles: List[dict]) -> List[dict]:
    seen: set = set()
    unique: List[dict] = []
    for profile in profiles:
        login = profile.get('login')
        if not login or login in seen:
            continue
        seen.add(login)
        unique.append(profile)
    return unique


def remap_index_after_dedupe(queue: List[dict], index: int, deduped: List[dict]) -> int:
    """Map a queue index (possibly on duplicate rows) to a deduped-queue index."""
    if not queue or index >= len(queue):
        return len(deduped)
    if not deduped:
        return 0

    prev_login = queue[index - 1].get('login') if index > 0 else None
    current_login = queue[index].get('login')
    if not current_login:
        return min(index, len(deduped))

    if index > 0 and current_login == prev_login:
        for i in range(index, len(queue)):
            login = queue[i].get('login')
            if login and login != current_login:
                for j, profile in enumerate(deduped):
                    if profile.get('login') == login:
                        return j
                break
        return len(deduped)

    for j, profile in enumerate(deduped):
        if profile.get('login') == current_login:
            return j
    return len(deduped)


def compact_incoming_likes_queue(
    queue: List[dict], index: int
) -> Tuple[List[dict], int, int]:
    deduped = dedupe_profiles_by_login(queue)
    new_index = remap_index_after_dedupe(queue, index, deduped)
    return deduped, new_index, len(deduped)
