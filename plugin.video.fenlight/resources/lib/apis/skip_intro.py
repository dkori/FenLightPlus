# -*- coding: utf-8 -*-
from apis import introdb_api
from caches.main_cache import main_cache
# from modules.kodi_utils import logger

cache_key = 'skip_intro.introdb.%s.%s.%s'
HIT_HOURS, EMPTY_HOURS = 720, 168  # 30 days for real data, 7 days for blank data
KINDS = ('recap', 'intro', 'outro')  # ordered by where they sit in an episode

def valid_segment(kind, seg, total_time=None):
	try:
		start, end = float(seg['start_sec']), float(seg['end_sec'])
	except (KeyError, TypeError, ValueError): return False
	if start < 0 or end <= start: return False
	duration = end - start
	if kind == 'recap':
		if not 5 <= duration <= 120: return False
		if total_time and start > total_time * 0.5: return False  # recaps sit at the start
		return True
	if kind == 'outro':
		if not 5 <= duration <= 300: return False
		if total_time and start < total_time * 0.5: return False  # outros sit in the latter half
		return True
	if not 5 <= duration <= 300: return False
	if total_time:
		if start > total_time * 0.5: return False  # not past the midpoint
	return True

def get_segments(imdb_id, season, episode, cache_only=False):
	if not imdb_id: return None
	try: season, episode = int(season), int(episode)
	except (TypeError, ValueError): return None
	key = cache_key % (imdb_id, season, episode)
	cached = main_cache.get(key)
	if cached is not None: return cached
	if cache_only: return None
	data = introdb_api.get_segments(imdb_id, season, episode)
	if data is None: return None  # error — do not cache
	segments = {'intro': data.get('intro'), 'recap': data.get('recap'), 'outro': data.get('outro')}
	main_cache.set(key, segments, expiration=HIT_HOURS if any(segments.values()) else EMPTY_HOURS)
	return segments

def prefetch(imdb_id, season, episode):
	# Warm the cache at source-search time
	try: get_segments(imdb_id, season, episode)
	except: pass

def get_skip_windows(imdb_id, season, episode, total_time, enabled_kinds, cache_only=True):
	segments = get_segments(imdb_id, season, episode, cache_only=cache_only)
	if not segments: return []
	windows = []
	for kind in KINDS:
		if kind not in enabled_kinds: continue
		seg = segments.get(kind)
		if seg and valid_segment(kind, seg, total_time):
			windows.append({'kind': kind, 'start': float(seg['start_sec']), 'end': float(seg['end_sec'])})
	return windows
