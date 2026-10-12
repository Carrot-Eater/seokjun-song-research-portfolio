#!/usr/bin/env python3
"""Go2 임무 원장(mission ledger) — 순찰 에이전트 events.jsonl 에서 세션·임무 지표를 계산한다.

입력  : 소스별 루트(기본 jetson=~/go2_runs_mirror/jetson, pc=~/go2_runs_mirror/pc)의 agent_*/events.jsonl (+ tick_profile_*.txt)
출력  : <out>/missions.csv     세션 1행(요청 열 전부)
        <out>/mission_list.csv 임무 1행(자동 재개로 이어 붙인 구간 묶음)
        <out>/missions.json    세션 + 임무 + 구간 상세
        <out>/summary.json, summary.md  누적 요약 + 일별 표
정의  : 같은 폴더 DEFINITIONS.md. 기록에 없는 값은 null(JSON) / 'unknown'(CSV) — 대치·추정하지 않는다.
실행  : python3 -I mission_ledger.py [--source NAME=DIR ...] [--out DIR] [--now EPOCH]
표준 라이브러리만 쓴다(사용자 site 의 numpy 2.4 가 깨져 있어 python3 -I 로 실행).
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import json
import math
import os
import re
import sys
import tempfile

SCHEMA = 'go2.mission_ledger.v1'
KST = dt.timezone(dt.timedelta(hours=9), 'KST')

IDLE, HOLD = 'IDLE', 'SAFE_HOLD'
ACTIVE_STATES = frozenset({'MAP', 'PATROL', 'ANOMALY', 'LOCALIZE', 'CONFIRM', 'RECHECK', 'RETURN'})   # 로봇이 스스로 판단·이동하는 상태
HUMAN_WAIT_STATES = frozenset({'REPORT', 'VERIFY'})                                                 # 임무 중이지만 사람 응답 대기(정지)
MISSION_STATES = ACTIVE_STATES | HUMAN_WAIT_STATES
IMPLICIT_IDLE_KINDS = ('reset', 'forget', 'coordinate_epoch_changed')   # 에이전트가 FSM 을 새로 만들며 전이 기록 없이 IDLE 이 되는 사건

# 상수(정의서와 같아야 한다)
GAP_CAP_S = 180.0              # 이동 상태에서 사건 사이 간격은 최대 이만큼만 자율 시간으로 인정(목표 제한 120 s·탈출 제한 120 s + 여유)
LAUNCH_WINDOW_S = 4.0          # IDLE→임무 전이 직전 이 안의 operator start / start_mode / 힌트를 그 임무의 시작 근거로 본다
END_EVIDENCE_WINDOW_S = 5.0    # 임무 종료 전이 직전 이 안의 정지·권한 회수 기록을 종료 원인으로 본다(틱 2 s + 느린 틱)
HINT_DONE_WINDOW_S = 1.5       # '이동 후 정지' 힌트 도착(operator_hint_done) 직후의 정지만 힌트 완료로 본다
AUTO_RESUME_MAX_GAP_S = 30.0   # 자동 종료 뒤 이 안의 같은 모드 재시작 = 콘솔 자동 재개(사람 개입 아님)
MERGE_MAX_GAP_S = 120.0        # 자동 종료 뒤 이 안의 같은 모드 재시작은 같은 임무로 이어 붙인다(30 s 초과분은 사람 재시작 = 개입)
DEBOUNCE_S = 10.0              # 같은 종류 개입이 이 안에 연달아 기록되면 1회(Space 연타·정지 버튼의 권한 회수 메아리)
LIVE_WINDOW_S = 600.0          # 소스의 가장 최근 세션이 이 안에 기록됐으면 '진행 중'으로 본다
CLOCK_BACKSTEP_FLAG_S = 1.0    # 이보다 큰 시각 역행만 데이터 품질 문제로 표시(수 ms 역행은 스레드 간 기록 순서 차이)


def _epoch(iso):
    return dt.datetime.fromisoformat(iso).timestamp()


# 지표별 '기록이 존재한 시점' — 그 사건 종류가 처음 나타난 세션의 시작 시각(보수적). 이전 세션의 값은 0 이 아니라 '알 수 없음'.
AVAILABLE_SINCE = {
    'escape': ('2026-09-19T11:57:20+09:00', 'pc/agent_20260919_115718', 'escape_start/escape_result'),
    'manual_takeover_flag': ('2026-09-29T14:37:03+09:00', 'pc/agent_20260929_143703', 'stop.manual_takeover_only'),
    'start_mode': ('2026-09-29T18:37:13+09:00', 'jetson/agent_20260929_093713', 'start_mode'),
    'verified_arrival': ('2026-09-30T11:19:57+09:00', 'jetson/agent_20260930_021957', 'movement_result'),
    'permit_failed': ('2026-09-30T14:33:46+09:00', 'jetson/agent_20260930_053346', 'permit_failed'),
    'operator_hint': ('2026-09-30T14:50:02+09:00', 'jetson/agent_20260930_055002', 'operator_hint'),
    'slow_tick': ('2026-09-30T17:28:31+09:00', 'jetson/agent_20260930_082831', 'slow_tick'),
    'authority_lost': ('2026-10-02T19:17:45+09:00', 'jetson/agent_20261002_101745', 'authority_lost'),
}
# 콘솔 자동 재개(web_console.auto_resume_loop, 코드 주석 2026-09-30). 그 전의 재시작은 전부 사람으로 센다.
AUTO_RESUME_SINCE = ('2026-09-30T00:00:00+09:00', 'web_console.auto_resume_loop 주석 날짜')
# 개입 기록이 모두 갖춰진 시점(정지·재개·힌트·수동 인계 귀속) = 위 항목 중 가장 늦은 것
COMPLETE_INSTRUMENTATION_KEYS = ('operator_hint', 'manual_takeover_flag', 'authority_lost')

END_REASON_PREFIXES = (
    ('task complete', 'task_complete'), ('explore done', 'explore_done'), ('returned home', 'returned_home'),
    ('patrol failure budget', 'patrol_failed'), ('patrol round incomplete', 'patrol_incomplete'),
    ('patrol unavailable', 'patrol_unavailable'), ('battery', 'battery_end'),
    ('navigation_only rejects', 'rejected'), ('coordinate epoch changed', 'coordinate_reset'),
    ('operator resume', 'resume_to_idle'), ('auto resume', 'hold_cleared_to_idle'),
)
OUTCOME_OF = {
    'task_complete': 'completed', 'explore_done': 'completed', 'returned_home': 'completed', 'hint_goto_done': 'completed',
    'operator_stop': 'operator_stopped', 'manual_takeover': 'manual_takeover',
    'authority_lost': 'fault', 'patrol_failed': 'fault', 'patrol_incomplete': 'fault', 'patrol_unavailable': 'fault',
    'rejected': 'fault', 'stop_unattributed': 'unattributed_stop', 'battery_end': 'battery_end',
    'coordinate_reset': 'reset', 'agent_reset': 'reset', 'truncated': 'truncated', 'in_progress': 'in_progress',
}
UNDECIDED_OUTCOMES = ('truncated', 'in_progress')
TERMINAL_GOAL_MODES = ('explore', 'task')            # 스스로 끝나는 임무(완료율 분모)
AUTO_END_CLASSES = ('authority_lost', 'stop_unattributed')
INTERVENTION_TYPES = ('stop', 'manual_takeover', 'hint', 'resume')


# ── 기본 도구 ────────────────────────────────────────────────────────────────
def kst(t):
    return None if t is None else dt.datetime.fromtimestamp(t, KST).isoformat(timespec='seconds')


def kst_date(t):
    return dt.datetime.fromtimestamp(t, KST).date().isoformat()


def split_by_day(t0, seconds):
    """[t0, t0+seconds) 를 KST 자정에서 잘라 (날짜, 초) 목록으로."""
    out = []
    while seconds > 1e-9:
        d = dt.datetime.fromtimestamp(t0, KST)
        nxt = (d.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)).timestamp()
        chunk = min(seconds, nxt - t0)
        out.append((d.date().isoformat(), chunk))
        t0 += chunk
        seconds -= chunk
    return out


def finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def load_events(path):
    """events.jsonl → (사건 목록, 깨진 줄 수, 전체 줄 수). 쓰는 중 잘린 마지막 줄도 깨진 줄로 센다."""
    events, bad, lines = [], 0, 0
    with open(path, 'rb') as f:
        for raw in f:
            lines += 1
            s = raw.decode('utf-8', 'replace').strip()
            if not s:
                continue
            try:
                r = json.loads(s)
            except ValueError:
                bad += 1
                continue
            if not isinstance(r, dict) or not finite(r.get('t')) or not isinstance(r.get('kind'), str):
                bad += 1
                continue
            events.append(r)
    return events, bad, lines


_TICK_RE = re.compile(r'^tick\s+([0-9]+(?:\.[0-9]+)?)\s*s')


def profile_max_tick(session_dir):
    """tick_profile_*.txt 첫 줄 'tick 2.271 s state MAP' 의 최댓값(파일이 없으면 None)."""
    best = None
    for p in sorted(glob.glob(os.path.join(session_dir, 'tick_profile_*.txt'))):
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                m = _TICK_RE.match(f.readline().strip())
        except OSError:
            continue
        if m:
            v = float(m.group(1))
            best = v if best is None else max(best, v)
    return best


def authority_cause(why):
    """authority_lost.why → ('human'|'auto', 원인). 'automatic authority lost: ' 겹 접두는 벗겨 가장 안쪽 이유로 판정."""
    s = str(why or '').strip()
    while s.startswith('automatic authority lost:'):
        s = s[len('automatic authority lost:'):].strip()
    for prefix, cause in (('operator stop', 'operator_stop'), ('manual takeover', 'manual_takeover'),
                          ('manual posture', 'manual_posture'), ('damping', 'damping')):
        if s.startswith(prefix):
            return 'human', cause
    if 'permit_expired' in s:
        return 'auto', 'permit_expired'
    for prefix, cause in (('connection lost', 'connection_lost'), ('driver reconnected', 'driver_reconnected'),
                          ('stop_move', 'stop_move'), ('automatic permit lost', 'permit_lost'),
                          ('explicit mission start canceled', 'start_canceled'), ('stack startup', 'stack_startup')):
        if s.startswith(prefix):
            return 'auto', cause
    if s.startswith('automatic mission stopped:'):
        return 'auto', 'auto_stopped:' + s.split(':', 1)[1].strip()[:40]
    return 'auto', 'other:' + s[:40]


def hold_flags(reason):
    """'safety: loc_lost,scan_lost' → ['loc_lost', 'scan_lost']."""
    r = str(reason or '')
    if ':' in r:
        r = r.split(':', 1)[1]
    return [f.strip() for f in r.split(',') if f.strip()] or ['unknown']


def goal_key(g):
    if isinstance(g, dict) and finite(g.get('x')) and finite(g.get('y')):
        return (round(g['x'], 4), round(g['y'], 4))
    return None


def travel_sum(travel):
    if not isinstance(travel, dict):
        return None
    vals = [v for v in travel.values() if finite(v) and v >= 0]
    return round(sum(vals), 3) if vals else None


def _human_stop_signal(e):
    """정지 계열 사람 신호면 ('stop'|'manual_takeover'), 아니면 None."""
    k = e['kind']
    if k == 'operator' and e.get('cmd') == 'stop':
        return 'stop'
    if k == 'authority_lost':
        klass, cause = authority_cause(e.get('why'))
        if klass == 'human':
            return 'manual_takeover' if cause in ('manual_takeover', 'manual_posture') else 'stop'
    if k == 'stop' and e.get('manual_takeover_only') is True:
        return 'manual_takeover'
    return None


# ── 세션 분석 ────────────────────────────────────────────────────────────────
def _launch(events, seg, avail):
    """임무 구간 시작 근거: start_mode·operator start·힌트(직전 LAUNCH_WINDOW_S, 직전 전이에서 멈춤)."""
    i0, t_s = seg['start_i'], seg['start_t']
    mode = hint = None
    op_start = False
    j = i0 - 1
    while j >= 0 and t_s - events[j]['t'] <= LAUNCH_WINDOW_S:
        e = events[j]
        k = e['kind']
        if k == 'transition':
            break
        if k == 'start_mode' and mode is None:
            mode = e.get('mode')
        elif k == 'operator' and e.get('cmd') == 'start':
            op_start = True
        elif k in ('operator_hint', 'operator_hint_area', 'skill_poses') and hint is None:
            hint = k
        j -= 1
    if mode in ('explore', 'patrol', 'full', 'task'):
        label = 'hint' if (mode == 'full' and hint in ('operator_hint', 'operator_hint_area')) else mode
    else:
        label = 'unspecified' if avail['start_mode'] else 'legacy'
    launch = 'skill' if mode == 'task' else ('hint' if label == 'hint' else ('start' if op_start else 'unlogged'))
    return dict(mode=label, start_mode=mode, launch=launch, launch_hint=hint if label == 'hint' else None)


def _end_trigger(events, seg, t_ref, hint_ok):
    """종료 직전 창의 가장 이른 원인: 사람 정지/수동 인계 > 자동 권한 회수(같은 창이면 이른 것) > 권한 증거 > 힌트 도착."""
    best = None
    permit_auto = False
    hint_done = False
    j = seg['end_i']
    while j >= seg['start_i'] and t_ref - events[j]['t'] <= END_EVIDENCE_WINDOW_S:
        e = events[j]
        k = e['kind']
        human = _human_stop_signal(e)
        cand = None
        if human == 'stop':
            cand = ('operator_stop', None)
        elif human == 'manual_takeover':
            cand = ('manual_takeover', None)
        elif k == 'authority_lost':
            cand = ('authority_lost', authority_cause(e.get('why'))[1])
        elif k == 'permit_failed' and 'automatic_stopped' in (e.get('failed') or ()):
            permit_auto = True
        elif k == 'operator_hint_done' and t_ref - e['t'] <= HINT_DONE_WINDOW_S:
            hint_done = True
        if cand is not None:
            best = cand            # 뒤에서 앞으로 훑으므로 마지막에 남는 것이 가장 이른 원인
        j -= 1
    if best is not None:
        return best
    if permit_auto:
        return ('authority_lost', 'unattributed')
    if hint_ok and hint_done:
        return ('hint_goto_done', None)
    return None


def _end_class(events, seg, live, t_last):
    if seg['open']:
        if live:
            return 'in_progress', None
        trig = _end_trigger(events, seg, t_last, hint_ok=False)
        if trig is not None and trig[0] in ('operator_stop', 'manual_takeover', 'authority_lost'):
            return trig
        return 'truncated', None
    r = seg['end_reason'] or ''
    if seg['end_implicit']:
        if r == 'coordinate_epoch_changed':
            return 'coordinate_reset', None
        trig = _end_trigger(events, seg, seg['end_t'], hint_ok=False)
        if trig is not None and trig[0] in ('operator_stop', 'manual_takeover'):
            return trig
        return 'agent_reset', None
    for prefix, cls in END_REASON_PREFIXES:
        if r.startswith(prefix):
            detail = r[r.find('(') + 1:r.rfind(')')] if cls == 'explore_done' and '(' in r else None
            if cls == 'battery_end':
                m = re.match(r'battery\s+([0-9.]+)', r)
                detail = m.group(1) if m else None
            return cls, detail
    if r.startswith('operator stop'):
        trig = _end_trigger(events, seg, seg['end_t'], hint_ok=not r.startswith('operator stop (hold)'))
        if trig is not None:
            return trig
        return 'stop_unattributed', None
    return 'other', r[:60]


def analyze_session(source, name, events, *, now=None, newest=False, bad_lines=0, n_lines=0, max_profile_tick=None):
    sid = '%s/%s' % (source, name)
    base = dict(session_id=sid, source=source, dir=name, n_events=len(events), n_lines=n_lines, bad_lines=bad_lines)
    if not events:
        base.update(empty=True, dry_run=None, live=False, missions=[], notes=['no_valid_events'])
        return base
    t0, t1 = events[0]['t'], events[-1]['t']
    start_ev = next((e for e in events if e['kind'] == 'start' and isinstance(e.get('params'), dict)), None)
    params = start_ev['params'] if start_ev else {}
    dry = params.get('dry_run') is True
    live = bool(newest and now is not None and 0 <= now - t1 <= LIVE_WINDOW_S)
    avail = {k: t0 >= _epoch(v[0]) for k, v in AVAILABLE_SINCE.items()}
    complete = all(avail[k] for k in COMPLETE_INSTRUMENTATION_KEYS)
    notes = []
    if start_ev is None:
        notes.append('no_start_event')
    if dry:
        notes.append('dry_run')
    daily = collections.defaultdict(collections.Counter)

    # ① 상태 흐름·임무 구간
    state, prev_t = IDLE, t0
    time_in = collections.Counter()
    trans = collections.Counter()
    autonomous = 0.0
    mismatches = backsteps = 0
    segs, seg = [], None
    holds = []
    seg_of = [None] * len(events)
    state_before = [None] * len(events)
    for i, e in enumerate(events):
        t = e['t']
        d = t - prev_t
        if d < 0:
            if d < -CLOCK_BACKSTEP_FLAG_S:
                backsteps += 1
            d = 0.0
        if d > 0:
            time_in[state] += d
            if seg is not None:
                seg['time_in'][state] += d
            if state in ACTIVE_STATES:
                credit = min(d, GAP_CAP_S)
                if seg is not None:
                    seg['autonomous_s'] += credit
                if not dry:
                    autonomous += credit
                    for day, sec in split_by_day(prev_t, credit):
                        daily[day]['autonomous_s'] += sec
        prev_t = max(prev_t, t)
        state_before[i] = state
        seg_of[i] = len(segs) if seg is not None else None
        k = e['kind']
        new = why = None
        implicit = False
        if k == 'transition':
            src, dst = e.get('src'), e.get('dst')
            trans['%s->%s' % (src, dst)] += 1
            if src != state:
                mismatches += 1
            if isinstance(dst, str):
                new, why = dst, str(e.get('reason') or '')
        elif k in IMPLICIT_IDLE_KINDS and state != IDLE:
            new, why, implicit = IDLE, k, True
        if new is None or new == state:
            continue
        if new == HOLD:
            holds.append(dict(t=t, flags=hold_flags(why), src=state, in_mission=seg is not None, seg=len(segs) if seg is not None else None))
        if seg is None and new in MISSION_STATES:
            seg = dict(start_i=i, start_t=t, start_state=new, start_reason=why, time_in=collections.Counter(), autonomous_s=0.0)
            seg_of[i] = len(segs)
        elif seg is not None and new == IDLE:
            seg.update(end_i=i, end_t=t, end_reason=why, end_implicit=implicit, open=False)
            segs.append(seg)
            seg = None
        state = new
    if seg is not None:
        seg.update(end_i=len(events) - 1, end_t=t1, end_reason=None, end_implicit=False, open=True)
        segs.append(seg)
    if mismatches:
        notes.append('transition_src_mismatch:%d' % mismatches)
    if backsteps:
        notes.append('clock_backsteps:%d' % backsteps)

    # ② 목표(전송·결과 짝짓기)
    goals, unmatched_results = [], 0
    for i, e in enumerate(events):
        k = e['kind']
        if k == 'goal' and isinstance(e.get('goal'), dict):
            goals.append(dict(i=i, t=e['t'], key=goal_key(e['goal']), dry=e.get('dry_run') is True, denied=False,
                              result=None, reason=None, verified=False, backend=None, displacement=None))
        elif k == 'goal_denied' and e.get('reason') == 'unattested_coordinate_context':
            for g in reversed(goals):                      # 'goal' 기록 뒤 같은 틱에 전송 거부 → 실제로 보내지 않음
                if g['result'] is None and not g['denied']:
                    g['denied'] = True
                    break
        elif k in ('movement_result', 'nav_backend_result', 'nav_result'):
            key = goal_key(e.get('goal'))
            field = 'backend' if k == 'nav_backend_result' else 'result'
            target = None
            for g in reversed(goals):
                if g['denied'] or g[field] is not None:
                    continue
                if key is None or g['key'] == key:
                    target = g
                    break
            if target is None:
                unmatched_results += 1
                continue
            res = e.get('result')
            if k == 'movement_result':
                target.update(result=res, reason=e.get('reason'), verified=(res == 'succeeded' and e.get('verified') is True))
                if target['verified'] and finite(e.get('displacement_m')) and e['displacement_m'] >= 0:
                    target['displacement'] = float(e['displacement_m'])
            elif k == 'nav_backend_result':
                target['backend'] = res
            else:                                          # 옛 기록(2026-09-30 이전): Nav2 결과뿐(도착 검증 없음)
                target.update(result=res, backend=res)

    # ③ 탈출(시도·결과 짝짓기)
    escapes, escape_unmatched = [], 0
    for i, e in enumerate(events):
        k = e['kind']
        if k in ('escape_start', 'unstick_start', 'reposition_start'):
            escapes.append(dict(i=i, t=e['t'], kind=k, state=None, travel=None, result=None))
        elif k == 'escape_result':
            for x in reversed(escapes):
                if x['state'] is None:
                    x.update(state=e.get('state'), travel=travel_sum(e.get('travel')), result=str(e.get('result') or '')[:80])
                    break
            else:
                escape_unmatched += 1

    # ④ 구간 속성
    for n, s in enumerate(segs):
        s['n'] = n
        s.update(_launch(events, s, avail))
        s['end_class'], s['end_detail'] = _end_class(events, s, live, t1)
        s['loss'] = None
        for j in range(s['start_i'], s['end_i'] + 1):
            e = events[j]
            if e['kind'] == 'authority_lost':
                klass, cause = authority_cause(e.get('why'))
                if klass == 'auto':
                    s['loss'] = dict(t=e['t'], cause=cause)
                    break
        if s['loss'] is None and s['end_class'] == 'authority_lost':
            s['loss'] = dict(t=s['end_t'], cause=s['end_detail'] or 'unattributed')
        s['holds'] = [h for h in holds if h['seg'] == n]
        s['held_at_end'] = (not s['open'] and events[s['end_i']].get('src') == HOLD) if events[s['end_i']]['kind'] == 'transition' else False

    # ⑤ 임무 = 구간 + 자동 재개로 이어진 구간
    auto_resume_t = _epoch(AUTO_RESUME_SINCE[0])
    missions = []
    for s in segs:
        prev = missions[-1]['segments'][-1] if missions else None
        s['restart'] = None
        if prev is not None and prev['end_class'] in AUTO_END_CLASSES and not prev['open']:
            gap = s['start_t'] - prev['end_t']
            between = any(_human_stop_signal(events[j]) for j in range(prev['end_i'] + 1, s['start_i']))
            if (0 <= gap <= MERGE_MAX_GAP_S and s['start_mode'] == prev['start_mode'] and s['launch'] != 'hint' and not between):
                s['restart'] = 'auto_resume' if (gap <= AUTO_RESUME_MAX_GAP_S and s['start_t'] >= auto_resume_t) else 'operator_restart'
                missions[-1]['segments'].append(s)
                continue
        missions.append(dict(segments=[s]))

    out_missions = []
    for n, m in enumerate(missions):
        out_missions.append(_mission_record(sid, n, m['segments'], events, state_before, goals, escapes, avail, dry, daily))

    # ⑥ 세션 합계
    real_goals = [g for g in goals if not g['dry']]
    sent = [g for g in real_goals if not g['denied']]
    slow = [e for e in events if e['kind'] == 'slow_tick' and finite(e.get('seconds'))]
    idle_stops = sum(1 for i, e in enumerate(events)
                     if e['kind'] == 'operator' and e.get('cmd') == 'stop' and seg_of[i] is None)
    max_tick_vals = [e['seconds'] for e in slow] + ([max_profile_tick] if max_profile_tick is not None else [])
    battery_end = next((float(x['end_detail']) for x in reversed(segs) if x['end_class'] == 'battery_end' and x['end_detail']), None)
    if not dry:
        daily[kst_date(t0)]['sessions'] += 1
        for e in slow:
            daily[kst_date(e['t'])]['slow_ticks'] += 1
        for h in holds:
            if h['in_mission']:
                daily[kst_date(h['t'])]['safe_hold_entries'] += 1
        for g in sent:
            daily[kst_date(g['t'])]['goals_sent'] += 1
            if g['verified']:
                daily[kst_date(g['t'])]['goals_verified'] += 1
        for x in escapes:
            daily[kst_date(x['t'])]['escapes_attempted'] += 1
            if x['state'] == 'done':
                daily[kst_date(x['t'])]['escapes_done'] += 1

    last = out_missions[-1] if out_missions else None
    if last is None:
        end_reason = 'no_mission'
    elif last['end_class'] == 'truncated':
        end_reason = 'process_ended_while_active'
    else:
        end_reason = last['end_class'] + (':' + last['end_detail'] if last['end_detail'] else '')
    inter = collections.Counter()
    for m in out_missions:
        for k in INTERVENTION_TYPES:
            inter[k] += m['interventions'][k]
    losses = collections.Counter(m_loss for m in out_missions for m_loss in m['authority_loss_causes'])
    hold_counter = collections.Counter(f for h in holds if h['in_mission'] for f in h['flags'])
    verified_known = avail['verified_arrival']
    disp = round(sum(g['displacement'] or 0.0 for g in sent if g['verified']), 3) if verified_known else None
    esc_travel = round(sum(x['travel'] or 0.0 for x in escapes), 3) if avail['escape'] else None
    lb_parts = [v for v in (disp, esc_travel) if v is not None]

    base.update(
        empty=False, start_t=t0, end_t=t1, start_kst=kst(t0), end_kst=kst(t1), duration_s=round(t1 - t0, 1),
        dry_run=dry, live=live, params=params, instrumentation_complete=complete,
        available={k: v for k, v in avail.items()},
        modes=sorted({m['mode'] for m in out_missions}) or ['none'],
        missions_count=len(out_missions), segments_count=len(segs),
        auto_resumes=sum(m['auto_resumes'] for m in out_missions),
        operator_restarts=sum(m['operator_restarts'] for m in out_missions),
        autonomous_s=round(autonomous, 1),
        time_in_state={k: round(v, 1) for k, v in sorted(time_in.items())},
        transitions=sum(trans.values()), transition_counts=dict(sorted(trans.items())),
        safe_hold_entries=sum(1 for h in holds if h['in_mission']),
        safe_hold_entries_idle=sum(1 for h in holds if not h['in_mission']),
        safe_hold_flags=dict(sorted(hold_counter.items())),
        goals_sent=len(sent),
        goals_succeeded_verified=sum(1 for g in sent if g['verified']) if verified_known else None,
        goals_succeeded_backend=sum(1 for g in sent if g['backend'] == 'succeeded'),
        goals_aborted=sum(1 for g in sent if g['result'] == 'aborted'),
        goals_canceled=sum(1 for g in sent if g['result'] == 'canceled'),
        goals_no_result=sum(1 for g in sent if g['result'] is None),
        goals_denied_after_log=sum(1 for g in real_goals if g['denied']),
        goal_results_unmatched=unmatched_results,
        distance_m=None, verified_displacement_m=disp, escape_travel_m=esc_travel,
        distance_lower_bound_m=round(sum(lb_parts), 3) if lb_parts else None,
        interventions_total=sum(inter.values()), interventions=dict(inter),
        interventions_excl_end_stop=sum(m['interventions_excl_end_stop'] for m in out_missions),
        checkpoint_decisions=sum(m['checkpoint_decisions'] for m in out_missions),
        hints_in_task=sum(m['hints_in_task'] for m in out_missions),
        idle_operator_stops=idle_stops,
        authority_losses=(sum(losses.values()) if (avail['authority_lost'] or avail['permit_failed']) else None),
        authority_loss_causes=dict(sorted(losses.items())),
        authority_lost_events=sum(1 for e in events if e['kind'] == 'authority_lost'),
        slow_ticks=len(slow) if avail['slow_tick'] else None,
        max_tick_s=round(max(max_tick_vals), 3) if max_tick_vals else None,   # 기록된 틱(slow_tick·프로파일) 중 최댓값
        max_profile_tick_s=max_profile_tick,
        escapes_attempted=len(escapes) if avail['escape'] else None,
        escapes_done=sum(1 for x in escapes if x['state'] == 'done') if avail['escape'] else None,
        escapes_failed=sum(1 for x in escapes if x['state'] == 'failed') if avail['escape'] else None,
        escapes_stopped=sum(1 for x in escapes if x['state'] == 'stopped') if avail['escape'] else None,
        escapes_no_result=sum(1 for x in escapes if x['state'] is None) if avail['escape'] else None,
        escapes_denied=sum(1 for e in events if e['kind'] == 'escape_denied'),
        escape_results_unmatched=escape_unmatched,
        battery_start=None, battery_end=battery_end,
        end_reason=end_reason, missions=out_missions, notes=notes,
        daily={d: dict(c) for d, c in sorted(daily.items())},
    )
    return base


def _mission_record(sid, n, segs, events, state_before, goals, escapes, avail, dry, daily):
    first, last = segs[0], segs[-1]
    idx = [(s['start_i'], s['end_i']) for s in segs]

    def inside(i):
        return any(a <= i <= b for a, b in idx)

    inter = collections.Counter()
    inter_t = []
    last_counted = {}
    checkpoints = hints_task = 0

    def add(kind, t, group=None):
        g = group or kind
        if g in last_counted and t - last_counted[g] <= DEBOUNCE_S:
            last_counted[g] = t
            return
        last_counted[g] = t
        inter[kind] += 1
        inter_t.append((t, kind))

    for s in segs:
        if s['restart'] == 'operator_restart':
            add('resume', s['start_t'])
        for j in range(s['start_i'], s['end_i'] + 1):
            e = events[j]
            k = e['kind']
            human = _human_stop_signal(e)
            if human in ('stop', 'manual_takeover'):
                add(human, e['t'], group='takeover')   # 정지·수동 인계가 10 s 안에 이어지면 한 번(먼저 기록된 종류)
            elif k == 'operator':
                cmd = e.get('cmd')
                if cmd == 'resume' or (cmd == 'start' and state_before[j] == HOLD):
                    add('resume', e['t'])
                elif cmd in ('approve', 'deny'):
                    checkpoints += 1
            elif k == 'operator_hint_area':
                add('hint', e['t'], group='hint_%d' % j)
            elif k == 'operator_hint':
                if first['mode'] == 'task':
                    hints_task += 1
                else:
                    add('hint', e['t'], group='hint_%d' % j)

    end_stop = None
    if last['end_class'] in ('operator_stop', 'manual_takeover'):
        t_end = last['end_t']
        for t, kind in reversed(inter_t):
            if kind in ('stop', 'manual_takeover') and 0 <= t_end - t <= END_EVIDENCE_WINDOW_S + DEBOUNCE_S:
                end_stop = (t, kind)
                break
    m_goals = [g for g in goals if inside(g['i']) and not g['dry'] and not g['denied']]
    m_esc = [x for x in escapes if inside(x['i'])]
    slow = [events[j] for a, b in idx for j in range(a, b + 1) if events[j]['kind'] == 'slow_tick' and finite(events[j].get('seconds'))]
    losses = [s['loss'] for s in segs if s['loss'] is not None]
    holds = [h for s in segs for h in s['holds']]
    end_class, end_detail = last['end_class'], last['end_detail']
    hints_done = sum(1 for a, b in idx for j in range(a, b + 1) if events[j]['kind'] == 'operator_hint_done')
    hints_abandoned = sum(1 for a, b in idx for j in range(a, b + 1) if events[j]['kind'] == 'operator_hint_abandoned')
    outcome = OUTCOME_OF.get(end_class, 'other')
    if outcome == 'completed' and (hints_abandoned or (end_class == 'explore_done' and end_detail not in (None, 'frontiers_done'))):
        outcome = 'partial'                        # 스스로 끝났지만 목표 일부 포기 / 부분 지도
    fault_free = None
    if outcome not in UNDECIDED_OUTCOMES:
        fault_free = outcome in ('completed', 'partial', 'operator_stopped') and not holds and not losses and not last['held_at_end']
    verified_known = avail['verified_arrival']
    disp = round(sum(g['displacement'] or 0.0 for g in m_goals if g['verified']), 3) if verified_known else None
    esc_travel = round(sum(x['travel'] or 0.0 for x in m_esc), 3) if avail['escape'] else None
    lb = [v for v in (disp, esc_travel) if v is not None]
    time_in = collections.Counter()
    for s in segs:
        time_in.update(s['time_in'])
    autonomous = sum(s['autonomous_s'] for s in segs)
    if not dry:
        daily[kst_date(first['start_t'])]['missions'] += 1
        for t, _k in inter_t:
            daily[kst_date(t)]['interventions'] += 1
        for loss in losses:
            daily[kst_date(loss['t'])]['authority_losses'] += 1
    return dict(
        mission_id='%s#%d' % (sid, n + 1), session_id=sid,
        start_t=first['start_t'], end_t=last['end_t'], start_kst=kst(first['start_t']), end_kst=kst(last['end_t']),
        mode=first['mode'], start_mode=first['start_mode'], launch=first['launch'],
        segments=len(segs), auto_resumes=sum(1 for s in segs if s['restart'] == 'auto_resume'),
        operator_restarts=sum(1 for s in segs if s['restart'] == 'operator_restart'),
        wall_s=round(last['end_t'] - first['start_t'], 1), autonomous_s=round(autonomous, 1),
        hold_s=round(time_in.get(HOLD, 0.0), 1), human_wait_s=round(sum(time_in.get(x, 0.0) for x in HUMAN_WAIT_STATES), 1),
        time_in_state={k: round(v, 1) for k, v in sorted(time_in.items())},
        end_class=end_class, end_detail=end_detail, outcome=outcome, fault_free=fault_free,
        held_at_end=last['held_at_end'], truncated=last['open'],
        goals_sent=len(m_goals),
        goals_succeeded_verified=sum(1 for g in m_goals if g['verified']) if verified_known else None,
        goals_succeeded_backend=sum(1 for g in m_goals if g['backend'] == 'succeeded'),
        goals_aborted=sum(1 for g in m_goals if g['result'] == 'aborted'),
        goals_canceled=sum(1 for g in m_goals if g['result'] == 'canceled'),
        verified_displacement_m=disp, escape_travel_m=esc_travel,
        distance_m=None, distance_lower_bound_m=round(sum(lb), 3) if lb else None,
        interventions={k: inter[k] for k in INTERVENTION_TYPES}, interventions_total=sum(inter.values()),
        interventions_excl_end_stop=sum(inter.values()) - (1 if end_stop else 0), ended_by_operator=end_stop is not None,
        intervention_times=[[kst(t), k] for t, k in inter_t],
        checkpoint_decisions=checkpoints, hints_in_task=hints_task, hints_done=hints_done, hints_abandoned=hints_abandoned,
        authority_losses=len(losses) if (avail['authority_lost'] or avail['permit_failed']) else None,
        authority_loss_causes=[x['cause'] for x in losses],
        safe_hold_entries=len(holds), safe_hold_flags=sorted({f for h in holds for f in h['flags']}),
        slow_ticks=len(slow) if avail['slow_tick'] else None,
        max_slow_tick_s=(max(e['seconds'] for e in slow) if slow else None),
        escapes_attempted=len(m_esc) if avail['escape'] else None,
        escapes_done=sum(1 for x in m_esc if x['state'] == 'done') if avail['escape'] else None,
        escapes_failed=sum(1 for x in m_esc if x['state'] == 'failed') if avail['escape'] else None,
        battery_end=float(end_detail) if end_class == 'battery_end' and end_detail else None,
        dry_run=dry,
    )


# ── 누적 요약 ────────────────────────────────────────────────────────────────
def _rate(num, hours):
    return round(num / hours, 3) if (num is not None and hours and hours > 0) else None


def _ratio(num, den):
    return round(num / den, 4) if den else None


def _overlaps(missions):
    """서로 다른 소스(PC·젯손)의 임무가 시간상 겹치면 같은 주행을 두 번 셀 수 있다 — 겹치는 쌍을 나열(정상이면 빈 목록)."""
    ms = sorted(missions, key=lambda m: m['start_t'])
    out = []
    for i, a in enumerate(ms):
        for b in ms[i + 1:]:
            if b['start_t'] >= a['end_t']:
                break
            if a['session_id'].split('/')[0] != b['session_id'].split('/')[0]:
                out.append([a['mission_id'], b['mission_id']])
    return out


def summarize(sessions, *, now=None, last_sync=None):
    real = [s for s in sessions if not s.get('empty') and not s['dry_run']]
    dry = [s for s in sessions if not s.get('empty') and s['dry_run']]
    missions = [m for s in real for m in s['missions']]
    hours = sum(s['autonomous_s'] for s in real) / 3600.0

    def hours_where(pred):
        return sum(s['autonomous_s'] for s in real if pred(s)) / 3600.0

    def total(key, pred=lambda s: True):
        vals = [s[key] for s in real if pred(s)]
        return sum(v for v in vals if v is not None)

    complete = [s for s in real if s['instrumentation_complete']]
    h_complete = sum(s['autonomous_s'] for s in complete) / 3600.0
    inter_all = collections.Counter()
    inter_complete = collections.Counter()
    for s in real:
        inter_all.update(s['interventions'])
        if s['instrumentation_complete']:
            inter_complete.update(s['interventions'])
    n_all, n_complete = sum(inter_all.values()), sum(inter_complete.values())
    x_all = sum(s['interventions_excl_end_stop'] for s in real)
    x_complete = sum(s['interventions_excl_end_stop'] for s in complete)
    hints_task_complete = sum(s['hints_in_task'] for s in complete)
    unattr_complete = sum(1 for s in complete for m in s['missions'] if m['outcome'] == 'unattributed_stop')

    by_mode = collections.defaultdict(lambda: collections.Counter())
    for m in missions:
        c = by_mode[m['mode']]
        c['missions'] += 1
        c['autonomous_s'] += m['autonomous_s']
        c['outcome:' + m['outcome']] += 1
        c['auto_resumes'] += m['auto_resumes']
    decided = [m for m in missions if m['outcome'] not in UNDECIDED_OUTCOMES]
    terminal = [m for m in decided if m['mode'] in TERMINAL_GOAL_MODES]
    completed_terminal = [m for m in terminal if m['outcome'] == 'completed']
    fault_free = [m for m in decided if m['fault_free']]

    v_sessions = [s for s in real if s['available']['verified_arrival']]
    g_ver = total('goals_succeeded_verified', lambda s: s['available']['verified_arrival'])
    g_ab_v = sum(s['goals_aborted'] for s in v_sessions)
    g_cancel_v = sum(s['goals_canceled'] for s in v_sessions)
    legacy = [s for s in real if not s['available']['verified_arrival']]
    g_leg_ok = sum(s['goals_succeeded_backend'] for s in legacy)
    g_leg_ab = sum(s['goals_aborted'] for s in legacy)

    loss_attr = collections.Counter()
    loss_unattr = 0
    for s in real:
        for cause, n in s['authority_loss_causes'].items():
            if cause == 'unattributed':
                loss_unattr += n
            else:
                loss_attr[cause] += n
    h_loss_attr = hours_where(lambda s: s['available']['authority_lost'])
    h_loss_any = hours_where(lambda s: s['available']['authority_lost'] or s['available']['permit_failed'])
    st_sessions = [s for s in real if s['available']['slow_tick']]
    h_slow = hours_where(lambda s: s['available']['slow_tick'])
    slow_n = sum(s['slow_ticks'] or 0 for s in st_sessions)
    max_tick = max([s['max_tick_s'] for s in real if s['max_tick_s'] is not None], default=None)
    esc_sessions = [s for s in real if s['available']['escape']]
    esc = {k: sum(s[k] or 0 for s in esc_sessions) for k in ('escapes_attempted', 'escapes_done', 'escapes_failed', 'escapes_stopped', 'escapes_no_result')}
    esc_decided = esc['escapes_done'] + esc['escapes_failed']
    holds = collections.Counter()
    for s in real:
        holds.update(s['safe_hold_flags'])
    disp = sum(s['verified_displacement_m'] or 0.0 for s in real)
    esc_travel = sum(s['escape_travel_m'] or 0.0 for s in real)

    daily = collections.defaultdict(collections.Counter)
    for s in real:
        for d, c in s['daily'].items():
            daily[d].update(c)
    day_rows = []
    for d in sorted(daily):
        c = daily[d]
        day_rows.append(dict(date=d, sessions=c['sessions'], missions=c['missions'],
                             autonomous_h=round(c['autonomous_s'] / 3600.0, 3), interventions=c['interventions'],
                             authority_losses=c['authority_losses'], slow_ticks=c['slow_ticks'],
                             safe_hold_entries=c['safe_hold_entries'], escapes_attempted=c['escapes_attempted'],
                             escapes_done=c['escapes_done'], goals_sent=c['goals_sent'], goals_verified=c['goals_verified']))

    src = collections.Counter(s['source'] for s in real)
    src_h = collections.Counter()
    for s in real:
        src_h[s['source']] += s['autonomous_s'] / 3600.0
    starts = [s['start_t'] for s in sessions if not s.get('empty')]
    complete_since = max(_epoch(AVAILABLE_SINCE[k][0]) for k in COMPLETE_INSTRUMENTATION_KEYS)
    return dict(
        schema=SCHEMA, generated_at_kst=kst(now) if now else None, last_sync=last_sync,
        sessions=dict(total=len([s for s in sessions if not s.get('empty')]), real=len(real), dry_run=len(dry),
                      empty=sum(1 for s in sessions if s.get('empty')), by_source=dict(src),
                      with_missions=sum(1 for s in real if s['missions_count']),
                      live=[s['session_id'] for s in sessions if s.get('live')],
                      first_kst=kst(min(starts)) if starts else None, last_kst=kst(max(starts)) if starts else None),
        missions=dict(total=len(missions), segments=sum(m['segments'] for m in missions),
                      auto_resumes_merged=sum(m['auto_resumes'] for m in missions),
                      operator_restarts=sum(m['operator_restarts'] for m in missions),
                      by_mode={k: dict(v, autonomous_h=round(v['autonomous_s'] / 3600.0, 3)) for k, v in sorted(by_mode.items())},
                      with_autonomous_ge_60s=sum(1 for m in missions if m['autonomous_s'] >= 60)),
        autonomous_hours=dict(total=round(hours, 3), by_source={k: round(v, 3) for k, v in src_h.items()},
                              by_mode={k: round(v['autonomous_s'] / 3600.0, 3) for k, v in sorted(by_mode.items())}),
        distance=dict(km=None, note='연속 포즈(오도메트리) 기록이 없어 총 이동 거리는 알 수 없음',
                      lower_bound_km=round((disp + esc_travel) / 1000.0, 4),
                      verified_displacement_km=round(disp / 1000.0, 4), escape_travel_km=round(esc_travel / 1000.0, 4)),
        goals=dict(sent=total('goals_sent'),
                   verified_era=dict(since=AVAILABLE_SINCE['verified_arrival'][0], sent=sum(s['goals_sent'] for s in v_sessions),
                                     succeeded_verified=g_ver, aborted=g_ab_v, canceled=g_cancel_v,
                                     success_rate=_ratio(g_ver, g_ver + g_ab_v)),
                   legacy_era=dict(sent=sum(s['goals_sent'] for s in legacy), backend_succeeded_unverified=g_leg_ok,
                                   aborted=g_leg_ab, backend_success_rate_unverified=_ratio(g_leg_ok, g_leg_ok + g_leg_ab))),
        success=dict(mission_completion_rate=_ratio(len(completed_terminal), len(terminal)),
                     completion_basis=dict(modes=list(TERMINAL_GOAL_MODES), completed=len(completed_terminal), decided=len(terminal)),
                     fault_free_rate=_ratio(len(fault_free), len(decided)),
                     fault_free_basis=dict(fault_free=len(fault_free), decided=len(decided)),
                     outcomes=dict(collections.Counter(m['outcome'] for m in missions))),
        interventions=dict(
            complete_instrumentation=dict(since=kst(complete_since), autonomous_h=round(h_complete, 3), total=n_complete,
                                          by_type=dict(inter_complete), per_hour=_rate(n_complete, h_complete),
                                          excl_end_stop_total=x_complete, excl_end_stop_per_hour=_rate(x_complete, h_complete),
                                          mtbi_min=round(h_complete * 60.0 / n_complete, 2) if n_complete else None,
                                          upper_bound_total=n_complete + hints_task_complete + unattr_complete,
                                          upper_bound_per_hour=_rate(n_complete + hints_task_complete + unattr_complete, h_complete),
                                          hints_in_task=hints_task_complete, unattributed_stops=unattr_complete),
            all_time=dict(autonomous_h=round(hours, 3), total=n_all, by_type=dict(inter_all), per_hour=_rate(n_all, hours),
                          excl_end_stop_total=x_all, excl_end_stop_per_hour=_rate(x_all, hours),
                          mtbi_min=round(hours * 60.0 / n_all, 2) if n_all else None,
                          note='2026-10-02 19:17 이전 세션은 수동 인계·일부 정지 원인이 기록되지 않아 하한'),
            checkpoint_decisions=sum(s['checkpoint_decisions'] for s in real),
            idle_operator_stops=sum(s['idle_operator_stops'] for s in real)),
        authority_losses=dict(attributed=dict(loss_attr), attributed_total=sum(loss_attr.values()),
                              attributed_since=AVAILABLE_SINCE['authority_lost'][0], attributed_hours=round(h_loss_attr, 3),
                              attributed_per_hour=_rate(sum(loss_attr.values()), h_loss_attr),
                              unattributed=loss_unattr, unattributed_window=[AVAILABLE_SINCE['permit_failed'][0], AVAILABLE_SINCE['authority_lost'][0]],
                              known_hours=round(h_loss_any, 3), unknown_hours=round(hours - h_loss_any, 3),
                              raw_authority_lost_events=sum(s['authority_lost_events'] for s in real)),
        slow_ticks=dict(count=slow_n, known_hours=round(h_slow, 3), per_hour=_rate(slow_n, h_slow),
                        max_tick_s=max_tick, since=AVAILABLE_SINCE['slow_tick'][0]),
        escapes=dict(esc, success_rate=_ratio(esc['escapes_done'], esc_decided),
                     denied=sum(s['escapes_denied'] for s in real), travel_m=round(esc_travel, 2),
                     known_hours=round(hours_where(lambda s: s['available']['escape']), 3)),
        safe_holds=dict(in_mission=sum(s['safe_hold_entries'] for s in real), idle=sum(s['safe_hold_entries_idle'] for s in real),
                        by_flag=dict(holds), per_hour=_rate(sum(s['safe_hold_entries'] for s in real), hours)),
        battery=dict(note='배터리 잔량은 에이전트 기록에 없음(시작·종료 모두 알 수 없음)',
                     ended_by_battery=sum(1 for m in missions if m['end_class'] == 'battery_end')),
        data_quality=dict(bad_lines=sum(s['bad_lines'] for s in sessions), truncated_missions=sum(1 for m in missions if m['outcome'] == 'truncated'),
                          cross_source_overlaps=_overlaps(missions),
                          in_progress_missions=sum(1 for m in missions if m['outcome'] == 'in_progress'),
                          sessions_with_notes={s['session_id']: s['notes'] for s in sessions if s.get('notes')},
                          dry_run_sessions=[s['session_id'] for s in dry]),
        per_day=day_rows,
        constants=dict(GAP_CAP_S=GAP_CAP_S, LAUNCH_WINDOW_S=LAUNCH_WINDOW_S, END_EVIDENCE_WINDOW_S=END_EVIDENCE_WINDOW_S,
                       HINT_DONE_WINDOW_S=HINT_DONE_WINDOW_S, AUTO_RESUME_MAX_GAP_S=AUTO_RESUME_MAX_GAP_S,
                       MERGE_MAX_GAP_S=MERGE_MAX_GAP_S, DEBOUNCE_S=DEBOUNCE_S, LIVE_WINDOW_S=LIVE_WINDOW_S),
        available_since={k: dict(since=v[0], first_session=v[1], event=v[2]) for k, v in AVAILABLE_SINCE.items()},
        auto_resume_since=AUTO_RESUME_SINCE[0],
    )


# ── 출력 ─────────────────────────────────────────────────────────────────────
SESSION_COLUMNS = (
    'session_id', 'source', 'start_kst', 'end_kst', 'duration_s', 'dry_run', 'live', 'modes', 'missions_count', 'segments_count',
    'auto_resumes', 'operator_restarts', 'autonomous_s', 'time_in_state', 'transitions', 'safe_hold_entries', 'safe_hold_flags',
    'safe_hold_entries_idle', 'goals_sent', 'goals_succeeded_verified', 'goals_succeeded_backend', 'goals_aborted', 'goals_canceled',
    'goals_no_result', 'distance_m', 'distance_lower_bound_m', 'verified_displacement_m', 'escape_travel_m', 'interventions_total',
    'interventions_excl_end_stop', 'interventions', 'hints_in_task', 'checkpoint_decisions', 'idle_operator_stops', 'authority_losses', 'authority_loss_causes',
    'authority_lost_events', 'slow_ticks', 'max_tick_s', 'escapes_attempted', 'escapes_done', 'escapes_failed', 'escapes_stopped',
    'escapes_denied', 'battery_start', 'battery_end', 'end_reason', 'instrumentation_complete', 'n_events', 'bad_lines', 'notes',
)
MISSION_COLUMNS = (
    'mission_id', 'session_id', 'start_kst', 'end_kst', 'mode', 'start_mode', 'launch', 'segments', 'auto_resumes', 'operator_restarts',
    'wall_s', 'autonomous_s', 'hold_s', 'human_wait_s', 'end_class', 'end_detail', 'outcome', 'fault_free', 'held_at_end', 'truncated',
    'goals_sent', 'goals_succeeded_verified', 'goals_succeeded_backend', 'goals_aborted', 'goals_canceled', 'distance_m',
    'distance_lower_bound_m', 'verified_displacement_m', 'escape_travel_m', 'interventions_total', 'interventions_excl_end_stop',
    'ended_by_operator', 'interventions', 'hints_in_task', 'checkpoint_decisions', 'hints_done', 'hints_abandoned', 'authority_losses', 'authority_loss_causes', 'safe_hold_entries',
    'safe_hold_flags', 'slow_ticks', 'max_slow_tick_s', 'escapes_attempted', 'escapes_done', 'escapes_failed', 'battery_end', 'dry_run',
)


def _cell(v):
    if v is None:
        return 'unknown'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (dict, list, tuple)):
        return json.dumps(v, ensure_ascii=False, sort_keys=isinstance(v, dict), separators=(',', ':'))
    return v


def _atomic_write(path, text):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.' + os.path.basename(path) + '.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text)
        mask = os.umask(0)
        os.umask(mask)
        os.chmod(tmp, 0o666 & ~mask)                 # mkstemp 의 0600 대신 보통 파일 권한
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _csv_text(rows, columns):
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(columns)
    for r in rows:
        w.writerow([_cell(r.get(c)) for c in columns])
    return buf.getvalue()


def _fmt(v, nd=2, unit=''):
    if v is None:
        return '알 수 없음'
    if isinstance(v, float):
        return ('%.' + str(nd) + 'f%s') % (v, unit)
    return '%s%s' % (v, unit)


def _pct(v):
    return '알 수 없음' if v is None else '%.1f %%' % (100.0 * v)


MODE_KO = {'explore': '탐색', 'patrol': '순찰', 'full': '통합(탐색→순찰)', 'task': '작업(두뇌 스킬)', 'hint': '힌트 시작',
           'legacy': '옛 기록(모드 기록 전)', 'unspecified': '모드 기록 없음'}
OUTCOME_KO = {'completed': '완료', 'partial': '부분 완료(목표 일부 포기)', 'operator_stopped': '운영자 정지', 'manual_takeover': '수동 인계', 'fault': '고장·자동 종료',
              'unattributed_stop': '원인 미기록 정지', 'battery_end': '배터리 종료', 'reset': '초기화', 'truncated': '기록 끊김',
              'in_progress': '진행 중', 'other': '기타'}
INTER_KO = {'stop': '정지', 'manual_takeover': '수동 인계', 'hint': '힌트·펜', 'resume': '재개·재시작'}


def summary_markdown(S):
    L = []
    a = L.append
    ses, mis, ah = S['sessions'], S['missions'], S['autonomous_hours']
    ic, ia = S['interventions']['complete_instrumentation'], S['interventions']['all_time']
    al, st, es, sh, go = S['authority_losses'], S['slow_ticks'], S['escapes'], S['safe_holds'], S['goals']
    a('# Go2 임무 원장 요약')
    a('')
    a('생성 %s · 정의는 `~/go2_ws/tools/mission_ledger/DEFINITIONS.md` · 알 수 없는 값은 "알 수 없음"으로 둔다(대치 없음).' % (S['generated_at_kst'] or '?'))
    if S.get('last_sync'):
        ls = S['last_sync']
        a('마지막 로봇 동기화: %s (rsync 코드 %s%s)' % (ls.get('time_kst', '?'), ls.get('robot_rc', '?'),
                                                 ', 실패 — 로봇 쪽 새 기록은 반영 안 됨' if ls.get('robot_rc') not in (0, 23, 24, '0', '23', '24') else ''))
    a('')
    a('## 한눈에')
    a('')
    a('| 지표 | 값 | 근거·범위 |')
    a('|---|---|---|')
    a('| 세션(에이전트 실행) | %d (젯손 %d · PC %d), 드라이런 %d 제외 | %s ~ %s |' % (
        ses['real'], ses['by_source'].get('jetson', 0), ses['by_source'].get('pc', 0), ses['dry_run'],
        (ses['first_kst'] or '?')[:10], (ses['last_kst'] or '?')[:10]))
    a('| 자율 임무 | %d (자동 재개 %d회는 같은 임무로 합침) | 1분 이상 자율 시간: %d |' % (mis['total'], mis['auto_resumes_merged'], mis['with_autonomous_ge_60s']))
    a('| 자율 운용 시간 | %.2f h | 이동 상태(MAP·PATROL 등) 시간, 사건 간격 %d s 상한 |' % (ah['total'], int(GAP_CAP_S)))
    a('| 이동 거리 | 알 수 없음 | 연속 포즈 기록 없음. 하한 %.3f km(검증 도착 직선 변위 + 탈출 주행) |' % S['distance']['lower_bound_km'])
    a('| 목표 도달 성공률(검증) | %s | 검증 도착 %d / (도착 %d + 실패 %d), %s 이후 |' % (
        _pct(go['verified_era']['success_rate']), go['verified_era']['succeeded_verified'] or 0, go['verified_era']['succeeded_verified'] or 0,
        go['verified_era']['aborted'], go['verified_era']['since'][:10]))
    a('| 임무 완료율(탐색·작업) | %s | 완료 %d / 결말 난 %d |' % (
        _pct(S['success']['mission_completion_rate']), S['success']['completion_basis']['completed'], S['success']['completion_basis']['decided']))
    a('| 무고장 종료율(전체 임무) | %s | %d / %d (안전 정지·자동 권한 회수 0회, 완료·운영자 정지로 끝남) |' % (
        _pct(S['success']['fault_free_rate']), S['success']['fault_free_basis']['fault_free'], S['success']['fault_free_basis']['decided']))
    a('| 운영자 개입 / 시간 | %s /h (임무를 끝낸 정지 제외 %s /h, 상한 %s /h) | 기록 완비 구간 %s 이후 %.2f h, 개입 %d건 |' % (
        _fmt(ic['per_hour']), _fmt(ic['excl_end_stop_per_hour']), _fmt(ic['upper_bound_per_hour']),
        (ic['since'] or '?')[:16].replace('T', ' '), ic['autonomous_h'], ic['total']))
    a('| 개입 간 평균 자율 시간(MTBI) | %s | 같은 구간 |' % (_fmt(ic['mtbi_min'], 1, ' 분') if ic['mtbi_min'] is not None else ('개입 0건' if ic['autonomous_h'] else '알 수 없음')))
    a('| 자동 권한 회수 | 귀속 %d건 (%s /h) + 원인 미기록 %d건 | 귀속 가능 %s 이후 %.2f h |' % (
        al['attributed_total'], _fmt(al['attributed_per_hour']), al['unattributed'], al['attributed_since'][:10], al['attributed_hours']))
    a('| 느린 틱(>1.5 s) | %d건 (%s /h), 최대 %s | 기록 %s 이후 %.2f h |' % (
        st['count'], _fmt(st['per_hour']), _fmt(st['max_tick_s'], 2, ' s'), st['since'][:10], st['known_hours']))
    a('| 탈출(escape) | 시도 %d · 성공 %d · 실패 %d · 운영자 중단 %d (성공률 %s) | 탈출 주행 %.1f m |' % (
        es['escapes_attempted'], es['escapes_done'], es['escapes_failed'], es['escapes_stopped'], _pct(es['success_rate']), es['travel_m']))
    a('| 안전 정지(SAFE_HOLD) 진입 | 임무 중 %d (%s /h), 대기 중 %d | 원인별: %s |' % (
        sh['in_mission'], _fmt(sh['per_hour']), sh['idle'], ', '.join('%s %d' % kv for kv in sorted(sh['by_flag'].items(), key=lambda x: -x[1])) or '없음'))
    a('| 배터리 | 알 수 없음 | 에이전트가 잔량을 기록하지 않음 |')
    a('')
    a('## 운영자 개입 내역')
    a('')
    a('| 구간 | 자율 h | 정지 | 수동 인계 | 힌트·펜 | 재개·재시작 | 합계 | /h | 종료 정지 제외 /h |')
    a('|---|---|---|---|---|---|---|---|---|')
    for label, d in (('기록 완비(%s~)' % (ic['since'] or '?')[:10], ic), ('전체(하한)', ia)):
        bt = d['by_type']
        a('| %s | %.2f | %d | %d | %d | %d | %d | %s | %s |' % (label, d['autonomous_h'], bt.get('stop', 0), bt.get('manual_takeover', 0),
                                                                 bt.get('hint', 0), bt.get('resume', 0), d['total'], _fmt(d['per_hour']),
                                                                 _fmt(d['excl_end_stop_per_hour'])))
    a('')
    a('작업(task) 임무 중 힌트 %d건은 두뇌 스킬 목표와 기록이 같아 개입에서 뺐다(상한에는 포함). 대기(IDLE) 중 정지 %d건·승인/거부 %d건은 개입이 아니다.' % (
        ic['hints_in_task'], S['interventions']['idle_operator_stops'], S['interventions']['checkpoint_decisions']))
    a('')
    a('## 모드별 임무')
    a('')
    a('| 모드 | 임무 | 자율 h | 자동 재개 | 결말 |')
    a('|---|---|---|---|---|')
    for mode, c in mis['by_mode'].items():
        outs = ', '.join('%s %d' % (OUTCOME_KO.get(k.split(':', 1)[1], k), v) for k, v in sorted(c.items()) if k.startswith('outcome:'))
        a('| %s | %d | %.2f | %d | %s |' % (MODE_KO.get(mode, mode), c['missions'], c['autonomous_h'], c['auto_resumes'], outs))
    a('')
    a('## 자동 권한 회수 원인')
    a('')
    if al['attributed']:
        for cause, n in sorted(al['attributed'].items(), key=lambda x: -x[1]):
            a('- %s: %d' % (cause, n))
    else:
        a('- (귀속 가능한 회수 없음)')
    a('- 원인 미기록(%s~%s, permit_failed 의 automatic_stopped 만 있음): %d' % (al['unattributed_window'][0][:10], al['unattributed_window'][1][:10], al['unattributed']))
    a('- 그 전 %.2f h 는 회수 여부 자체를 알 수 없음' % al['unknown_hours'])
    a('')
    a('## 일별')
    a('')
    a('| 날짜(KST) | 세션 | 임무 | 자율 h | 개입 | 권한 회수 | 느린 틱 | 안전 정지 | 탈출 시도/성공 | 목표 전송/검증 도착 |')
    a('|---|---|---|---|---|---|---|---|---|---|')
    for r in S['per_day']:
        a('| %s | %d | %d | %.3f | %d | %d | %d | %d | %d/%d | %d/%d |' % (
            r['date'], r['sessions'], r['missions'], r['autonomous_h'], r['interventions'], r['authority_losses'], r['slow_ticks'],
            r['safe_hold_entries'], r['escapes_attempted'], r['escapes_done'], r['goals_sent'], r['goals_verified']))
    a('')
    a('일별 표의 개입·권한 회수·느린 틱·탈출은 그 기록이 존재하기 시작한 날부터만 의미가 있다(이전 날의 0 은 "기록 없음"일 수 있다 — 정의서 §가용성).')
    a('')
    a('## 데이터 품질')
    a('')
    dq = S['data_quality']
    a('- 깨진 줄: %d · 기록이 끊긴 임무(프로세스 종료): %d · 진행 중 임무: %d' % (dq['bad_lines'], dq['truncated_missions'], dq['in_progress_missions']))
    a('- 드라이런 세션(집계 제외): %d' % len(dq['dry_run_sessions']))
    a('- PC·젯손 임무 시간 겹침(이중 집계 위험): %s' % (len(dq['cross_source_overlaps']) or '없음'))
    if ses['live']:
        a('- 진행 중 세션: %s' % ', '.join(ses['live']))
    a('- 총 이동 거리·배터리는 기록이 없어 알 수 없음. 필요하면 에이전트에 주기적 오도메트리 누적 거리와 시작/종료 배터리 기록을 추가해야 한다.')
    a('')
    return '\n'.join(L)


# ── 진입점 ───────────────────────────────────────────────────────────────────
def discover(sources):
    """[(source, root)] → [(source, name, dir)] (agent_* 디렉터리, events.jsonl 있는 것만)."""
    out = []
    for source, root in sources:
        for d in sorted(glob.glob(os.path.join(os.path.expanduser(root), 'agent_*'))):
            if os.path.isfile(os.path.join(d, 'events.jsonl')):
                out.append((source, os.path.basename(d), d))
    return out


def build(sources, now=None):
    found = discover(sources)
    loaded = []
    for source, name, d in found:
        events, bad, n = load_events(os.path.join(d, 'events.jsonl'))
        loaded.append((source, name, d, events, bad, n))
    newest = {}
    for source, name, d, events, bad, n in loaded:
        if events and (source not in newest or events[0]['t'] > newest[source][0]):
            newest[source] = (events[0]['t'], name)
    sessions = []
    for source, name, d, events, bad, n in loaded:
        sessions.append(analyze_session(source, name, events, now=now, newest=newest.get(source, (None, None))[1] == name,
                                        bad_lines=bad, n_lines=n, max_profile_tick=profile_max_tick(d)))
    sessions.sort(key=lambda s: (s.get('start_t') or 0, s['session_id']))
    return sessions


def write_outputs(sessions, out_dir, now=None, last_sync=None):
    S = summarize(sessions, now=now, last_sync=last_sync)
    missions = [m for s in sessions for m in s.get('missions', [])]
    doc = dict(schema=SCHEMA, generated_at_kst=kst(now) if now else None,
               constants=S['constants'], available_since=S['available_since'], sessions=sessions)
    _atomic_write(os.path.join(out_dir, 'missions.csv'), _csv_text(sessions, SESSION_COLUMNS))
    _atomic_write(os.path.join(out_dir, 'mission_list.csv'), _csv_text(missions, MISSION_COLUMNS))
    _atomic_write(os.path.join(out_dir, 'missions.json'), json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False) + '\n')
    _atomic_write(os.path.join(out_dir, 'summary.json'), json.dumps(S, ensure_ascii=False, indent=1) + '\n')
    _atomic_write(os.path.join(out_dir, 'summary.md'), summary_markdown(S) + '\n')
    return S


def main(argv=None):
    ap = argparse.ArgumentParser(description='Go2 임무 원장: events.jsonl → missions.csv/json, summary.json/md')
    ap.add_argument('--source', action='append', default=None, metavar='NAME=DIR',
                    help='소스 이름=루트(여러 번). 기본 jetson=~/go2_runs_mirror/jetson, pc=~/go2_runs_mirror/pc')
    ap.add_argument('--out', default='~/go2_runs_mirror/ledger')
    ap.add_argument('--now', type=float, default=None, help='기준 시각(epoch s, 시험용). 기본 현재')
    ap.add_argument('--last-sync', default=None, help='동기화 상태 JSON 파일(있으면 요약에 표시)')
    args = ap.parse_args(argv)
    specs = args.source or ['jetson=~/go2_runs_mirror/jetson', 'pc=~/go2_runs_mirror/pc']
    sources = []
    for spec in specs:
        if '=' not in spec:
            ap.error('--source 는 NAME=DIR 형식')
        name, root = spec.split('=', 1)
        sources.append((name.strip(), root.strip()))
    now = args.now if args.now is not None else dt.datetime.now(KST).timestamp()
    last_sync = None
    if args.last_sync and os.path.isfile(os.path.expanduser(args.last_sync)):
        try:
            with open(os.path.expanduser(args.last_sync), encoding='utf-8') as f:
                last_sync = json.load(f)
        except (OSError, ValueError):
            last_sync = {'error': 'unreadable'}
    sessions = build(sources, now=now)
    S = write_outputs(sessions, os.path.expanduser(args.out), now=now, last_sync=last_sync)
    print('sessions %d (dry %d) · missions %d · autonomous %.2f h · interventions(complete era) %s/h · out %s' % (
        S['sessions']['real'], S['sessions']['dry_run'], S['missions']['total'], S['autonomous_hours']['total'],
        S['interventions']['complete_instrumentation']['per_hour'], os.path.expanduser(args.out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
